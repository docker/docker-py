from docker.types.containers import ContainerConfig


def test_uid_0_is_not_elided():
    x = ContainerConfig(image='i', version='v', command='true', user=0)
    assert x['User'] == '0'
