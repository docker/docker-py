import unittest

from docker.utils import convert_port_bindings

class UtilsTest(unittest.TestCase):
    def test_convert_port_binding_with_dict(self):
        """
        Ensure the port binding raises an exception if the value is clearly unexpected
        """
        binding = [{
            'HostIp': '0.0.0.0',
            'HostPort': '4000',
        }]

        bindings = {
            '80': binding,
        }

        self.assertRaises(TypeError, convert_port_bindings, bindings)

    def test_convert_port_binding_with_non_int_string(self):
        """
        Ensure the port binding raises an exception if the value is clearly unexpected
        """
        binding = ['hi']

        bindings = {
            '80': binding,
        }

        self.assertRaises(ValueError, convert_port_bindings, bindings)

    def test_convert_port_binding_just_port_number(self):
        binding = '4000'
        bindings = {
            '80': binding,
        }

        converted = convert_port_bindings(bindings)

        self.assertEqual(binding, converted.values()[0][0]['HostPort'])
