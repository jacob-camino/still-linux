"""Source/packaging checks; these are not substitutes for a Linux build."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = '0d03416c32aab13c678f6d284956d4510b07ad86'
FIXTURE = os.environ.get('STILL_LINUX_FIXTURE')
PATCHES = sorted((ROOT / 'still/patches').glob('*.patch'))


def run(*argv, **kwargs):
    return subprocess.run(list(map(str, argv)), text=True, capture_output=True,
                          check=True, **kwargs)


def upstream(name):
    return run('git', '-C', ROOT, 'show', f'{UPSTREAM}:{name}').stdout


class LinuxIntegrationTests(unittest.TestCase):
    def test_shell_syntax_and_appstream_desktop_identity(self):
        run('bash', '-n', *[ROOT / name for name in (
            'scripts/shared.sh', 'scripts/dev.sh', 'scripts/package.sh', 'package/mkdeb.sh',
            'package/still-wrapper.sh', 'package/still-wrapper-appimage.sh')])
        metadata = ET.parse(ROOT / 'package/com.jacobcamino.still.metainfo.xml').getroot()
        self.assertEqual(metadata.findtext('id'), 'com.jacobcamino.still')
        self.assertEqual(metadata.findtext('launchable'), 'still.desktop')
        self.assertEqual(metadata.findtext('name'), 'Still')
        desktop = (ROOT / 'package/still.desktop').read_text()
        self.assertIn('\nName=Still\n', desktop)
        self.assertIn('\nExec=still %U\n', desktop)
        self.assertIn('\nIcon=still\n', desktop)

    def test_apparmor_and_launcher_changes_preserve_permission_semantics(self):
        expected = upstream('package/apparmor.cfg').replace('helium-bin', 'still-bin').replace('/opt/helium/', '/opt/still/')
        self.assertEqual((ROOT / 'package/apparmor.cfg').read_text(), expected)
        expected = upstream('package/helium-wrapper-appimage.sh').replace('Helium AppImage', 'Still AppImage').replace('helium-appimage', 'still-appimage').replace('Helium has', 'Still has').replace('Before Helium', 'Before Still').replace('/opt/helium/', '/opt/still/')
        self.assertEqual((ROOT / 'package/still-wrapper-appimage.sh').read_text(), expected)
        self.assertEqual((ROOT / 'package/still-wrapper.sh').read_text(), upstream('package/helium-wrapper.sh'))
        self.assertEqual((ROOT / 'flags.linux.gn').read_text(), upstream('flags.linux.gn'))

    @unittest.skipUnless(FIXTURE, 'set STILL_LINUX_FIXTURE to the prepared selected-file fixture')
    def test_archive_source_inside_wrapper_repo_is_really_patched_and_idempotent(self):
        # This deliberately sits under a parent Git repo, without its own .git.
        work = ROOT / 'still/.integration-work'
        work.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work) as directory:
            source = Path(directory) / 'src'
            selected = {'chrome/VERSION'}
            for patch in PATCHES:
                selected.update(re.findall(r'^\+\+\+ b/([^\s]+)', patch.read_text(), re.M))
            # A full build tree can be very large. Copy only the patch inputs;
            # new files legitimately do not exist in a pristine fixture yet.
            for name in selected:
                original = Path(FIXTURE) / name
                if original.is_file():
                    destination = source / name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(original, destination)
            env = {**os.environ, 'GIT_CEILING_DIRECTORIES': str(source.parent)}
            # Accept either a pristine or already-applied integration fixture.
            for patch in reversed(PATCHES):
                check = subprocess.run(['git', '-C', str(source), 'apply', '--reverse', '--check', str(patch)],
                                       env=env, capture_output=True)
                if check.returncode == 0:
                    run('git', '-C', source, 'apply', '--reverse', patch, env=env)
            branding = source / 'chrome/app/theme/chromium/BRANDING'
            self.assertIn('PRODUCT_FULLNAME=Helium\n', branding.read_text())
            result = run(sys.executable, ROOT / 'still/apply.py', '--source', source, '--check-only')
            self.assertIn(f'{len(PATCHES)} pending', result.stdout)
            self.assertIn('PRODUCT_FULLNAME=Helium\n', branding.read_text())
            run(sys.executable, ROOT / 'still/apply.py', '--source', source)
            self.assertIn('PRODUCT_FULLNAME=Still\n', branding.read_text())
            self.assertIn('com.jacobcamino.still', (source / 'chrome/common/chrome_paths_linux.cc').read_text())
            self.assertIn('still_blocking_bundle', (source / 'chrome/BUILD.gn').read_text())
            self.assertIn('IDS_STILL_PAGE_COLOR', (source / 'chrome/app/generated_resources.grd').read_text())
            self.assertTrue((source / 'chrome/app/vector_icons/still_color.icon').is_file())
            snapshot = {str(path.relative_to(source)): hashlib.sha256(path.read_bytes()).hexdigest()
                        for path in source.rglob('*') if path.is_file()}
            result = run(sys.executable, ROOT / 'still/apply.py', '--source', source)
            self.assertEqual(result.stdout.count('Already applied:'), len(PATCHES))
            self.assertEqual(snapshot, {str(path.relative_to(source)): hashlib.sha256(path.read_bytes()).hexdigest()
                                       for path in source.rglob('*') if path.is_file()})

    def test_packaging_rejects_absent_or_corrupt_blocker_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            provider = source / 'chrome/browser/extensions/external_provider_impl.cc'
            provider.parent.mkdir(parents=True)
            provider.write_text('// Test fixture only.\n')
            command = [sys.executable, str(ROOT / 'still/verify-package-inputs.py'), '--source', str(source)]
            missing = subprocess.run(command, text=True, capture_output=True)
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn('Missing build output', missing.stderr)
            output = source / 'out/Default/resources/still-blocking.crx'
            output.parent.mkdir(parents=True)
            output.write_bytes(b'not the reviewed package')
            corrupt = subprocess.run(command, text=True, capture_output=True)
            self.assertNotEqual(corrupt.returncode, 0)
            self.assertIn('differs from the reviewed package', corrupt.stderr)
            shutil.copyfile(ROOT / 'still/blocking/package/still-blocking.crx', output)
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)

    def test_package_script_preserves_blocker_and_personal_update_identity(self):
        # Execute the real assembly script with fake binaries and packaging tools.
        # No resulting file is a browser release or a real AppImage.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('scripts', 'package'):
                shutil.copytree(ROOT / name, root / name)
            shutil.copytree(ROOT / 'still/blocking', root / 'still/blocking')
            shutil.copyfile(ROOT / 'still/verify-package-inputs.py', root / 'still/verify-package-inputs.py')
            for name in ('LICENSE', 'LICENSE.ungoogled_chromium', 'revision.txt'):
                shutil.copyfile(ROOT / name, root / name)
            core = root / 'helium-chromium'
            (core / 'utils').mkdir(parents=True)
            for name in ('version.txt', 'chromium_version.txt', 'revision.txt', 'utils/helium_version.py'):
                shutil.copyfile(ROOT / 'helium-chromium' / name, core / name)
            source, output = root / 'build/src', root / 'build/src/out/Default'
            output.mkdir(parents=True)
            (source / 'LICENSE').write_text('Chromium test fixture license placeholder\n')
            provider = source / 'chrome/browser/extensions/external_provider_impl.cc'
            provider.parent.mkdir(parents=True)
            provider.write_text('// Test fixture only.\n')
            (output / 'args.gn').write_text('target_cpu = "x64"\n')
            script = (root / 'scripts/package.sh').read_text()
            for name in re.search(r'_files="([^"]+)"', script).group(1).split():
                (output / name).write_bytes(b'fake binary/resource for packaging test\n')
            (output / 'locales').mkdir()
            (output / 'locales/en-US.pak').write_bytes(b'fixture')
            (output / 'resources').mkdir()
            shutil.copyfile(ROOT / 'still/blocking/package/still-blocking.crx', output / 'resources/still-blocking.crx')
            tools = root / 'fake-tools'
            tools.mkdir()
            programs = {
                'pv': '#!/bin/sh\ncat\n',
                'strip': '#!/bin/sh\nexit 0\n',
                'eu-strip': '#!/bin/sh\nexit 0\n',
                'file': '#!/usr/bin/env python3\nimport sys\nfrom pathlib import Path\nfor name in sys.argv[1:]:\n print(name + (": ELF fixture" if Path(name).name in {"helium", "helium_crashpad_handler", "chromedriver"} else ": data"))\n',
                'appimagetool': '''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
assert sys.argv[1] == '-u'
appdir = Path(sys.argv[3])
assert (appdir / 'opt/still/resources/still-blocking.crx').is_file()
assert (appdir / 'still.desktop').is_file()
assert (appdir / 'still.png').is_file()
assert '/opt/still/helium' in (appdir / 'AppRun').read_text()
assert os.environ['APPIMAGETOOL_APP_NAME'] == 'Still'
Path(os.environ['STILL_TEST_PACKAGE_RECORD']).write_text(json.dumps({'update': sys.argv[2], 'output': sys.argv[4]}))
Path(sys.argv[4]).write_bytes(b'fake AppImage fixture, not executable')
''',
            }
            for name, text in programs.items():
                path = tools / name
                path.write_text(text)
                path.chmod(0o755)
            record = root / 'assembly.json'
            env = {key: value for key, value in os.environ.items()
                   if key not in ('GPG_PRIVATE_KEY', 'GPG_PASSPHRASE', 'SIGN_TARBALL')}
            env.update(PATH=str(tools) + os.pathsep + env['PATH'], MAKE_DEB='0',
                       STILL_TEST_PACKAGE_RECORD=str(record))
            run('bash', root / 'scripts/package.sh', env=env)
            result = json.loads(record.read_text())
            self.assertEqual(result['update'], 'gh-releases-zsync|jacob-camino|still-linux|latest|Still-*-linux-x64.AppImage.zsync')
            self.assertRegex(result['output'], r'^Still-[0-9.]+-linux-x64\.AppImage$')
            archives = list((root / 'build/release').glob('Still-*-linux-x64.tar.xz'))
            self.assertEqual(len(archives), 1)
            with tarfile.open(archives[0]) as archive:
                prefix = archives[0].name.removesuffix('.tar.xz')
                data = archive.extractfile(prefix + '/resources/still-blocking.crx').read()
                self.assertEqual(data, (ROOT / 'still/blocking/package/still-blocking.crx').read_bytes())
                self.assertTrue(archive.getmember(prefix + '/chrome').issym())
                self.assertEqual(archive.getmember(prefix + '/chrome').linkname, 'helium')
                self.assertIsNotNone(archive.getmember(prefix + '/still-wrapper'))
                self.assertIsNotNone(archive.getmember(prefix + '/still.desktop'))
                self.assertIsNotNone(archive.getmember(prefix + '/LICENSE.chromium'))


if __name__ == '__main__':
    unittest.main()
