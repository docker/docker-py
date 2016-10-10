import sys
import unittest

import six


class BaseTestCase(unittest.TestCase):
    def assertIn(self, object, collection):
        if six.PY2 and sys.version_info[1] <= 6:
            return self.assertTrue(object in collection)
        return super(BaseTestCase, self).assertIn(object, collection)


class Cleanup(object):
    if sys.version_info < (2, 7):
        # Provide a basic implementation of addCleanup for Python < 2.7
        def __init__(self, *args, **kwargs):
            super(Cleanup, self).__init__(*args, **kwargs)
            self._cleanups = []

        def tearDown(self):
            super(Cleanup, self).tearDown()
            ok = True
            while self._cleanups:
                fn, args, kwargs = self._cleanups.pop(-1)
                try:
                    fn(*args, **kwargs)
                except KeyboardInterrupt:
                    raise
                except:
                    ok = False
            if not ok:
                raise

        def addCleanup(self, function, *args, **kwargs):
            self._cleanups.append((function, args, kwargs))
