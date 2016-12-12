import six

from .. import errors
from .. import utils


class ExecApiMixin(object):
    @utils.minimum_version('1.15')
    @utils.check_resource
    def exec_create(self, container, cmd, stdout=True, stderr=True,
                    stdin=False, tty=False, privileged=False, user=''):
        """
        Sets up an exec instance in a running container.

        Args:
            container (str): Target container where exec instance will be
                created
            cmd (str or list): Command to be executed
            stdout (bool): Attach to stdout. Default: ``True``
            stderr (bool): Attach to stderr. Default: ``True``
            stdin (bool): Attach to stdin. Default: ``False``
            tty (bool): Allocate a pseudo-TTY. Default: False
            privileged (bool): Run as privileged.
            user (str): User to execute command as. Default: root

        Returns:
            (dict): A dictionary with an exec ``Id`` key.

        Raises:
            :py:class:`docker.errors.APIError`
                If the server returns an error.
        """

        if privileged and utils.compare_version('1.19', self._version) < 0:
            raise errors.InvalidVersion(
                'Privileged exec is not supported in API < 1.19'
            )
        if user and utils.compare_version('1.19', self._version) < 0:
            raise errors.InvalidVersion(
                'User-specific exec is not supported in API < 1.19'
            )
        if isinstance(cmd, six.string_types):
            cmd = utils.split_command(cmd)

        data = {
            'Container': container,
            'User': user,
            'Privileged': privileged,
            'Tty': tty,
            'AttachStdin': stdin,
            'AttachStdout': stdout,
            'AttachStderr': stderr,
            'Cmd': cmd
        }

        url = self._url('/containers/{0}/exec', container)
        res = self._post_json(url, data=data)
        return self._result(res, True)

    @utils.minimum_version('1.16')
    def exec_inspect(self, exec_id):
        """
        Return low-level information about an exec command.

        Args:
            exec_id (str): ID of the exec instance

        Returns:
            (dict): Dictionary of values returned by the endpoint.

        Raises:
            :py:class:`docker.errors.APIError`
                If the server returns an error.
        """
        if isinstance(exec_id, dict):
            exec_id = exec_id.get('Id')
        res = self._get(self._url("/exec/{0}/json", exec_id))
        return self._result(res, True)

    @utils.minimum_version('1.15')
    def exec_resize(self, exec_id, height=None, width=None):
        """
        Resize the tty session used by the specified exec command.

        Args:
            exec_id (str): ID of the exec instance
            height (int): Height of tty session
            width (int): Width of tty session
        """

        if isinstance(exec_id, dict):
            exec_id = exec_id.get('Id')

        params = {'h': height, 'w': width}
        url = self._url("/exec/{0}/resize", exec_id)
        res = self._post(url, params=params)
        self._raise_for_status(res)

    @utils.minimum_version('1.15')
    def exec_start(self, exec_id, detach=False, tty=False, stream=False,
                   socket=False):
        """
        Start a previously set up exec instance.

        Args:
            exec_id (str): ID of the exec instance
            detach (bool): If true, detach from the exec command.
                Default: False
            tty (bool): Allocate a pseudo-TTY. Default: False
            stream (bool): Stream response data. Default: False

        Returns:
            (generator or str): If ``stream=True``, a generator yielding
            response chunks. A string containing response data otherwise.

        Raises:
            :py:class:`docker.errors.APIError`
                If the server returns an error.
        """
        # we want opened socket if socket == True
        if isinstance(exec_id, dict):
            exec_id = exec_id.get('Id')

        data = {
            'Tty': tty,
            'Detach': detach
        }

        headers = {} if detach else {
            'Connection': 'Upgrade',
            'Upgrade': 'tcp'
        }

        res = self._post_json(
            self._url('/exec/{0}/start', exec_id),
            headers=headers,
            data=data,
            stream=True
        )
        if detach:
            return self._result(res)
        if socket:
            return self._get_raw_response_socket(res)
        return self._read_from_socket(res, stream)
