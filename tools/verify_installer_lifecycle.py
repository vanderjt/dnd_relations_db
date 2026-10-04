"""Exercise Setup with a unique test AppId and disposable app/story directories.

Uses the real frozen payload, but omits the offline WebView2 bootstrapper: this
checks install/update/uninstall/reinstall behavior, not clean-PC runtime setup.
Never installs over the user's Story Atlas registration or touches their data.
"""
import hashlib
from pathlib import Path
import sqlite3
import subprocess
import time
import uuid
import winreg

ROOT = Path(__file__).resolve().parents[1]
identity = str(uuid.uuid4()).upper()
folder = ROOT / 'build-verification' / ('lifecycle-' + identity.lower())
folder.mkdir(parents=True)
app = folder / 'app'
data = folder / 'stories-and-backups'
setup = folder / 'Lifecycle-Setup.exe'
definition = (ROOT / 'installer/StoryAtlasPreview.iss').read_text(encoding='utf-8')
definition = definition.split('[Code]')[0]
definition = '\n'.join(line for line in definition.splitlines()
                       if 'MicrosoftEdgeWebView2RuntimeInstallerX64.exe' not in line)
definition = definition.replace('B1A827F6-93A7-4365-A494-D793125179DA', identity)
definition = definition.replace('Story Atlas Preview', 'Story Atlas Lifecycle Test ' + identity)
definition = definition.replace('..\\', str(ROOT) + '\\')
definition = definition.replace('OutputDir=.', 'OutputDir=' + str(folder))
definition = definition.replace('OutputBaseFilename=StoryAtlasPreview-{#AppVersion}-Windows-x64-Offline-Setup',
                                'OutputBaseFilename=Lifecycle-Setup')
definition = definition.replace('DefaultDirName={localappdata}\\Programs\\Story Atlas Lifecycle Test ' + identity,
                                'DefaultDirName=' + str(app))
definition = definition.replace('{localappdata}\\StoryAtlasPreview', str(data))
source = folder / 'lifecycle.iss'
source.write_text(definition, encoding='utf-8')
subprocess.run([str(ROOT / 'build/inno/ISCC.exe'), '/Q', str(source)], check=True)

key = 'Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{' + identity + '}_is1'


def registered():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as registry:
            return winreg.QueryValueEx(registry, 'InstallLocation')[0]
    except FileNotFoundError:
        return None


def install(label):
    subprocess.run([str(setup), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                    '/TASKS=', '/DIR=' + str(app), '/LOG=' + str(folder / (label + '.log'))], check=True)
    assert Path(registered()).resolve() == app.resolve(), 'Incorrect test registration'
    assert digest(app / 'StoryAtlasPreview.exe') == digest(ROOT / 'dist/StoryAtlasPreview/StoryAtlasPreview.exe')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def uninstall():
    executable = None
    if registered():
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as registry:
            executable = Path(winreg.QueryValueEx(registry, 'UninstallString')[0].strip('"'))
        assert executable.parent.resolve() == app.resolve(), 'Uninstaller outside test app'
        subprocess.run([str(executable), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'], check=True)
    # Inno hands uninstall off to a temporary executable; wait for that process.
    deadline = time.monotonic() + 15
    while (registered() is not None or (executable and executable.exists())) and time.monotonic() < deadline:
        time.sleep(0.1)
    assert registered() is None, 'Test uninstall registration remains'
    assert not (app / 'StoryAtlasPreview.exe').exists(), 'App executable remains'


try:
    install('install')
    story = data / 'stories' / 'User story.atlas-preview'
    with sqlite3.connect(story) as connection:
        connection.execute('CREATE TABLE sentinel (value TEXT)')
        connection.execute("INSERT INTO sentinel VALUES ('Keep my story')")
    backups = data / 'backups'
    backups.mkdir()
    backup = backups / 'User backup.atlas-preview'
    backup.write_bytes(story.read_bytes())
    example = data / 'stories' / 'Frankenstein.atlas-preview'
    with sqlite3.connect(example) as connection:
        connection.execute('CREATE TABLE user_edits (value TEXT)')
        connection.execute("INSERT INTO user_edits VALUES ('Edited example')")
    preserved = {path: digest(path) for path in (story, backup, example)}
    install('update')
    assert all(digest(path) == value for path, value in preserved.items()), 'Update changed story files'
    uninstall()
    assert all(digest(path) == value for path, value in preserved.items()), 'Uninstall changed story files'
    install('reinstall')
    assert all(digest(path) == value for path, value in preserved.items()), 'Reinstall changed story files'
finally:
    uninstall()
print('PASS: install, update, uninstall, reinstall; story, backup, and edited example preserved')
print('Evidence:', folder)
