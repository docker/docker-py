# Copyright 2013 dotCloud inc.

#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

CURRENT_VERSION = 'v1.9'

FAKE_CONTAINER_ID = '3cc2351ab11b'
FAKE_IMAGE_ID = 'e9aa60c60128'
FAKE_IMAGE_NAME = 'test_image'
FAKE_TARBALL_PATH = '/path/to/tarball'
FAKE_REPO_NAME = 'repo'
FAKE_TAG_NAME = 'tag'
FAKE_FILE_NAME = 'file'
FAKE_URL = 'myurl'
FAKE_PATH = '/path'

# Each method is prefixed with HTTP method (get, post...)
# for clarity and readability


def get_fake_version():
    status_code = 200
    response = {'GoVersion': '1', 'Version': '1.1.1',
                'GitCommit': 'deadbeef+CHANGES'}
    return status_code, response


def get_fake_info():
    status_code = 200
    response = {'Containers': 1, 'Images': 1, 'Debug': False,
                'MemoryLimit': False, 'SwapLimit': False,
                'IPv4Forwarding': True}
    return status_code, response


def get_fake_search():
    status_code = 200
    response = [{'Name': 'busybox', 'Description': 'Fake Description'}]
    return status_code, response


def get_fake_images():
    status_code = 200
    response = [{
        'Id': FAKE_IMAGE_ID,
        'Created': '2 days ago',
        'Repository': 'busybox',
        'RepoTags': ['busybox:latest', 'busybox:1.0'],
    }]
    return status_code, response


def get_fake_image_history():
    status_code = 200
    response = [
        {
            "Id": "b750fe79269d",
            "Created": 1364102658,
            "CreatedBy": "/bin/bash"
        },
        {
            "Id": "27cf78414709",
            "Created": 1364068391,
            "CreatedBy": ""
        }
    ]

    return status_code, response


def post_fake_import_image():
    status_code = 200
    response = 'Import messages...'

    return status_code, response


def get_fake_containers():
    status_code = 200
    response = [{
        'Id': FAKE_CONTAINER_ID,
        'Image': 'busybox:latest',
        'Created': '2 days ago',
        'Command': 'true',
        'Status': 'fake status'
    }]
    return status_code, response


def post_fake_start_container():
    status_code = 200
    response = {'Id': FAKE_CONTAINER_ID}
    return status_code, response


def post_fake_create_container():
    status_code = 200
    response = {'Id': FAKE_CONTAINER_ID}
    return status_code, response


def get_fake_inspect_container():
    status_code = 200
    response = {
        'Id': FAKE_CONTAINER_ID,
        'Config': {'Privileged': True},
        'ID': FAKE_CONTAINER_ID,
        'Image': 'busybox:latest',
        "State": {
            "Running": True,
            "Pid": 0,
            "ExitCode": 0,
            "StartedAt": "2013-09-25T14:01:18.869545111+02:00",
            "Ghost": False
        },
    }
    return status_code, response


def get_fake_inspect_image():
    status_code = 200
    response = {
        'id': FAKE_IMAGE_ID,
        'parent': "27cf784147099545",
        'created': "2013-03-23T22:24:18.818426-07:00",
        'container': FAKE_CONTAINER_ID,
        'container_config':
        {
            "Hostname": "",
            "User": "",
            "Memory": 0,
            "MemorySwap": 0,
            "AttachStdin": False,
            "AttachStdout": False,
            "AttachStderr": False,
            "PortSpecs": "",
            "Tty": True,
            "OpenStdin": True,
            "StdinOnce": False,
            "Env": "",
            "Cmd": ["/bin/bash"],
            "Dns": "",
            "Image": "base",
            "Volumes": "",
            "VolumesFrom": "",
            "WorkingDir": ""
        },
        'Size': 6823592
    }
    return status_code, response


def get_fake_port():
    status_code = 200
    response = {
        'HostConfig': {
            'Binds': None,
            'ContainerIDFile': '',
            'Links': None,
            'LxcConf': None,
            'PortBindings': {
                '1111': None,
                '1111/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '4567'}],
                '2222': None
            },
            'Privileged': False,
            'PublishAllPorts': False
        },
        'NetworkSettings': {
            'Bridge': 'docker0',
            'PortMapping': None,
            'Ports': {
                '1111': None,
                '1111/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '4567'}],
                '2222': None}
        }
    }
    return status_code, response


def get_fake_insert_image():
    status_code = 200
    response = {'StatusCode': 0}
    return status_code, response


def get_fake_wait():
    status_code = 200
    response = {'StatusCode': 0}
    return status_code, response


def get_fake_logs():
    status_code = 200
    response = 'Flowering Nights (Sakuya Iyazoi)'
    return status_code, response


def get_fake_diff():
    status_code = 200
    response = [{'Path': '/test', 'Kind': 1}]
    return status_code, response


def get_fake_export():
    status_code = 200
    response = 'Byte Stream....'
    return status_code, response


def post_fake_stop_container():
    status_code = 200
    response = {'Id': FAKE_CONTAINER_ID}
    return status_code, response


def post_fake_kill_container():
    status_code = 200
    response = {'Id': FAKE_CONTAINER_ID}
    return status_code, response


def post_fake_restart_container():
    status_code = 200
    response = {'Id': FAKE_CONTAINER_ID}
    return status_code, response


def delete_fake_remove_container():
    status_code = 200
    response = {'Id': FAKE_CONTAINER_ID}
    return status_code, response


def post_fake_image_create():
    status_code = 200
    response = {'Id': FAKE_IMAGE_ID}
    return status_code, response


def delete_fake_remove_image():
    status_code = 200
    response = {'Id': FAKE_IMAGE_ID}
    return status_code, response


def post_fake_commit():
    status_code = 200
    response = {'Id': FAKE_CONTAINER_ID}
    return status_code, response


def post_fake_push():
    status_code = 200
    response = {'Id': FAKE_IMAGE_ID}
    return status_code, response


def post_fake_build_container():
    status_code = 200
    response = {'Id': FAKE_CONTAINER_ID}
    return status_code, response


def post_fake_tag_image():
    status_code = 200
    response = {'Id': FAKE_IMAGE_ID}
    return status_code, response


# Maps real api url to fake response callback
prefix = 'http+unix://var/run/docker.sock'
fake_responses = {
    '{1}/{0}/version'.format(CURRENT_VERSION, prefix):
    get_fake_version,
    '{1}/{0}/info'.format(CURRENT_VERSION, prefix):
    get_fake_info,
    '{1}/{0}/images/search'.format(CURRENT_VERSION, prefix):
    get_fake_search,
    '{1}/{0}/images/json'.format(CURRENT_VERSION, prefix):
    get_fake_images,
    '{1}/{0}/images/test_image/history'.format(CURRENT_VERSION, prefix):
    get_fake_image_history,
    '{1}/{0}/images/create'.format(CURRENT_VERSION, prefix):
    post_fake_import_image,
    '{1}/{0}/containers/json'.format(CURRENT_VERSION, prefix):
    get_fake_containers,
    '{1}/{0}/containers/3cc2351ab11b/start'.format(CURRENT_VERSION, prefix):
    post_fake_start_container,
    '{1}/{0}/containers/3cc2351ab11b/json'.format(CURRENT_VERSION, prefix):
    get_fake_inspect_container,
    '{1}/{0}/images/e9aa60c60128/tag'.format(CURRENT_VERSION, prefix):
    post_fake_tag_image,
    '{1}/{0}/containers/3cc2351ab11b/wait'.format(CURRENT_VERSION, prefix):
    get_fake_wait,
    '{1}/{0}/containers/3cc2351ab11b/attach'.format(CURRENT_VERSION, prefix):
    get_fake_logs,
    '{1}/{0}/containers/3cc2351ab11b/changes'.format(CURRENT_VERSION, prefix):
    get_fake_diff,
    '{1}/{0}/containers/3cc2351ab11b/export'.format(CURRENT_VERSION, prefix):
    get_fake_export,
    '{1}/{0}/containers/3cc2351ab11b/stop'.format(CURRENT_VERSION, prefix):
    post_fake_stop_container,
    '{1}/{0}/containers/3cc2351ab11b/kill'.format(CURRENT_VERSION, prefix):
    post_fake_kill_container,
    '{1}/{0}/containers/3cc2351ab11b/json'.format(CURRENT_VERSION, prefix):
    get_fake_port,
    '{1}/{0}/containers/3cc2351ab11b/restart'.format(CURRENT_VERSION, prefix):
    post_fake_restart_container,
    '{1}/{0}/containers/3cc2351ab11b'.format(CURRENT_VERSION, prefix):
    delete_fake_remove_container,
    '{1}/{0}/images/create'.format(CURRENT_VERSION, prefix):
    post_fake_image_create,
    '{1}/{0}/images/e9aa60c60128'.format(CURRENT_VERSION, prefix):
    delete_fake_remove_image,
    '{1}/{0}/images/test_image/json'.format(CURRENT_VERSION, prefix):
    get_fake_inspect_image,
    '{1}/{0}/images/test_image/insert'.format(CURRENT_VERSION, prefix):
    get_fake_insert_image,
    '{1}/{0}/images/test_image/push'.format(CURRENT_VERSION, prefix):
    post_fake_push,
    '{1}/{0}/commit'.format(CURRENT_VERSION, prefix):
    post_fake_commit,
    '{1}/{0}/containers/create'.format(CURRENT_VERSION, prefix):
    post_fake_create_container,
    '{1}/{0}/build'.format(CURRENT_VERSION, prefix):
    post_fake_build_container
}
