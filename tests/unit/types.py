import unittest
from docker.types.services import Mount


class TestMounts(unittest.TestCase):
    def test_parse_mount_string_docker(self):
        mount = Mount.parse_mount_string("foo/bar:/buz:ro")
        self.assertEqual(mount['Source'], "foo/bar")
        self.assertEqual(mount['Target'], "/buz")
        self.assertEqual(mount['ReadOnly'], True)

        mount = Mount.parse_mount_string("foo/bar:/buz:rw")
        self.assertEqual(mount['ReadOnly'], False)

        mount = Mount.parse_mount_string("foo/bar:/buz")
        self.assertEqual(mount['ReadOnly'], False)
