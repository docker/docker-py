import unittest

from docker.auth import resolve_repository_name, INDEX_URL


class AuthTest(unittest.TestCase):

    def test_resolve_repository_name(self):
        self.assertEqual(resolve_repository_name("root"),
                         (INDEX_URL, "root"))
        self.assertEqual(resolve_repository_name("root:tag"),
                         (INDEX_URL, "root:tag"))
        self.assertEqual(resolve_repository_name("root:tag.minor"),
                         (INDEX_URL, "root:tag.minor"))
        self.assertEqual(resolve_repository_name("user/repo"),
                         (INDEX_URL, "user/repo"))
        self.assertEqual(resolve_repository_name("user/repo:tag"),
                         (INDEX_URL, "user/repo:tag"))
        self.assertEqual(resolve_repository_name("localhost:5000/user/repo"),
                         ("http://localhost:5000/v1/", "user/repo"))
        self.assertEqual(resolve_repository_name("localhost:5000/user/repo:tag"),
                         ("http://localhost:5000/v1/", "user/repo:tag"))        
        self.assertEqual(resolve_repository_name("domain.name:5000/user/repo"),
                         ("http://domain.name:5000/v1/", "user/repo"))
        self.assertEqual(resolve_repository_name("domain.name:5000/user/repo:tag"),
                         ("http://domain.name:5000/v1/", "user/repo:tag"))

if __name__ == '__main__':
    unittest.main()
