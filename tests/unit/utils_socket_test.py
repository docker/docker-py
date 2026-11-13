import unittest

from docker.utils.socket import consume_socket_output


class SocketConsumeOutputTests(unittest.TestCase):
    def test_no_demux(self):
        frames = [b"frame1", b"frame2", b"frame3"]
        result = consume_socket_output(frames, demux=False)
        self.assertEqual(result, b"frame1frame2frame3")

    def test_demux(self):
        frames = [
            (b"stdout1", None),
            (None, b"stderr1"),
            (b"stdout2", None),
            (None, b"stderr2"),
        ]
        stdout, stderr = consume_socket_output(frames, demux=True)
        self.assertEqual(stdout, b"stdout1stdout2")
        self.assertEqual(stderr, b"stderr1stderr2")

    def test_empty_frames(self):
        result = consume_socket_output([], demux=False)
        self.assertEqual(result, b"")

    def test_empty_frames_demux(self):
        stdout, stderr = consume_socket_output([], demux=True)
        self.assertEqual((None, None), (stdout, stderr))
