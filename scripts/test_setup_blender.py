#!/usr/bin/env python3
"""Offline failure-path tests; real installation/render is a separate macOS check."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import setup_blender as setup


class BlenderSetupTests(unittest.TestCase):
    def test_missing_blender_records_failure_without_downloading(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(setup.platform, 'platform', return_value='test-macOS'), patch.object(setup.subprocess, 'run') as run, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                result = setup.main(['--home', directory, '--blender', str(root/'missing')])
            self.assertEqual(result, 1)
            run.assert_not_called()
            report = json.loads((root/'setup-result.json').read_text())
            self.assertFalse(report['ok'])
            self.assertIn('Blender executable not found', report['error'])

    def test_activated_path_does_not_select_own_launcher_on_rerun(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            launcher = root/'managed/blender'
            setup.write_wrapper(launcher, 'exit 0')
            real = root/'actual/blender'
            real.parent.mkdir()
            real.write_text('#!/bin/sh\nexit 0\n')
            real.chmod(0o755)
            with patch.dict(os.environ, {'PATH': str(launcher.parent)+os.pathsep+str(real.parent)}):
                self.assertEqual(setup.find_blender(), real.resolve())
            with self.assertRaises(ValueError):
                setup.find_blender(str(launcher))

    def test_wrapper_preserves_space_chinese_and_shell_arguments(self):
        with tempfile.TemporaryDirectory(prefix='Blender 空格 ') as directory:
            path = Path(directory)/'command'
            setup.write_wrapper(path, 'exec /usr/bin/printf "%s\\n" "$@"')
            args = ['two words', '中文', '$(do-not-execute)', 'a; b', 'single\'quote']
            result = subprocess.run([str(path), *args], capture_output=True, text=True, check=True)
            self.assertEqual(result.stdout.splitlines(), args)
            setup.write_wrapper(path, 'exit 0')  # Our own wrapper can be updated.

    def test_does_not_replace_existing_command_or_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'command'
            path.write_text('existing tool')
            with self.assertRaises(ValueError):
                setup.write_wrapper(path, 'exit 0')
            self.assertEqual(path.read_text(), 'existing tool')
            link = Path(directory)/'link'
            link.symlink_to(path)
            with self.assertRaises(ValueError):
                setup.write_wrapper(link, 'exit 0')

    def test_successful_commands_without_real_image_are_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            def fake_run(command, **kwargs):
                if command[-2:] == ['scene', 'json']:
                    return json.dumps({'objects': [{'name': 'ProductBox'}]})
                if 'execute' in command:
                    return json.dumps({'script_path': str(Path(directory)/'generated.py')})
                return '{}'
            with self.assertRaises(FileNotFoundError):
                setup.smoke_test(fake_run, 'cli', 'blender', Path(directory))

    def test_invalid_or_truncated_png_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'smoke.png'
            for data in (b'', b'not a render', b'\x89PNG\r\n\x1a\n'):
                path.write_bytes(data)
                with self.assertRaises(ValueError):
                    setup.png_size(path)


if __name__ == '__main__':
    unittest.main(verbosity=2)
