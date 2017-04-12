import os
import re
import sys
from distutils.spawn import find_executable


NVIDIA_DEVICES = ['/dev/nvidiactl',
                  '/dev/nvidia-uvm',
                  '/dev/nvidia-uvm-tools']


def nvidia_docker_compatible():
    return (sys.platform.startswith('linux') and
            os.path.isfile('/proc/driver/nvidia/version') and
            find_executable('nvidia-docker'))


def get_nvidia_driver_version():
    '''
    Determine the version of nvidia driver installed

    Parses the /proc/driver/nvidia/version to determine version.

    Example:

    NVRM version: NVIDIA UNIX x86_64 Kernel Module  375.39  Tue Jan 31 20:47:00 PST 2017
    GCC version:  gcc version 5.4.0 20160609 (Ubuntu 5.4.0-6ubuntu1~16.04.4)

    '''  # noqa: E501

    with open('/proc/driver/nvidia/version', 'r') as fid:
        return fid.read().split('Kernel Module')[1].split()[0]


def get_nvidia_driver_volume():
    '''
    Get the nvidia_docker driver volume name
    '''

    return ('nvidia_driver_' +
            get_nvidia_driver_version())


def add_nvidia_docker_to_config(container_config):

    if not container_config.get('HostConfig', None):
        container_config['HostConfig'] = {}
    container_config['HostConfig'].setdefault('Binds', [])
    # It's important not to contain the project name as a prefix here
    container_config['HostConfig']['Binds'] += \
        [get_nvidia_driver_volume() + ':/usr/local/nvidia:ro']

    # Get nvidia control devices
    devices = container_config['HostConfig'].get('Devices', [])
    for device in NVIDIA_DEVICES:
        if os.path.exists(device):
            devices.append({'PathInContainer': device,
                            'PathOnHost': device,
                            'CgroupPermissions': 'rwm'})

    # suport both '0 1' and '0, 1' formats, just like nvidia-docker
    gpu_isolation = os.getenv('NV_GPU', '').replace(',', ' ').split()
    if gpu_isolation:
        gpus = ['nvidia'+gpu for gpu in gpu_isolation]
    else:
        gpus = os.listdir('/dev/')
        pattern = re.compile(r'nvidia[0-9]+$')
        gpus = [x for x in gpus if re.match(pattern, x)]
    for gpu in gpus:
        devices.append({'PathInContainer': '/dev/'+gpu,
                        'PathOnHost': '/dev/'+gpu,
                        'CgroupPermissions': 'rwm'})

    container_config['HostConfig']['Devices'] = devices
