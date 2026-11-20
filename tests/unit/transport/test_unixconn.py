import gc
import os
import socket
import tempfile
import threading
import unittest
import warnings

from docker.transport.unixconn import UnixHTTPConnection


class UnixHTTPConnectionTest(unittest.TestCase):
    def test_connect_closes_socket_on_failure(self):
        """A failed connect() must not leak the socket (docker-py#3464)."""
        conn = UnixHTTPConnection(
            base_url='http+unix://localhost',
            unix_socket='/nonexistent/docker.sock',
            timeout=5,
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always', ResourceWarning)
            with self.assertRaises(FileNotFoundError):
                conn.connect()
            gc.collect()
        leaked = [w for w in caught
                  if issubclass(w.category, ResourceWarning)
                  and 'unclosed' in str(w.message)]
        self.assertEqual(leaked, [])
        self.assertIsNone(conn.sock)

    def test_connect_sets_sock_on_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'docker.sock')
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(path)
            server.listen(1)
            accepted = []

            def _accept():
                client, _ = server.accept()
                accepted.append(client)
                client.close()

            thread = threading.Thread(target=_accept, daemon=True)
            thread.start()
            try:
                conn = UnixHTTPConnection(
                    base_url='http+unix://localhost',
                    unix_socket=path,
                    timeout=5,
                )
                conn.connect()
                self.assertIsNotNone(conn.sock)
                conn.close()
            finally:
                thread.join(timeout=5)
                server.close()


if __name__ == '__main__':
    unittest.main()
