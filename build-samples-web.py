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

def build_sample(project_name, project_path, app_name, language, samples_ref, languages, output):

    print("Bulding sample: %s, language: %s" % (project_name, language), flush=True)

    supernova_root = os.path.abspath('supernova')
    build_tool = os.path.join(supernova_root, 'tools', 'supernova.py')

    #samples_root = os.path.join(supernova_root, 'samples')
    samples_root = os.path.join('samples')
    
    sample_path = os.path.abspath(os.path.join(samples_root, project_path))

    if language == 'cpp':
        source_sample_path = os.path.join(sample_path, 'main.cpp')
    else:
        source_sample_path = os.path.join(sample_path, 'lua', 'main.lua')

    lexer = get_lexer_for_filename(source_sample_path)
    style = get_style_by_name('colorful')

    snippet = codeSnippet(file_get_contents(source_sample_path), lexer, style, True, get_default_style())

    shell_file_template = os.path.join('..', 'template', 'sample_shell.html')
    shell_file = os.path.abspath('sample_shell.html')

    lang_change = ''
    lang_change_url = ''
    github_main_project = 'https://github.com/supernovaengine/supernova-samples' + '/blob/' + samples_ref + '/' + project_path
    if language == 'cpp':
        lang_label = 'C++'
        github_url = github_main_project + '/main.cpp'
        compile_lang = '--no-lua-init'
        if 'lua' in languages:
            lang_change = 'Change to Lua sample'
            lang_change_url = '../' + app_name + '-lua'
    else:
        lang_label = 'Lua'
        github_url = github_main_project + '/lua/main.lua'
        compile_lang = '--no-cpp-init'
        if 'cpp' in languages:
            lang_change = 'Change to C++ sample'
            lang_change_url = '../' + app_name

    t = Template(file_get_contents(shell_file_template))
    shell_content = t.render(
        emscripten="{{{ SCRIPT }}}", 
        code_snippet=snippet,
        sample_name=project_name,
        sample_language=lang_label,
        sample_change=lang_change,
        sample_change_url=lang_change_url,
        sample_github_url=github_url,
        sample_output=output,
        year=datetime.date.today().year
        )

    file_write_contents(shell_file, shell_content)

    subprocess.run([
        sys.executable, build_tool, 
        '--platform', 'web', 
        "--project", sample_path, 
        "--supernova", supernova_root, 
        "--appname", app_name,
        "--em-shell-file", shell_file,
        compile_lang,
        "--build"
        ]).check_returncode()

    src_dir = os.path.join(supernova_root, 'tools', 'build', 'web')
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

    samples_list_yaml = data['samples']
    supernovaRepo = data['repo']
    repoRef = data['repoRef']
    samplesRepo = data['samplesRepo']
    samplesRef = data['samplesRepoRef']

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

    cloneRepo(supernovaRepo, 'supernova', repoRef)
    cloneRepo(samplesRepo, 'samples', samplesRef)

    # Call supershader.py before building any samples
    supernova_root = os.path.abspath('supernova')
    supershader_tool = os.path.join(supernova_root, 'tools', 'supershader.py')

    print("Running supershader.py...", flush=True)
    subprocess.run([sys.executable, supershader_tool, "-l", "glsl300es"]).check_returncode()

    ### Create samples index
    samples_list = []
    for sl in samples_list_yaml: 
        sample_name = sl['name']
        sample_desc = sl['desc']
        sample_path = sl['path']
        sample_app = sample_path.replace('_','-').replace(' ','-')
        sample_langs = sl['langs']
        
        langs_links = []
        for la in sample_langs:
            if la=='cpp':
                langs_links.append({'name': 'C++', 'link': sample_app})
            if la=='lua':
                langs_links.append({'name': 'Lua', 'link': sample_app+'-lua'})  

        thumb_image = os.path.join('thumb',sample_path.lower()+'.png')
        if not os.path.exists(os.path.join('site', thumb_image)):
            thumb_image = os.path.join('thumb','default.png')

        samples_list.append({
            'name': sample_name, 
            'url': langs_links[0]['link'], 
            'description': sample_desc,
            'thumb': thumb_image,
            'langs': langs_links
            })

    ### Build CPP samples
    for lang in ['cpp', 'lua']:
        for sl in samples_list_yaml:
            sample_name = sl['name']
            sample_desc = sl['desc']
            sample_path = sl['path']
            sample_app = sample_path.replace('_','-').replace(' ','-')
            sample_langs = sl['langs']
            if 'output' in sl:
                sample_output = sl['output']
            else:
                sample_output = False

            if (lang in sl['langs']): 
                build_sample(sample_name, sample_path, sample_app, lang, samplesRef, sample_langs, sample_output)


    index_file_template = os.path.join('..', 'template', 'index.html')
    index_file = os.path.join('site', 'index.html')

    t = Template(file_get_contents(index_file_template))
    index_content = t.render(
        samples_list=samples_list,
        year=datetime.date.today().year
        )

    file_write_contents(index_file, index_content)


if __name__ == '__main__':
    build_all()
