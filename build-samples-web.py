#!/usr/bin/env python

# /*
# (c) 2026 Eduardo Doria.
# */

import os
import sys
import shutil
import subprocess
import git
import datetime

import re
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.lexers import get_lexer_for_filename
from pygments.styles import get_style_by_name

from jinja2 import Template

import yaml

def copyResourcesDir(src, dst):
    if os.path.exists(src):
        if os.path.exists(dst) and os.path.isdir(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst, False, None)

def moveSource(src, dst, exts):
    if os.path.exists(dst) and os.path.isdir(dst):
        shutil.rmtree(dst)
    
    os.makedirs(dst)

    for item in os.listdir(src):
        if item.lower().endswith(exts):
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            shutil.move(s, d)

def cloneRepo(repo, dst, tag):
    if not os.path.exists(dst):
        print("Cloning %s repository and checkout to: %s" % (dst, tag), flush=True)
        repo = git.Repo.clone_from(repo, dst)
    else:
        print("Checking out %s repository to: %s" % (dst, tag), flush=True)
        repo = git.Repo(dst)

    repo.git.fetch()
    repo.git.checkout(tag)
    repo.remotes['origin'].pull(tag)
    repo.submodule_update(recursive=False)

def codeSnippet(code, lexer, style, linenos, divstyles):
    defstyles = 'overflow:auto;width:auto;'

    formatter = HtmlFormatter(style=style,
                              linenos=False,
                              noclasses=True,
                              cssclass='',
                              cssstyles=defstyles + divstyles,
                              prestyles='margin: 0')
    html = highlight(code, lexer, formatter)
    return html

def get_default_style():
    return 'border:solid gray; border-width:.1em .1em .1em .8em; padding:.2em .6em; margin: 50px auto;'

def file_get_contents(filename):
    with open(filename) as f:
        return f.read()

def file_write_contents(filename, content):
    with open(filename, "w") as f:
        f.write(content)

def find_emscripten_toolchain():
    """Find the Emscripten CMake toolchain file."""
    # Check EMSDK and EMSCRIPTEN env vars first
    emsdk = os.environ.get('EMSDK', '')
    emscripten = os.environ.get('EMSCRIPTEN', '')
    search_paths = []
    if emsdk:
        search_paths.append(emsdk)
    if emscripten:
        search_paths.append(os.path.join(emscripten, '..', '..'))
        search_paths.append(emscripten)
    # Common locations
    search_paths.append(os.path.expanduser('~/Development/emsdk'))
    search_paths.append(os.path.expanduser('~/emsdk'))
    search_paths.append('/opt/emsdk')

    for base in search_paths:
        toolchain = os.path.join(base, 'upstream', 'emscripten', 'cmake', 'Modules', 'Platform', 'Emscripten.cmake')
        if os.path.exists(toolchain):
            return toolchain

    sys.exit("Error: Could not find Emscripten.cmake toolchain file. Set EMSDK environment variable or install emsdk.")

def build_test(project_name, project_path, app_name, language, tests_ref, languages, output):

    print("Building test: %s, language: %s" % (project_name, language), flush=True)

    doriax_root = os.path.abspath(os.path.join('doriax', 'engine'))
    project_cmake_dir = os.path.join(doriax_root, 'project')

    tests_root = os.path.join('samples')
    
    test_path = os.path.abspath(os.path.join(tests_root, project_path))

    if language == 'cpp':
        source_test_path = os.path.join(test_path, 'main.cpp')
    else:
        source_test_path = os.path.join(test_path, 'lua', 'main.lua')

    lexer = get_lexer_for_filename(source_test_path)
    style = get_style_by_name('monokai')

    snippet = codeSnippet(file_get_contents(source_test_path), lexer, style, True, get_default_style())

    shell_file_template = os.path.join('..', 'template', 'test_shell.html')
    shell_file = os.path.abspath('test_shell.html')

    lang_change = ''
    lang_change_url = ''
    github_main_project = 'https://github.com/supernovaengine/supernova-samples' + '/blob/' + tests_ref + '/' + project_path
    if language == 'cpp':
        lang_label = 'C++'
        github_url = github_main_project + '/main.cpp'
        if 'lua' in languages:
            lang_change = 'Change to Lua test'
            lang_change_url = '../' + app_name + '-lua'
    else:
        lang_label = 'Lua'
        github_url = github_main_project + '/lua/main.lua'
        if 'cpp' in languages:
            lang_change = 'Change to C++ test'
            lang_change_url = '../' + app_name

    t = Template(file_get_contents(shell_file_template))
    shell_content = t.render(
        emscripten="{{{ SCRIPT }}}", 
        code_snippet=snippet,
        test_name=project_name,
        test_language=lang_label,
        test_change=lang_change,
        test_change_url=lang_change_url,
        test_github_url=github_url,
        test_output=output,
        year=datetime.date.today().year
        )

    file_write_contents(shell_file, shell_content)

    # Build using cmake directly
    build_dir = os.path.abspath('build_web')

    # Delete cmake cache to force reconfiguration with new project settings
    cmake_cache = os.path.join(build_dir, 'CMakeCache.txt')
    if os.path.exists(cmake_cache):
        os.remove(cmake_cache)

    if language == 'cpp':
        compile_defs = '-DNO_LUA_INIT'
    else:
        compile_defs = '-DNO_CPP_INIT'

    emscripten_toolchain = find_emscripten_toolchain()

    subprocess.run([
        'cmake',
        '-S', project_cmake_dir,
        '-B', build_dir,
        '-DCMAKE_TOOLCHAIN_FILE=' + emscripten_toolchain,
        '-DAPP_NAME=' + app_name,
        '-DDORIAX_ROOT=' + doriax_root,
        '-DPROJECT_ROOT=' + test_path,
        '-DEM_ADDITIONAL_LINK_FLAGS=--shell-file ' + shell_file,
        '-DCMAKE_CXX_FLAGS=' + compile_defs,
        '-DCMAKE_C_FLAGS=' + compile_defs,
        ]).check_returncode()

    subprocess.run([
        'cmake', '--build', build_dir
        ]).check_returncode()

    src_dir = build_dir
    if language == 'lua':
        dst_dir = os.path.join('site', app_name+'-lua')
    else:
        dst_dir = os.path.join('site', app_name)

    moveSource(src_dir, dst_dir, ('.html', '.map', '.wasm', '.js', '.data'))

    os.rename(
        os.path.join(dst_dir, app_name+'.html'), 
        os.path.join(dst_dir, 'index.html')
        )
    
    os.remove(shell_file)

def build_all():

    with open('samples.yaml') as f:
        data = yaml.load(f, Loader=yaml.FullLoader)

    tests_list_yaml = data['tests']
    doriaxRepo = data['repo']
    repoRef = data['repoRef']
    testsRepo = data['testsRepo']
    testsRef = data['testsRepoRef']

    directory = "build"
    if not os.path.exists(directory):
        os.makedirs(directory)
    os.chdir(directory)

    sitepath = os.path.join('site')
    if os.path.exists(sitepath) and os.path.isdir(sitepath):
        shutil.rmtree(sitepath)
    os.makedirs(sitepath)

    copyResourcesDir(os.path.join('..', 'template', 'css'), os.path.join('site','css'))
    copyResourcesDir(os.path.join('..', 'template', 'img'), os.path.join('site','img'))
    copyResourcesDir(os.path.join('..', 'template', 'js'), os.path.join('site','js'))
    copyResourcesDir(os.path.join('..', 'template', 'thumb'), os.path.join('site','thumb'))

    cloneRepo(doriaxRepo, 'doriax', repoRef)
    cloneRepo(testsRepo, 'samples', testsRef)

    # Call supershader.py before building any tests
    doriax_root = os.path.abspath(os.path.join('doriax', 'engine'))
    doriax_repo_root = os.path.abspath('doriax')
    supershader_tool = os.path.join(doriax_root, 'tools', 'supershader.py')

    print("Running supershader.py...", flush=True)
    subprocess.run([sys.executable, supershader_tool, "-l", "glsl300es", "-r", doriax_repo_root]).check_returncode()

    ### Create tests index
    tests_list = []
    for sl in tests_list_yaml: 
        test_name = sl['name']
        test_desc = sl['desc']
        test_path = sl['path']
        test_app = test_path.replace('_','-').replace(' ','-')
        test_langs = sl['langs']
        
        langs_links = []
        for la in test_langs:
            if la=='cpp':
                langs_links.append({'name': 'C++', 'link': test_app})
            if la=='lua':
                langs_links.append({'name': 'Lua', 'link': test_app+'-lua'})  

        thumb_image = os.path.join('thumb',test_path.lower()+'.png')
        if not os.path.exists(os.path.join('site', thumb_image)):
            thumb_image = os.path.join('thumb','default.png')

        tests_list.append({
            'name': test_name, 
            'url': langs_links[0]['link'], 
            'description': test_desc,
            'thumb': thumb_image,
            'langs': langs_links
            })

    ### Build tests
    for lang in ['cpp', 'lua']:
        for sl in tests_list_yaml:
            test_name = sl['name']
            test_desc = sl['desc']
            test_path = sl['path']
            test_app = test_path.replace('_','-').replace(' ','-')
            test_langs = sl['langs']
            if 'output' in sl:
                test_output = sl['output']
            else:
                test_output = False

            if (lang in sl['langs']): 
                build_test(test_name, test_path, test_app, lang, testsRef, test_langs, test_output)


    index_file_template = os.path.join('..', 'template', 'index.html')
    index_file = os.path.join('site', 'index.html')

    t = Template(file_get_contents(index_file_template))
    index_content = t.render(
        tests_list=tests_list,
        year=datetime.date.today().year
        )

    file_write_contents(index_file, index_content)


if __name__ == '__main__':
    build_all()
