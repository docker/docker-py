import unittest

from docker.utils import parse_repository_tag


class UtilsTest(unittest.TestCase):

    def test_parse_repository_tag(self):
        self.assertEqual(parse_repository_tag("root"),
                         ("root", ""))
        self.assertEqual(parse_repository_tag("root:tag"),
                         ("root", "tag"))
        self.assertEqual(parse_repository_tag("user/repo"),
                         ("user/repo", ""))
        self.assertEqual(parse_repository_tag("user/repo:tag"),
                         ("user/repo", "tag"))
        self.assertEqual(parse_repository_tag("url:5000/repo"),
                         ("url:5000/repo", ""))
        self.assertEqual(parse_repository_tag("url:5000/repo:tag"),
                         ("url:5000/repo", "tag"))


if __name__ == '__main__':
    unittest.main()
