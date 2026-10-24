"""Regression tests for the embedded PowerShell payload.

The build pipeline runs a large Base64-encoded .ps1.  Editing it by hand
is error-prone, so these tests decode the payload straight from the source
(AST, no import of the Windows-only GUI) and assert the bounded-wait and
single-source-walk fixes stay in place.
"""

import ast
import base64
import os
import unittest


_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_HERE, os.pardir, 'exfat_builder.py')


def _load_payload(name):
    with open(_SRC, 'r', encoding='utf-8', errors='replace') as fh:
        source = fh.read()
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return base64.b64decode(
                        ast.literal_eval(node.value)).decode('utf-8')
    raise AssertionError('%s not found in exfat_builder.py' % name)


class TestEmbeddedPs1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ps1 = _load_payload('_PS1_B64')

    def test_payload_decodes_as_utf8(self):
        self.assertGreater(len(self.ps1), 10000)
        self.assertIn('function Invoke-OsfHidden', self.ps1)

    def test_osfmount_helper_has_a_hard_timeout(self):
        # The old helper called WaitForExit() with no timeout and could
        # block a build forever on a wedged OSFMount driver.
        self.assertIn('ReadToEndAsync', self.ps1)
        self.assertIn('$p.WaitForExit([int]($TimeoutSeconds * 1000))',
                      self.ps1)
        self.assertNotIn('[void]$p.WaitForExit()', self.ps1)

    def test_dismount_is_bounded_and_does_not_retry_on_timeout(self):
        self.assertIn("'-d'", self.ps1)
        self.assertIn('-TimeoutSeconds 60', self.ps1)
        self.assertIn('TimedOut', self.ps1)

    def test_mount_uses_a_timeout(self):
        self.assertIn('-TimeoutSeconds 300', self.ps1)

    def test_mounted_confirmation_emitted_after_attach(self):
        # The app must only start tracking a drive letter after OSFMount
        # confirms the attach; the old announcement was printed before it.
        self.assertIn('Write-Host "[MOUNTED] $MountPoint"', self.ps1)
        self.assertLess(
            self.ps1.index('Wait-ForLogicalDrive -driveLetter $DriveLetter'),
            self.ps1.index('Write-Host "[MOUNTED] $MountPoint"'))

    def test_free_letter_detection_uses_all_views(self):
        # Get-PSDrive alone misses phantom/reserved letters, which caused
        # the next mount to reuse a half-released letter and wedge.
        self.assertIn('Get-PSDrive -PSProvider FileSystem', self.ps1)
        self.assertIn('[System.IO.DriveInfo]::GetDrives()', self.ps1)
        self.assertIn('[Environment]::GetLogicalDrives()', self.ps1)
        self.assertIn('HKLM:\\SYSTEM\\MountedDevices', self.ps1)

    def test_stale_osf_mounts_are_swept_before_attach(self):
        self.assertIn('function Clear-StaleOsfMounts', self.ps1)
        self.assertIn('function Get-OsfMountEntries', self.ps1)
        self.assertLess(
            self.ps1.index('Clear-StaleOsfMounts -osfPath $osf'),
            self.ps1.index('$osfOpts = "rw,rem"'))

    def test_dismount_falls_back_to_force(self):
        self.assertIn("@('-D','-m',$target)", self.ps1)

    def test_format_has_a_hard_timeout(self):
        self.assertIn('$proc.WaitForExit(180 * 1000)', self.ps1)
        self.assertIn('$lastFormatExitCode = 124', self.ps1)

    def test_source_is_walked_once_for_cluster_size(self):
        # DataBytes32K/64K are computed in the same file loop.  Exactly
        # one walk per branch (override / default), and the 64 KB choice
        # must reuse the cached DataBytes64K instead of walking again.
        self.assertIn('DataBytes32K', self.ps1)
        self.assertIn('DataBytes64K', self.ps1)
        self.assertEqual(
            self.ps1.count('$stats = Get-SourceStats -dir $SourceDir '
                           '-clusterBytes $ExfatClusterSize'), 1)
        self.assertEqual(
            self.ps1.count('$stats = Get-SourceStats -dir $SourceDir '
                           '-clusterBytes 32768'), 1)
        self.assertNotIn(
            '$stats = Get-SourceStats -dir $SourceDir -clusterBytes 65536',
            self.ps1)
        self.assertIn('$stats.DataBytes = $stats.DataBytes64K', self.ps1)


if __name__ == '__main__':
    unittest.main()
