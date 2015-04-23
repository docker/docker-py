import sys
import unittest

import six


class BaseTestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(BaseTestCase, self).__init__(*args, **kwargs)
        if six.PY2:
            self.assertRegex = self.assertRegexpMatches
            self.assertCountEqual = self.assertItemsEqual

    def assertIn(self, object, collection):
        if six.PY2 and sys.version_info[1] <= 6:
            return self.assertTrue(object in collection)
        return super(BaseTestCase, self).assertIn(object, collection)
