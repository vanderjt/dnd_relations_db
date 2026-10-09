"""Portable tests for lifecycle fixtures; never install, query the registry, or launch PowerShell."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from tools import verify_installer_lifecycle as lifecycle


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.identity = 'F02547EC-32CF-47B4-B628-97A17B4CF3F0'
        self.sandbox = lifecycle.Sandbox(self.root / ('lifecycle-' + self.identity.lower()), self.identity)
        self.sandbox.folder.mkdir()

    def payload(self, name, content=b'MZ old executable'):
        folder = self.root / name
        folder.mkdir()
        (folder / lifecycle.APP_EXE).write_bytes(content)
        (folder / '_internal').mkdir()
        (folder / '_internal' / 'index.html').write_text(name, encoding='utf-8')
        return folder

    def registration(self, app=None, version='0.1.2'):
        app = app or self.sandbox.custom_app
        return {'InstallLocation': str(app), 'UninstallString': f'"{app / "unins001.exe"}"',
                'DisplayVersion': version}

    def seed_examples(self):
        stories = self.sandbox.data / 'stories'
        stories.mkdir(parents=True)
        for name in ('Frankenstein', 'Dracula'):
            with contextlib.closing(sqlite3.connect(stories / (name + '.atlas-preview'))) as connection, connection:
                connection.execute('CREATE TABLE example (value TEXT)')
        (stories / 'portrait-sources.json').write_text('{}', encoding='utf-8')

    def test_import_has_no_filesystem_registry_or_process_side_effects(self):
        code = """
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
with patch.object(Path, 'mkdir', side_effect=AssertionError('mkdir at import')), \\
     patch.object(subprocess, 'run', side_effect=AssertionError('process at import')):
    import tools.verify_installer_lifecycle
assert 'winreg' not in sys.modules
"""
        result = subprocess.run([sys.executable, '-c', code], cwd=lifecycle.ROOT,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_no_opt_in_refuses_before_reading_inputs(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error, \
                patch.object(lifecycle, 'run_lifecycle') as run:
            lifecycle.main(['--old-payload', 'missing', '--old-version', '0.1.1'])
        self.assertEqual(error.exception.code, 2)
        run.assert_not_called()

    def test_native_guard_rejects_non_windows_before_any_process(self):
        with patch.object(lifecycle.sys, 'platform', 'linux'), \
                patch.object(lifecycle.subprocess, 'run') as run, \
                self.assertRaisesRegex(RuntimeError, 'Native Windows'):
            lifecycle.run_lifecycle(argparse.Namespace(run_windows_sandbox=True))
        run.assert_not_called()

    def test_direct_call_also_requires_opt_in(self):
        with self.assertRaisesRegex(RuntimeError, 'opt into'):
            lifecycle.run_lifecycle(argparse.Namespace(run_windows_sandbox=False))

    def test_upgrade_requires_increasing_numeric_version(self):
        self.assertEqual(lifecycle.validate_upgrade('0.1.9', '0.1.10', {'app': 'old'}, {'app': 'new'}), ['app'])
        for old, new in [('0.1.2', '0.1.2'), ('0.2.0', '0.1.99')]:
            with self.subTest(old=old, new=new), self.assertRaisesRegex(RuntimeError, 'greater'):
                lifecycle.validate_upgrade(old, new, {'app': 'old'}, {'app': 'new'})

    def test_invalid_versions_are_rejected(self):
        for version in ('1.2', '1.2.3.4', '01.2.3', '1.2.3-beta', '1.2.65536', '1.2.3\n', '/DIR=C:\\data'):
            with self.subTest(version=version), self.assertRaises(RuntimeError):
                lifecycle.version_tuple(version)

    def test_upgrade_rejects_identical_payload_or_only_new_file(self):
        for new in ({'app': 'same'}, {'app': 'same', 'marker': 'new'}):
            with self.subTest(new=new), self.assertRaisesRegex(RuntimeError, 'changed shared file'):
                lifecycle.validate_upgrade('0.1.1', '0.1.2', {'app': 'same'}, new)

    def test_inventory_hashes_nested_payload_files(self):
        folder = self.payload('old')
        inventory = lifecycle.inventory_payload(folder)
        self.assertEqual(set(inventory), {lifecycle.APP_EXE, '_internal/index.html'})
        self.assertEqual(inventory[lifecycle.APP_EXE], lifecycle.digest(folder / lifecycle.APP_EXE))

    def test_inventory_rejects_missing_non_pe_and_installed_payloads(self):
        with self.assertRaisesRegex(RuntimeError, 'missing'):
            lifecycle.inventory_payload(self.root / 'missing')
        folder = self.payload('not-pe', b'version https://git-lfs.github.com/spec/v1')
        with self.assertRaisesRegex(RuntimeError, 'Windows PE'):
            lifecycle.inventory_payload(folder)
        folder = self.payload('installed')
        (folder / 'unins001.exe').write_bytes(b'MZ uninstaller')
        with self.assertRaisesRegex(RuntimeError, 'installed app'):
            lifecycle.inventory_payload(folder)

    def test_inventory_rejects_symlink(self):
        folder = self.payload('linked')
        try:
            (folder / 'linked.html').symlink_to(folder / '_internal' / 'index.html')
        except OSError:
            self.skipTest('This host does not permit creating test symlinks.')
        with self.assertRaisesRegex(RuntimeError, 'links/junctions'):
            lifecycle.inventory_payload(folder)

    def test_path_fence_rejects_parent_sibling_prefix_and_traversal(self):
        for candidate in (self.sandbox.folder, self.root, Path(str(self.sandbox.folder) + '-other'),
                          self.sandbox.folder / '..' / 'outside'):
            with self.subTest(candidate=candidate), self.assertRaisesRegex(RuntimeError, 'outside'):
                lifecycle.within(candidate, self.sandbox.folder)
        self.assertEqual(lifecycle.within(self.sandbox.custom_app, self.sandbox.folder), self.sandbox.custom_app.resolve())

    def test_path_fence_resolves_links_before_allowing(self):
        try:
            (self.sandbox.folder / 'escape').symlink_to(self.root, target_is_directory=True)
        except OSError:
            self.skipTest('This host does not permit creating test symlinks.')
        with self.assertRaisesRegex(RuntimeError, 'outside'):
            lifecycle.within(self.sandbox.folder / 'escape' / 'file', self.sandbox.folder)

    def test_sandbox_cannot_target_production_registration(self):
        app_id = lifecycle.PRODUCTION_APP_ID
        with self.assertRaisesRegex(RuntimeError, 'Production AppId'):
            lifecycle.Sandbox(self.root / ('lifecycle-' + app_id.lower()), app_id)
        with self.assertRaisesRegex(RuntimeError, 'unique AppId'):
            lifecycle.Sandbox(self.root / 'app', self.identity)

    def definition(self, text=None):
        if text is None:
            text = (lifecycle.ROOT / 'installer/StoryAtlasPreview.iss').read_text(encoding='utf-8')
        return lifecycle.render_definition(text, lifecycle.ROOT, self.sandbox,
            self.sandbox.folder / 'new-payload', self.sandbox.folder / 'new', '0.1.2', self.sandbox.default_app)

    def test_definition_retains_code_but_isolates_all_destinations(self):
        source = (lifecycle.ROOT / 'installer/StoryAtlasPreview.iss').read_text(encoding='utf-8')
        source += '\nfunction LifecycleControlMustRemain: Boolean;\nbegin\n  Result := False;\nend;\n'
        result = self.definition(source)
        self.assertIn('function PrepareToInstall', result)
        self.assertIn('function LifecycleControlMustRemain', result)
        self.assertIn('Result := True;', result)
        self.assertIn('AppId={{' + self.identity + '}', result)
        self.assertIn('DefaultDirName=' + str(self.sandbox.default_app), result)
        self.assertIn(str(self.sandbox.data), result)
        self.assertIn(str(self.sandbox.folder / 'shortcuts'), result)
        self.assertNotIn('Source: "..\\dist', result)
        self.assertNotIn('RegQueryStringValue', result)
        self.assertFalse(any(lifecycle.RUNTIME in line for line in result.splitlines() if line.startswith('Source:')))
        for token in ('{localappdata}', '{userdesktop}', '{userprograms}', lifecycle.PRODUCTION_APP_ID):
            self.assertNotIn(token, result)

    def test_definition_fails_closed_when_runtime_hook_changes(self):
        source = (lifecycle.ROOT / 'installer/StoryAtlasPreview.iss').read_text(encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError, 'Could not isolate'):
            self.definition(source.replace('function HasWebView2:', 'function RuntimeAvailable:'))

    def test_definition_rejects_new_production_destinations(self):
        source = (lifecycle.ROOT / 'installer/StoryAtlasPreview.iss').read_text(encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError, 'production destination'):
            self.definition(source + '\n; {localappdata}\\UnexpectedData\n')

    def test_definition_rejects_non_sandbox_output(self):
        source = (lifecycle.ROOT / 'installer/StoryAtlasPreview.iss').read_text(encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError, 'outside'):
            lifecycle.render_definition(source, lifecycle.ROOT, self.sandbox, self.root / 'outside',
                                        self.sandbox.folder / 'new', '0.1.2', self.sandbox.custom_app)

    def test_directive_rewrite_rejects_missing_or_duplicate(self):
        for text in ('Other=1', 'OutputDir=a\nOutputDir=b'):
            with self.assertRaisesRegex(RuntimeError, 'exactly one'):
                lifecycle.replace_directive(text, 'OutputDir', 'sandbox')

    def test_manager_copy_uses_only_unique_registration(self):
        source = (lifecycle.ROOT / 'installer/manage_installation.ps1').read_text(encoding='utf-8-sig')
        result = lifecycle.render_manager(source, self.sandbox)
        self.assertNotIn(lifecycle.PRODUCTION_APP_ID, result)
        self.assertIn(self.identity, result)
        self.assertEqual(result.replace(self.identity, lifecycle.PRODUCTION_APP_ID), source)
        with self.assertRaisesRegex(RuntimeError, 'exactly one'):
            lifecycle.render_manager('no AppId', self.sandbox)

    def test_process_wrapper_fences_paths_and_calls_actual_manager(self):
        wrapper = lifecycle.manager_wrapper(self.sandbox.folder / 'new' / 'manage_installation.ps1',
                                            'Reinstall', self.sandbox, self.sandbox.folder / 'test.log')
        self.assertIn("Invoke-InstallationAction -Action 'Reinstall'", wrapper)
        self.assertIn('Assert-SandboxPath $FilePath', wrapper)
        self.assertIn('Assert-SandboxPath $Directory', wrapper)
        self.assertIn('Microsoft.PowerShell.Management\\Start-Process', wrapper)
        self.assertIn('/VERYSILENT /SUPPRESSMSGBOXES', wrapper)
        self.assertNotIn(lifecycle.PRODUCTION_APP_ID, wrapper)
        self.assertEqual(lifecycle.ps_literal("C:\\O'Brien\\app"), "'C:\\O''Brien\\app'")

    def test_registered_uninstaller_must_be_quoted_and_inside_known_app(self):
        self.assertEqual(lifecycle.registered_uninstaller(self.sandbox, self.registration()),
                         (self.sandbox.custom_app / 'unins001.exe').resolve())
        for command in ('unins001.exe', '"C:\\Windows\\unins001.exe"',
                        f'"{self.sandbox.default_app / "unins001.exe"}"',
                        f'"{self.sandbox.custom_app / "unins001.exe"}" /SILENT'):
            with self.subTest(command=command), self.assertRaises(RuntimeError):
                lifecycle.registered_uninstaller(self.sandbox, {**self.registration(), 'UninstallString': command})
        with self.assertRaisesRegex(RuntimeError, 'Unexpected registered'):
            lifecycle.registered_app(self.sandbox, self.registration(app=self.sandbox.folder / 'unexpected'))

    def test_sentinels_cover_story_backup_edited_example_and_metadata(self):
        self.seed_examples()
        before_example = lifecycle.digest(self.sandbox.data / 'stories/Frankenstein.atlas-preview')
        sentinels = lifecycle.seed_sentinels(self.sandbox)
        self.assertEqual(set(sentinels), {'stories/User story.atlas-preview', 'backups/User backup.atlas-preview',
            'stories/Frankenstein.atlas-preview', 'stories/Dracula.atlas-preview', 'stories/portrait-sources.json'})
        self.assertNotEqual(sentinels['stories/Frankenstein.atlas-preview'], before_example)
        self.assertEqual(sentinels['stories/User story.atlas-preview'], sentinels['backups/User backup.atlas-preview'])
        lifecycle.verify_sentinels(self.sandbox, sentinels)
        for name in ('stories/User story.atlas-preview', 'backups/User backup.atlas-preview',
                     'stories/Frankenstein.atlas-preview', 'stories/portrait-sources.json'):
            path = self.sandbox.data / name
            before = path.read_bytes()
            path.write_bytes(before + b'changed')
            with self.subTest(name=name), self.assertRaisesRegex(RuntimeError, 'Persistent data'):
                lifecycle.verify_sentinels(self.sandbox, sentinels)
            path.write_bytes(before)

    def test_sentinels_detect_missing_example(self):
        self.seed_examples()
        sentinels = lifecycle.seed_sentinels(self.sandbox)
        (self.sandbox.data / 'stories/Dracula.atlas-preview').unlink()
        with self.assertRaisesRegex(RuntimeError, 'disappeared'):
            lifecycle.verify_sentinels(self.sandbox, sentinels)

    def test_installation_checks_version_destination_and_all_bytes(self):
        app = self.sandbox.custom_app
        app.mkdir(parents=True)
        executable = app / lifecycle.APP_EXE
        executable.write_bytes(b'new')
        (app / 'unins001.exe').write_bytes(b'MZ test uninstaller')
        files = {lifecycle.APP_EXE: lifecycle.digest(executable)}
        with patch.object(lifecycle, 'read_registration', return_value=self.registration()):
            lifecycle.verify_installation(self.sandbox, '0.1.2', files, app)
            with self.assertRaisesRegex(RuntimeError, 'version'):
                lifecycle.verify_installation(self.sandbox, '0.1.1', files, app)
            with self.assertRaisesRegex(RuntimeError, 'location'):
                lifecycle.verify_installation(self.sandbox, '0.1.2', files, self.sandbox.default_app)
            executable.write_bytes(b'old')
            with self.assertRaisesRegex(RuntimeError, 'payload differs'):
                lifecycle.verify_installation(self.sandbox, '0.1.2', files, app)

    def test_uninstall_wait_requires_registration_and_executable_removal(self):
        with patch.object(lifecycle, 'read_registration', return_value=None):
            lifecycle.wait_for_removed(self.sandbox)
        with self.assertRaisesRegex(RuntimeError, 'remains'):
            lifecycle.wait_for_removed(self.sandbox, timeout=0)


    def test_release_fixture_stages_copy_and_supplies_version_to_compiler(self):
        source_payload = self.payload('source-old')
        original = lifecycle.inventory_payload(source_payload)
        manager = (lifecycle.ROOT / 'installer/manage_installation.ps1').read_text(encoding='utf-8-sig')

        def fake_compile(arguments, **kwargs):
            self.assertIn('/DAppVersion=0.1.1', arguments)
            source = Path(arguments[-1])
            self.assertTrue(source.is_file())
            self.assertIn('DefaultDirName=' + str(self.sandbox.custom_app), source.read_text(encoding='utf-8-sig'))
            (source.parent / lifecycle.setup_filename('0.1.1')).write_bytes(b'MZ test installer fixture')
            return Mock(returncode=0, stdout='compile fixture', stderr='')

        with patch.object(lifecycle.subprocess, 'run', side_effect=fake_compile) as compile_setup:
            release = lifecycle.build_release(self.root / 'ISCC.exe', lifecycle.ROOT, self.sandbox,
                'old', source_payload, '0.1.1', self.sandbox.custom_app, manager)
        compile_setup.assert_called_once()
        metadata = json.loads((release / 'release.json').read_text(encoding='utf-8'))
        self.assertEqual(metadata['version'], '0.1.1')
        self.assertEqual(metadata['sha256'], lifecycle.digest(release / metadata['installer']))
        self.assertEqual(lifecycle.inventory_payload(self.sandbox.folder / 'old-payload'), original)
        self.assertEqual(lifecycle.inventory_payload(source_payload), original)
        self.assertNotIn(lifecycle.PRODUCTION_APP_ID, (release / 'manage_installation.ps1').read_text(encoding='utf-8-sig'))

    def lifecycle_mocks(self, *, action_failure=None, cleanup_failure=None):
        """Exercise orchestration with every OS/process boundary replaced."""
        compiler = self.root / 'ISCC.exe'
        compiler.write_bytes(b'not executed')
        args = argparse.Namespace(run_windows_sandbox=True, compiler=compiler,
            old_payload=self.root / 'old-input', new_payload=self.root / 'new-input',
            old_version='0.1.1', new_version='0.1.2')
        installer = self.root / 'installer'
        installer.mkdir()
        (installer / 'manage_installation.ps1').write_text('fixture manager', encoding='utf-8')
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        replacements = {
            'ROOT': self.root,
            'inventory_payload': Mock(side_effect=[{'app': 'old', 'obsolete': 'old-only'}, {'app': 'new'}]),
            'read_registration': Mock(return_value=None),
            'build_release': Mock(side_effect=[self.root / 'old', self.root / 'new']),
            'run_manager': Mock(side_effect=action_failure),
            'verify_installation': Mock(),
            'seed_sentinels': Mock(return_value={'stories/story': 'sentinel'}),
            'verify_sentinels': Mock(),
            'wait_for_removed': Mock(side_effect=cleanup_failure),
        }
        for name, replacement in replacements.items():
            stack.enter_context(patch.object(lifecycle, name, replacement))
        stack.enter_context(patch.object(lifecycle.sys, 'platform', 'win32'))
        stack.enter_context(patch.object(lifecycle.shutil, 'which', return_value='test-powershell'))
        stack.enter_context(patch.object(lifecycle.subprocess, 'run', return_value=Mock(returncode=0, stdout='pass', stderr='')))
        stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        return args, replacements

    def test_orchestration_requests_expected_manager_actions_and_records_limits(self):
        args, mocks = self.lifecycle_mocks()
        evidence = json.loads(lifecycle.run_lifecycle(args).read_text(encoding='utf-8'))
        self.assertEqual(evidence['status'], 'passed')
        self.assertEqual(evidence['changed_payload_files'], ['app'])
        self.assertEqual(evidence['old_only_payload_after_upgrade']['obsolete']['remains'], False)
        self.assertEqual(evidence['old_only_payload_after_reinstall'], {'obsolete': False})
        self.assertTrue(any('WebView2' in item for item in evidence['excluded']))
        self.assertTrue(any('interactive cancellation' in item for item in evidence['excluded']))
        self.assertEqual([call.args[2] for call in mocks['run_manager'].call_args_list],
                         ['Check', 'Install', 'Check', 'Install', 'Reinstall', 'Uninstall', 'Install'])
        # Both version bytes and path are checked after old install, upgrade,
        # custom-path reinstall, and a fresh install after full removal.
        self.assertEqual([call.args[1] for call in mocks['verify_installation'].call_args_list],
                         ['0.1.1', '0.1.2', '0.1.2', '0.1.2'])
        paths = [call.args[3].name for call in mocks['verify_installation'].call_args_list]
        self.assertEqual(paths, ['Story Atlas Preview', 'Story Atlas Preview', 'Story Atlas Preview', 'default app'])
        self.assertEqual(mocks['verify_sentinels'].call_count, 5)

    def test_orchestration_records_failure_without_claiming_pass(self):
        args, mocks = self.lifecycle_mocks(action_failure=RuntimeError('simulated setup failure'))
        with self.assertRaisesRegex(RuntimeError, 'simulated setup failure'):
            lifecycle.run_lifecycle(args)
        report = next((self.root / 'build-verification').glob('lifecycle-*/evidence.json'))
        evidence = json.loads(report.read_text(encoding='utf-8'))
        self.assertEqual(evidence['status'], 'failed')
        self.assertIn('simulated setup failure', evidence['error'])
        mocks['wait_for_removed'].assert_called_once()

    def test_cleanup_failure_is_recorded_and_prevents_success(self):
        args, _ = self.lifecycle_mocks(cleanup_failure=[None, RuntimeError('simulated cleanup failure')])
        with self.assertRaisesRegex(RuntimeError, 'cleanup failed'):
            lifecycle.run_lifecycle(args)
        report = next((self.root / 'build-verification').glob('lifecycle-*/evidence.json'))
        evidence = json.loads(report.read_text(encoding='utf-8'))
        self.assertEqual(evidence['status'], 'failed')
        self.assertEqual(evidence['cleanup_error'], 'simulated cleanup failure')


if __name__ == '__main__':
    unittest.main()
