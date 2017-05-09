import os
import re
import requests
import sys
from distutils.spawn import find_executable

NVIDIA_DEVICES = ['/dev/nvidiactl',
                  '/dev/nvidia-uvm',
                  '/dev/nvidia-uvm-tools']

NVIDIA_DEFAULT_HOST = 'localhost'
NVIDIA_DEFAULT_PORT = 3476
NVIDIA_HOST = 'NV_HOST'


def get_nvidia_docker_endpoint():
    host = os.environ.get(NVIDIA_HOST,
                          "http://{}:{}".format(NVIDIA_DEFAULT_HOST,
                                                NVIDIA_DEFAULT_PORT))
    return host+'/docker/cli/json'


def get_nvidia_configuration():
    return requests.get(get_nvidia_docker_endpoint()).json()


def nvidia_docker_compatible():
    return (sys.platform.startswith('linux') and
            os.path.isfile('/proc/driver/nvidia/version') and
            find_executable('nvidia-docker'))


def add_nvidia_docker_to_config(container_config):

    if not container_config.get('HostConfig', None):
        container_config['HostConfig'] = {}

    nvidia_config = get_nvidia_configuration()

    # Setup the Volumes
    container_config['HostConfig'].setdefault('VolumeDriver',
                                              nvidia_config['VolumeDriver'])

    container_config['HostConfig'].setdefault('Binds', [])
    container_config['HostConfig']['Binds'].extend(nvidia_config['Volumes'])

    # Get nvidia control devices
    devices = container_config['HostConfig'].get('Devices', [])
    # suport both '0 1' and '0, 1' formats, just like nvidia-docker
    gpu_isolation = os.getenv('NV_GPU', '').replace(',', ' ').split()
    pattern = re.compile(r'/nvidia([0-9]+)$')
    for device in nvidia_config['Devices']:
        if gpu_isolation:
            card_number = pattern.search(device)
            if card_number and (card_number.group(1) not in gpu_isolation):
                continue
        # Add device
        devices.append({'PathInContainer': device,
                        'PathOnHost': device,
                        'CgroupPermissions': 'rwm'})

    container_config['HostConfig']['Devices'] = devices
