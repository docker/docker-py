import io
import random

import docker
import six

from .base import BaseAPIIntegrationTest, BUSYBOX
import pytest


class TestRegressions(BaseAPIIntegrationTest):
    def test_443_handle_nonchunked_response_in_stream(self):
        dfile = io.BytesIO()
        with pytest.raises(docker.errors.APIError) as exc:
            for line in self.client.build(fileobj=dfile, tag="a/b/c"):
                pass
        assert exc.value.response.status_code == 500
        dfile.close()

    def test_542_truncate_ids_client_side(self):
        self.client.start(
            self.client.create_container(BUSYBOX, ['true'])
        )
        result = self.client.containers(all=True, trunc=True)
        assert len(result[0]['Id']) == 12

    def test_647_support_doubleslash_in_image_names(self):
        with pytest.raises(docker.errors.APIError):
            self.client.inspect_image('gensokyo.jp//kirisame')

    def test_649_handle_timeout_value_none(self):
        self.client.timeout = None
        ctnr = self.client.create_container(BUSYBOX, ['sleep', '2'])
        self.client.start(ctnr)
        self.client.stop(ctnr)

    def test_715_handle_user_param_as_int_value(self):
        ctnr = self.client.create_container(BUSYBOX, ['id', '-u'], user=1000)
        self.client.start(ctnr)
        self.client.wait(ctnr)
        logs = self.client.logs(ctnr)
        if six.PY3:
            logs = logs.decode('utf-8')
        assert logs == '1000\n'

    def test_792_explicit_port_protocol(self):

        tcp_port, udp_port = random.sample(range(9999, 32000), 2)
        ctnr = self.client.create_container(
            BUSYBOX, ['sleep', '9999'], ports=[2000, (2000, 'udp')],
            host_config=self.client.create_host_config(
                port_bindings={'2000/tcp': tcp_port, '2000/udp': udp_port}
            )
        )
        self.tmp_containers.append(ctnr)
        self.client.start(ctnr)
        assert self.client.port(
            ctnr, 2000
        )[0]['HostPort'] == six.text_type(tcp_port)
        assert self.client.port(
            ctnr, '2000/tcp'
        )[0]['HostPort'] == six.text_type(tcp_port)
        assert self.client.port(
            ctnr, '2000/udp'
        )[0]['HostPort'] == six.text_type(udp_port)
