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
import json
import stat
import tarfile
import urllib.error
import urllib.request
import zipfile

import re
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.lexers import get_lexer_for_filename
from pygments.styles import get_style_by_name

from jinja2 import Template

import yaml

GITHUB_API_HEADERS = {
    'Accept': 'application/vnd.github+json',
    'User-Agent': 'doriax-tests-site-build-script',
}

EDITOR_WORKFLOW_FILE = 'cmake.yml'
BUILD_TARGET_NAME = 'doriax-test'

def github_actions_escape(value):
    return value.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')

def show_alert(message):
    print("Warning: %s" % message, flush=True)
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        print("::warning::%s" % github_actions_escape(message), flush=True)

def copyResourcesDir(src, dst, copy_function=shutil.copy2):
    if os.path.exists(src):
        if os.path.exists(dst) and os.path.isdir(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst, False, None, copy_function=copy_function)

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

def github_api_get_json(url):
    request = urllib.request.Request(url, headers=GITHUB_API_HEADERS)
    try:
        with urllib.request.urlopen(request) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='replace')
        sys.exit("Error: GitHub API request failed for %s: %s\n%s" % (url, exc, detail))

def download_file(url, filename):
    request = urllib.request.Request(url, headers={'User-Agent': GITHUB_API_HEADERS['User-Agent']})
    try:
        with urllib.request.urlopen(request) as response, open(filename, 'wb') as output:
            shutil.copyfileobj(response, output)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='replace')
        sys.exit("Error: Download failed for %s: %s\n%s" % (url, exc, detail))

def parse_github_repo(repo_url):
    match = re.match(r'(?:https?://github\.com/|git@github\.com:)([^/]+)/([^/]+?)(?:\.git)?/?$', repo_url)
    if not match:
        sys.exit("Error: Expected a GitHub repository URL, got: %s" % repo_url)
    return match.group(1), match.group(2)

def get_editor_artifact_name():
    artifact_name = os.environ.get('DORIAX_EDITOR_ARTIFACT')
    if artifact_name:
        return artifact_name
    if sys.platform.startswith('linux'):
        # The plain doriax_linux artifact is now the AppImage, and artifact zips
        # drop the executable bit anyway, so use the tarball artifact instead.
        return 'doriax_linux_tarball'
    if sys.platform == 'darwin':
        return 'doriax_macos'
    if os.name == 'nt':
        return 'doriax_windows'
    sys.exit("Error: Unsupported host platform for doriax-editor artifact download")

def get_editor_executable_name():
    executable_name = os.environ.get('DORIAX_EDITOR_BINARY')
    if executable_name:
        return executable_name
    if os.name == 'nt':
        return 'doriax-editor.exe'
    return 'doriax-editor'

def is_safe_archive_path(destination_root, member_name):
    member_path = os.path.abspath(os.path.join(destination_root, member_name))
    return member_path == destination_root or member_path.startswith(destination_root + os.sep)

def extract_zip(archive_path, destination):
    destination_root = os.path.abspath(destination)
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            if not is_safe_archive_path(destination_root, member.filename):
                sys.exit("Error: Artifact contains an unsafe path: %s" % member.filename)
        archive.extractall(destination)

def extract_tarball(archive_path, destination):
    destination_root = os.path.abspath(destination)
    with tarfile.open(archive_path) as archive:
        for member in archive.getmembers():
            if not is_safe_archive_path(destination_root, member.name):
                sys.exit("Error: Artifact contains an unsafe path: %s" % member.name)
        # The data filter keeps the executable bit, which is the whole reason
        # the Linux build ships a tarball inside the artifact zip.
        if hasattr(tarfile, 'data_filter'):
            archive.extractall(destination, filter='data')
        else:
            archive.extractall(destination)

def unpack_nested_tarballs(destination):
    tarballs = []
    for root, _dirs, files in os.walk(destination):
        for name in files:
            if name.lower().endswith(('.tar.gz', '.tgz')):
                tarballs.append(os.path.join(root, name))

    for archive_path in tarballs:
        extract_tarball(archive_path, destination)
        os.remove(archive_path)

def find_editor_executable(destination, executable_name):
    for root, _dirs, files in os.walk(destination):
        if executable_name in files:
            return os.path.join(root, executable_name)
    return None

def find_successful_workflow_run(owner, repo_name, commit_sha):
    workflow_runs_url = (
        'https://api.github.com/repos/%s/%s/actions/workflows/%s/runs?head_sha=%s&per_page=100'
        % (owner, repo_name, EDITOR_WORKFLOW_FILE, commit_sha)
    )
    workflow_runs = github_api_get_json(workflow_runs_url).get('workflow_runs', [])
    return next((run for run in workflow_runs if run.get('conclusion') == 'success'), None)

def find_successful_workflow_run_in_history(owner, repo_name, commit):
    head_sha = commit.hexsha
    current = commit
    while current is not None:
        workflow_run = find_successful_workflow_run(owner, repo_name, current.hexsha)
        if workflow_run is not None:
            if current.hexsha != head_sha:
                show_alert(
                    "Could not find a successful %s workflow run for %s at commit %s; using commit %s."
                    % (EDITOR_WORKFLOW_FILE, repo_name, head_sha, current.hexsha)
                )
            return workflow_run
        if not current.parents:
            break
        current = current.parents[0]
    return None

def download_doriax_editor(repo_url, repo_dir):
    owner, repo_name = parse_github_repo(repo_url)
    repo = git.Repo(repo_dir)
    head_commit = repo.head.commit
    head_sha = head_commit.hexsha
    artifact_name = get_editor_artifact_name()
    executable_name = get_editor_executable_name()

    workflow_run = find_successful_workflow_run_in_history(owner, repo_name, head_commit)
    if workflow_run is None:
        sys.exit(
            "Error: Could not find a successful %s workflow run for %s at commit %s or any previous commit"
            % (EDITOR_WORKFLOW_FILE, repo_name, head_sha)
        )

    artifacts = github_api_get_json(workflow_run['artifacts_url']).get('artifacts', [])
    artifact = next(
        (item for item in artifacts if item.get('name') == artifact_name and not item.get('expired')),
        None
    )
    if artifact is None:
        artifact_list = ', '.join(item.get('name', '<unknown>') for item in artifacts) or '<none>'
        sys.exit(
            "Error: Could not find artifact %s for workflow run %s. Available artifacts: %s"
            % (artifact_name, workflow_run.get('html_url', workflow_run['url']), artifact_list)
        )

    download_dir = os.path.abspath(os.path.join('tools', 'doriax-editor', artifact_name))
    if os.path.exists(download_dir) and os.path.isdir(download_dir):
        shutil.rmtree(download_dir)
    os.makedirs(download_dir)

    archive_path = os.path.join(download_dir, artifact_name + '.zip')
    download_url = 'https://nightly.link/%s/%s/actions/artifacts/%s.zip' % (owner, repo_name, artifact['id'])
    print("Downloading doriax-editor artifact: %s" % artifact_name, flush=True)
    download_file(download_url, archive_path)

    extract_zip(archive_path, download_dir)
    os.remove(archive_path)
    unpack_nested_tarballs(download_dir)

    editor_path = find_editor_executable(download_dir, executable_name)
    if editor_path is None:
        sys.exit("Error: Artifact %s does not contain %s" % (artifact_name, executable_name))

    if os.name != 'nt':
        os.chmod(editor_path, stat.S_IMODE(os.stat(editor_path).st_mode) | stat.S_IXUSR)

    return download_dir, editor_path

def build_doriax_shaders(repo_url, repo_dir):
    doriax_root = os.path.abspath(os.path.join(repo_dir, 'engine'))
    shaders_dir = os.path.join(doriax_root, 'shaders')
    if os.path.exists(shaders_dir) and os.path.isdir(shaders_dir):
        shutil.rmtree(shaders_dir)
    os.makedirs(shaders_dir)

    editor_root, editor_path = download_doriax_editor(repo_url, repo_dir)
    shader_builder = os.path.abspath(os.path.join('..', 'build_all_shaders.sh'))
    env = os.environ.copy()
    env['DORIAX_EDITOR'] = editor_path

    print("Building shader headers with doriax-editor...", flush=True)
    subprocess.run(['bash', shader_builder, shaders_dir], cwd=editor_root, env=env).check_returncode()

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

def build_test(project_name, project_path, app_name, language, tests_repo, tests_ref, languages, output):

    print("Building test: %s, language: %s" % (project_name, language), flush=True)

    doriax_root = os.path.abspath(os.path.join('doriax', 'engine'))
    project_cmake_dir = doriax_root

    tests_root = os.path.join('samples')
    
    test_path = os.path.abspath(os.path.join(tests_root, project_path))
    staged_test_path = os.path.abspath('project_web')
    # Give staged sources fresh mtimes so the stable target recompiles the
    # project's own changed files while retaining the engine object files.
    copyResourcesDir(test_path, staged_test_path, shutil.copy)

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
    tests_owner, tests_repo_name = parse_github_repo(tests_repo)
    github_main_project = 'https://github.com/' + tests_owner + '/' + tests_repo_name + '/blob/' + tests_ref + '/' + project_path
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

    if language == 'cpp':
        compile_defs = '-DNO_LUA_INIT'
    else:
        compile_defs = '-DNO_CPP_INIT'

    emscripten_toolchain = find_emscripten_toolchain()

    cmake_args = [
        'cmake',
        '-S', project_cmake_dir,
        '-B', build_dir,
        '-DCMAKE_TOOLCHAIN_FILE=' + emscripten_toolchain,
        '-DCMAKE_BUILD_TYPE=Release',
        # Doriax exposes APP_NAME as a global compile definition. Keep it stable
        # so changing samples does not invalidate every engine object file.
        '-DAPP_NAME=' + BUILD_TARGET_NAME,
        '-DDORIAX_ROOT=' + doriax_root,
        # Keep the project root path stable so the engine target can reuse compiled objects.
        '-DPROJECT_ROOT=' + staged_test_path,
        '-DEM_ADDITIONAL_LINK_FLAGS=--shell-file ' + shell_file,
        '-DCMAKE_CXX_FLAGS=' + compile_defs,
        '-DCMAKE_C_FLAGS=' + compile_defs,
    ]

    subprocess.run(cmake_args).check_returncode()

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
        os.path.join(dst_dir, BUILD_TARGET_NAME+'.html'),
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

    build_doriax_shaders(doriaxRepo, 'doriax')

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
                build_test(test_name, test_path, test_app, lang, testsRepo, testsRef, test_langs, test_output)


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
