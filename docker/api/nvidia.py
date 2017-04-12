import os
import re
import sys
from distutils.spawn import find_executable


class NvidiaContainerApiMixin(object):

    @staticmethod
    def nvidia_docker_compatible():
        return (sys.platform.startswith('linux') and
                os.path.isfile('/proc/driver/nvidia/version') and
                find_executable('nvidia-docker'))

    def add_nvidia_docker_to_config(self, container_config, image):

        try:
            use_nvidia_docker = sys.platform.startswith('linux') \
                and (self.inspect_image(image)['Config']['Labels'].
                     get('com.nvidia.volumes.needed', None) ==
                     'nvidia_driver') \
                and find_executable('nvidia-docker')
            # ### Is it necessary to check for nvidia-docker?
        except:
            use_nvidia_docker = False

        if use_nvidia_docker:
            # Get the nvidia driver version
            with open('/proc/driver/nvidia/version', 'r') as fid:
                nvidia_driver_version = fid.read().split('Kernel Module')[1]\
                        .split()[0]
            # It's important not to contain the project name as a prefix here
            container_config['HostConfig']['Binds'] += \
                ['nvidia_driver_' + nvidia_driver_version +
                 ':/usr/local/nvidia:ro']

            devices = container_config['HostConfig'].get('Devices', [])
            devices += [{'PathInContainer': '/dev/nvidiactl',
                         'PathOnHost': '/dev/nvidiactl',
                         'CgroupPermissions': 'rwm'},
                        {'PathInContainer': '/dev/nvidia-uvm',
                         'PathOnHost': '/dev/nvidia-uvm',
                         'CgroupPermissions': 'rwm'}]

            # suport both '0 1' and '0, 1' formats, just like nvidia-docker
            gpu_isolation = os.getenv('NV_GPU', '').replace(',', ' ').split()
            if gpu_isolation:
                gpus = ['nvidia'+gpu for gpu in gpu_isolation]
            else:
                gpus = os.listdir('/dev/')
                pattern = re.compile(r'nvidia[0-9]+$')
                gpus = [x for x in gpus if re.match(pattern, x)]
            for gpu in gpus:
                devices += [{'PathInContainer': '/dev/'+gpu,
                             'PathOnHost': '/dev/'+gpu,
                             'CgroupPermissions': 'rwm'}]

            container_config['HostConfig']['Devices'] = devices
