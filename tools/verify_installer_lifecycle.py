"""Opt-in Windows installer/manager integration test, using disposable data only.

Requires TWO distinct frozen packages and increasing release versions. Nothing
runs on import. See --help for the explicit sandbox opt-in and required inputs.
The real manager and installer lifecycle code run under a unique test AppId.
Only WebView2 detection is stubbed; this is NOT clean-PC/runtime or native UI
acceptance. Tests retain their data, logs, and JSON evidence for inspection.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_APP_ID = 'B1A827F6-93A7-4365-A494-D793125179DA'
RUNTIME = 'MicrosoftEdgeWebView2RuntimeInstallerX64.exe'
APP_EXE = 'StoryAtlasPreview.exe'


def require(condition, message):
    # These checks must still run when Python is invoked with -O.
    if not condition:
        raise RuntimeError(message)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def version_tuple(value):
    require(re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', value),
            'Versions must contain three numeric components, for example 0.1.2.')
    result = tuple(map(int, value.split('.')))
    require(all(component <= 65535 for component in result), 'Version components exceed the Windows limit.')
    return result


def within(path, parent):
    path, parent = Path(path).resolve(), Path(parent).resolve()
    require(path != parent and parent in path.parents, f'Path is outside the disposable sandbox: {path}')
    return path


def inventory_payload(folder):
    folder = Path(folder).resolve()
    require(folder.is_dir(), f'Frozen payload directory is missing: {folder}')
    require((folder / APP_EXE).is_file(), f'Frozen payload lacks {APP_EXE}: {folder}')
    result = {}
    for path in sorted(folder.rglob('*')):
        require(not path.is_symlink() and not getattr(path, 'is_junction', lambda: False)(),
                f'Payload links/junctions are not allowed: {path}')
        within(path, folder)
        if path.is_file():
            result[path.relative_to(folder).as_posix()] = digest(path)
    with (folder / APP_EXE).open('rb') as executable:
        require(executable.read(2) == b'MZ', 'Payload executable is not a Windows PE file.')
    require(not any(re.fullmatch(r'unins\d+\.(?:exe|dat|msg)', name, re.I) for name in result),
            'Use a frozen package, not an installed app directory containing an uninstaller.')
    return result


def validate_upgrade(old_version, new_version, old_files, new_files):
    require(version_tuple(old_version) < version_tuple(new_version),
            'The new version must be greater than the old version.')
    changed = sorted(name for name in old_files.keys() & new_files.keys()
                     if old_files[name] != new_files[name])
    require(changed, 'Old and new payloads need at least one changed shared file; identical reinstall is not an upgrade test.')
    return changed


@dataclass(frozen=True)
class Sandbox:
    folder: Path
    identity: str

    def __post_init__(self):
        require(self.folder.is_absolute(), 'Sandbox folder must be an absolute path.')
        require(str(uuid.UUID(self.identity)).upper() == self.identity, 'Sandbox AppId must be an uppercase UUID.')
        require(self.identity != PRODUCTION_APP_ID, 'Production AppId is forbidden in lifecycle tests.')
        require(self.folder.name == 'lifecycle-' + self.identity.lower(), 'Sandbox folder must match its unique AppId.')
        require(not any(c in str(self.folder) for c in '\r\n"{}'), 'Sandbox path contains unsupported installer syntax.')

    @property
    def custom_app(self):
        return self.folder / 'custom install path' / 'Story Atlas Preview'

    @property
    def default_app(self):
        return self.folder / 'default app'

    @property
    def data(self):
        return self.folder / 'stories-and-backups'

    @property
    def registry_key(self):
        return 'Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{' + self.identity + '}_is1'


def replace_directive(text, name, value):
    text, count = re.subn(r'^' + re.escape(name) + r'=.*$', lambda _: name + '=' + value, text, flags=re.M)
    require(count == 1, f'Expected exactly one installer {name} directive, got {count}.')
    return text


def render_definition(definition, repository, sandbox, payload, output_dir, version, default_app):
    """Rewrite only destinations/identity and runtime detection; retain other code."""
    for path in (payload, output_dir, default_app):
        within(path, sandbox.folder)
    require(PRODUCTION_APP_ID in definition, 'Installer production AppId was not found.')
    definition = definition.replace(PRODUCTION_APP_ID, sandbox.identity)
    definition = definition.replace('Story Atlas Preview', 'Story Atlas Lifecycle Test ' + sandbox.identity)
    definition = definition.replace('..\\dist\\StoryAtlasPreview\\*', str(payload / '*'))
    definition = definition.replace('..\\', str(repository) + os.sep)
    definition = replace_directive(definition, 'DefaultDirName', str(default_app))
    definition = replace_directive(definition, 'OutputDir', str(output_dir))
    definition = replace_directive(definition, 'OutputBaseFilename', setup_filename(version)[:-4])
    definition = definition.replace('{localappdata}\\StoryAtlasPreview', str(sandbox.data))
    definition = definition.replace('{userdesktop}', str(sandbox.folder / 'shortcuts' / 'desktop'))
    definition = definition.replace('{userprograms}', str(sandbox.folder / 'shortcuts' / 'start-menu'))
    definition, count = re.subn(r'^Source:.*' + re.escape(RUNTIME) + r'.*\n?', '', definition, flags=re.M)
    require(count == 1, 'Expected exactly one embedded WebView2 payload entry.')
    definition, count = re.subn(r'^function HasWebView2: Boolean;.*?^end;',
                              'function HasWebView2: Boolean;\nbegin\n'
                              '  // Lifecycle sandbox only: real runtime acceptance is a separate check.\n'
                              '  Result := True;\nend;', definition, flags=re.M | re.S)
    require(count == 1, 'Could not isolate WebView2 detection; refusing a broad [Code] removal.')
    require(not any(token in definition for token in (PRODUCTION_APP_ID, '{localappdata}', '{userdesktop}', '{userprograms}')),
            'Installer still contains a production destination; refusing to compile.')
    require('[Code]' in definition and 'function PrepareToInstall' in definition,
            'Installer lifecycle code must be preserved.')
    return definition


def setup_filename(version):
    version_tuple(version)
    return f'StoryAtlasPreview-{version}-Windows-x64-Offline-Setup.exe'


def render_manager(source, sandbox):
    require(source.count(PRODUCTION_APP_ID) == 1, 'Expected exactly one manager registry AppId.')
    return source.replace(PRODUCTION_APP_ID, sandbox.identity)


def ps_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def manager_wrapper(manager, action, sandbox, log):
    """Run manager logic unmodified, wrapping process launch for silent fixtures.

    The wrapper rejects every executable or /DIR outside this sandbox, even if
    the manager under test constructs an incorrect invocation. It never imports
    or queries the production app registration.
    """
    within(manager, sandbox.folder)
    within(log, sandbox.folder)
    require(action in ('Check', 'Install', 'Reinstall', 'Uninstall'), 'Unsupported manager test action.')
    return f"""$ErrorActionPreference = 'Stop'
$SandboxRoot = [IO.Path]::GetFullPath({ps_literal(sandbox.folder)}).TrimEnd('\\') + '\\'
function Assert-SandboxPath([string]$Path) {{
    $Full = [IO.Path]::GetFullPath($Path)
    if (!$Full.StartsWith($SandboxRoot, [StringComparison]::OrdinalIgnoreCase)) {{
        throw "Refusing a process or destination outside lifecycle sandbox: $Full"
    }}
}}
. {ps_literal(manager)}
function Start-Process {{
    param([string]$FilePath, [string[]]$ArgumentList, [switch]$Wait, [switch]$PassThru)
    Assert-SandboxPath $FilePath
    $Arguments = $ArgumentList -join ' '
    foreach ($Match in [regex]::Matches($Arguments, '(?i)/DIR=(?:"([^"]+)"|([^\\s]+))')) {{
        $Directory = if ($Match.Groups[1].Success) {{ $Match.Groups[1].Value }} else {{ $Match.Groups[2].Value }}
        Assert-SandboxPath $Directory
    }}
    $Arguments += ' /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /TASKS= /NOICONS'
    $Arguments += ' /LOG="' + {ps_literal(log)} + '"'
    Microsoft.PowerShell.Management\\Start-Process -FilePath $FilePath -ArgumentList $Arguments -Wait -PassThru
}}
try {{
    Invoke-InstallationAction -Action {ps_literal(action)}
    exit 0
}} catch {{
    Write-Error $_ -ErrorAction Continue
    exit 1
}}
"""


def read_registration(sandbox):
    import winreg  # Windows only; importing this module elsewhere is harmless.
    try:
        registry = winreg.OpenKey(winreg.HKEY_CURRENT_USER, sandbox.registry_key)
    except FileNotFoundError:
        return None
    with registry:
        return {name: winreg.QueryValueEx(registry, name)[0]
                for name in ('InstallLocation', 'UninstallString', 'DisplayVersion')}


def registered_app(sandbox, registration):
    app = within(registration['InstallLocation'], sandbox.folder)
    require(app in (sandbox.custom_app.resolve(), sandbox.default_app.resolve()), 'Unexpected registered installation directory.')
    return app


def registered_uninstaller(sandbox, registration):
    app = registered_app(sandbox, registration)
    match = re.fullmatch(r'"([^"\r\n]+[\\/]unins[0-9]+\.exe)"', registration['UninstallString'], re.I)
    require(match, 'Registered uninstall command is malformed.')
    executable = within(match[1], sandbox.folder)
    require(executable.parent == app, 'Uninstaller is outside the registered test app.')
    return executable


def seed_sentinels(sandbox):
    stories = sandbox.data / 'stories'
    require(stories.is_dir(), 'Setup did not install the example story directory.')
    story = stories / 'User story.atlas-preview'
    require(not story.exists(), 'Test story unexpectedly exists before seeding.')
    with closing(sqlite3.connect(story)) as connection, connection:
        connection.execute('CREATE TABLE sentinel (value TEXT)')
        connection.execute("INSERT INTO sentinel VALUES ('Keep my story')")
    backups = sandbox.data / 'backups'
    backups.mkdir()
    backup = backups / 'User backup.atlas-preview'
    backup.write_bytes(story.read_bytes())
    example = stories / 'Frankenstein.atlas-preview'
    require(example.is_file(), 'Setup did not install Frankenstein.')
    with closing(sqlite3.connect(example)) as connection, connection:
        connection.execute('CREATE TABLE lifecycle_user_edits (value TEXT)')
        connection.execute("INSERT INTO lifecycle_user_edits VALUES ('Edited example')")
    metadata = stories / 'portrait-sources.json'
    require(metadata.is_file(), 'Setup did not install example attribution metadata.')
    metadata.write_text(metadata.read_text(encoding='utf-8') + '\n', encoding='utf-8')
    # Include ALL seeded examples as well as personal story/backup/edited example.
    return {path.relative_to(sandbox.data).as_posix(): digest(path)
            for path in sandbox.data.rglob('*') if path.is_file()}


def verify_sentinels(sandbox, expected):
    for name, expected_hash in expected.items():
        path = within(sandbox.data / name, sandbox.data)
        require(path.is_file() and digest(path) == expected_hash, f'Persistent data changed or disappeared: {name}')


def verify_installation(sandbox, version, files, expected_app):
    registration = read_registration(sandbox)
    require(registration, 'Test install registration is missing.')
    app = registered_app(sandbox, registration)
    require(app == expected_app.resolve(), f'Wrong install location: {app}; expected {expected_app}')
    require(registration['DisplayVersion'] == version, 'Installed version does not match the tested release.')
    require(registered_uninstaller(sandbox, registration).is_file(), 'Registered test uninstaller is missing.')
    for name, expected_hash in files.items():
        path = within(app / name, app)
        require(path.is_file() and digest(path) == expected_hash, f'Installed payload differs from release: {name}')


def wait_for_removed(sandbox, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if read_registration(sandbox) is None and not any(
                (app / APP_EXE).exists() or list(app.glob('unins*.exe'))
                for app in (sandbox.custom_app, sandbox.default_app)):
            return
        time.sleep(0.1)
    raise RuntimeError('Test uninstall registration or executable remains.')


def run_manager(powershell, release, action, sandbox, label):
    registration = read_registration(sandbox)
    if registration:
        registered_uninstaller(sandbox, registration)
    wrapper = sandbox.folder / (label + '.ps1')
    wrapper.write_text(manager_wrapper(release / 'manage_installation.ps1', action, sandbox,
                                      sandbox.folder / (label + '.log')), encoding='utf-8-sig')
    result = subprocess.run([str(powershell), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                             '-File', str(wrapper)], capture_output=True, text=True, timeout=300)
    (sandbox.folder / (label + '-manager.txt')).write_text(result.stdout + result.stderr, encoding='utf-8')
    require(result.returncode == 0, f'Manager {action} failed; see {label}-manager.txt.')


def build_release(compiler, repository, sandbox, label, payload, version, default_app, manager_source):
    release = sandbox.folder / label
    release.mkdir()
    staged = sandbox.folder / (label + '-payload')
    shutil.copytree(payload, staged)
    definition = render_definition((repository / 'installer/StoryAtlasPreview.iss').read_text(encoding='utf-8'),
                                   repository, sandbox, staged, release, version, default_app)
    source = release / 'lifecycle.iss'
    source.write_text(definition, encoding='utf-8-sig')
    result = subprocess.run([str(compiler), '/Q', '/DAppVersion=' + version, str(source)],
                            capture_output=True, text=True, timeout=600)
    (release / 'compiler.txt').write_text(result.stdout + result.stderr, encoding='utf-8')
    require(result.returncode == 0, f'Fixture compilation failed; see {release / "compiler.txt"}.')
    setup = release / setup_filename(version)
    require(setup.is_file(), 'Fixture compiler did not produce the expected setup.')
    (release / 'manage_installation.ps1').write_text(render_manager(manager_source, sandbox), encoding='utf-8-sig')
    # Fixture metadata is never a published release or a claim about provenance.
    (release / 'release.json').write_text(json.dumps({'version': version, 'source_commit': '0' * 40,
        'installer': setup.name, 'sha256': digest(setup)}, indent=2) + '\n', encoding='utf-8')
    return release


def run_lifecycle(args):
    require(args.run_windows_sandbox, 'Use --run-windows-sandbox to opt into installation of disposable test fixtures.')
    require(sys.platform == 'win32', 'Native Windows is required; unit tests are available on other platforms.')
    require(sys.maxsize > 2**32, 'Use 64-bit Python to match the x64 installer and registry view.')
    compiler = args.compiler.resolve()
    powershell = shutil.which('powershell.exe')
    require(compiler.is_file(), f'Inno Setup compiler is missing: {compiler}')
    require(powershell, 'Windows PowerShell is required to exercise the installation manager.')
    old_files, new_files = inventory_payload(args.old_payload), inventory_payload(args.new_payload)
    changed = validate_upgrade(args.old_version, args.new_version, old_files, new_files)
    identity = str(uuid.uuid4()).upper()
    evidence_root = within(ROOT / 'build-verification', ROOT)
    require(not (ROOT / 'build-verification').is_symlink() and
            not getattr(ROOT / 'build-verification', 'is_junction', lambda: False)(),
            'Verification root must not be a symlink/junction.')
    sandbox = Sandbox(evidence_root / ('lifecycle-' + identity.lower()), identity)
    require(read_registration(sandbox) is None, 'Unique test AppId is unexpectedly already registered.')
    sandbox.folder.mkdir(parents=True, exist_ok=False)
    evidence = {'status': 'running', 'app_id': identity, 'platform': sys.platform,
                'old_version': args.old_version, 'new_version': args.new_version,
                'old_payload': str(args.old_payload.resolve()), 'new_payload': str(args.new_payload.resolve()),
                'changed_payload_files': changed, 'old_files': old_files, 'new_files': new_files,
                'phases': [], 'excluded': ['WebView2 runtime installation/detection (stubbed)',
                'native app launch/UI', 'network-disabled clean-machine acceptance',
                'desktop/Start menu shortcuts (redirected and suppressed)',
                'interactive cancellation (covered only by manager contract mocks)',
                'automatic removal of obsolete payload files during in-place update']}
    evidence_path = sandbox.folder / 'evidence.json'
    latest_release = None
    preserved = None
    try:
        # Dependency-free manager contracts include cancellation and custom paths.
        result = subprocess.run([powershell, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                                 '-File', str(ROOT / 'tests/test_installation_manager.ps1')],
                                capture_output=True, text=True, timeout=120)
        (sandbox.folder / 'manager-contracts.txt').write_text(result.stdout + result.stderr, encoding='utf-8')
        require(result.returncode == 0, 'Manager contract tests failed; see manager-contracts.txt.')
        evidence['phases'].append('manager mocked contracts')
        manager_source = (ROOT / 'installer/manage_installation.ps1').read_text(encoding='utf-8-sig')
        old = build_release(compiler, ROOT, sandbox, 'old', args.old_payload, args.old_version,
                            sandbox.custom_app, manager_source)
        new = build_release(compiler, ROOT, sandbox, 'new', args.new_payload, args.new_version,
                            sandbox.default_app, manager_source)
        latest_release = old
        run_manager(powershell, old, 'Check', sandbox, 'check-old')
        run_manager(powershell, old, 'Install', sandbox, 'install-old')
        verify_installation(sandbox, args.old_version, old_files, sandbox.custom_app)
        preserved = seed_sentinels(sandbox)
        evidence['preserved_files'] = preserved
        evidence['phases'].append('install old release into custom path and seed data')
        latest_release = new
        run_manager(powershell, new, 'Check', sandbox, 'check-new')
        run_manager(powershell, new, 'Install', sandbox, 'update-new')
        verify_installation(sandbox, args.new_version, new_files, sandbox.custom_app)
        verify_sentinels(sandbox, preserved)
        evidence['old_only_payload_after_upgrade'] = {name: {
            'remains': (sandbox.custom_app / name).is_file(),
            'sha256': digest(sandbox.custom_app / name) if (sandbox.custom_app / name).is_file() else None}
            for name in sorted(old_files.keys() - new_files.keys())}
        evidence['phases'].append('upgrade to distinct new version/payload at custom path')
        run_manager(powershell, new, 'Reinstall', sandbox, 'manager-reinstall')
        verify_installation(sandbox, args.new_version, new_files, sandbox.custom_app)
        verify_sentinels(sandbox, preserved)
        evidence['old_only_payload_after_reinstall'] = {name: (sandbox.custom_app / name).exists()
            for name in sorted(old_files.keys() - new_files.keys())}
        require(not any(evidence['old_only_payload_after_reinstall'].values()),
                'Manager reinstall left an obsolete installer-tracked payload file.')
        evidence['phases'].append('manager uninstall/reinstall preserves custom path and data')
        run_manager(powershell, new, 'Uninstall', sandbox, 'manager-uninstall')
        wait_for_removed(sandbox)
        verify_sentinels(sandbox, preserved)
        evidence['phases'].append('manager uninstall preserves data')
        run_manager(powershell, new, 'Install', sandbox, 'reinstall-after-removal')
        verify_installation(sandbox, args.new_version, new_files, sandbox.default_app)
        verify_sentinels(sandbox, preserved)
        evidence['phases'].append('install after removal preserves existing data')
        evidence['status'] = 'passed'
    except BaseException as error:
        evidence['status'] = 'failed'
        evidence['error'] = str(error)
        raise
    finally:
        try:
            if latest_release and read_registration(sandbox):
                run_manager(powershell, latest_release, 'Uninstall', sandbox, 'cleanup')
            wait_for_removed(sandbox)
            if preserved:
                verify_sentinels(sandbox, preserved)
            evidence['cleanup'] = 'test registration and app executables removed; data/evidence retained'
        except BaseException as error:
            evidence['cleanup_error'] = str(error)
            evidence['status'] = 'failed'
        finally:
            evidence_path.write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
            print('Evidence:', evidence_path)
    require(evidence['status'] == 'passed', 'Lifecycle verification or cleanup failed; inspect evidence.json.')
    print('PASS: manager install, distinct-version upgrade, custom-path reinstall, uninstall, reinstall; persistent data preserved.')
    print('NOT TESTED: real WebView2 bootstrap, native app/UI, interactive cancellation, clean/offline Windows acceptance.')
    return evidence_path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-windows-sandbox', action='store_true',
                        help='Explicitly allow disposable per-user fixture installs on Windows; never targets the production AppId.')
    parser.add_argument('--old-payload', type=Path, required=True, help='Previous frozen dist/StoryAtlasPreview directory.')
    parser.add_argument('--old-version', required=True, help='Version of the previous frozen payload.')
    parser.add_argument('--new-payload', type=Path, default=ROOT / 'dist/StoryAtlasPreview', help='New frozen package directory.')
    parser.add_argument('--new-version', help='New package version (defaults to root VERSION).')
    parser.add_argument('--compiler', type=Path, default=ROOT / 'build/inno/ISCC.exe', help='Path to the Inno Setup compiler.')
    args = parser.parse_args(argv)
    if not args.run_windows_sandbox:
        parser.error('--run-windows-sandbox is required; no installation was attempted.')
    try:
        if args.new_version is None:
            args.new_version = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
        run_lifecycle(args)
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print('FAIL:', error, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
