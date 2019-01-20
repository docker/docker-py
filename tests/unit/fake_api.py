from . import fake_stat
from docker import constants

CURRENT_VERSION = 'v{0}'.format(constants.DEFAULT_DOCKER_API_VERSION)

FAKE_CONTAINER_ID = '3cc2351ab11b'
FAKE_IMAGE_ID = 'e9aa60c60128'
FAKE_EXEC_ID = 'd5d177f121dc'
FAKE_NETWORK_ID = '33fb6a3462b8'
FAKE_IMAGE_NAME = 'test_image'
FAKE_TARBALL_PATH = '/path/to/tarball'
FAKE_REPO_NAME = 'repo'
FAKE_TAG_NAME = 'tag'
FAKE_FILE_NAME = 'file'
FAKE_URL = 'myurl'
FAKE_PATH = '/path'
FAKE_VOLUME_NAME = 'perfectcherryblossom'
FAKE_NODE_ID = '24ifsmvkjbyhk'

# Each method is prefixed with HTTP method (get, post...)
# for clarity and readability


def get_fake_version():
    status_code = 200
    response = {
        'ApiVersion': '1.35',
        'Arch': 'amd64',
        'BuildTime': '2018-01-10T20:09:37.000000000+00:00',
        'Components': [{
            'Details': {
                'ApiVersion': '1.35',
                'Arch': 'amd64',
                'BuildTime': '2018-01-10T20:09:37.000000000+00:00',
                'Experimental': 'false',
                'GitCommit': '03596f5',
                'GoVersion': 'go1.9.2',
                'KernelVersion': '4.4.0-112-generic',
                'MinAPIVersion': '1.12',
                'Os': 'linux'
            },
            'Name': 'Engine',
            'Version': '18.01.0-ce'
        }],
        'GitCommit': '03596f5',
        'GoVersion': 'go1.9.2',
        'KernelVersion': '4.4.0-112-generic',
        'MinAPIVersion': '1.12',
        'Os': 'linux',
        'Platform': {'Name': ''},
        'Version': '18.01.0-ce'
    }

    return status_code, response


def get_fake_info():
    status_code = 200
    response = {'Containers': 1, 'Images': 1, 'Debug': False,
                'MemoryLimit': False, 'SwapLimit': False,
                'IPv4Forwarding': True}
    return status_code, response


def post_fake_auth():
    status_code = 200
    response = {'Status': 'Login Succeeded',
                'IdentityToken': '9cbaf023786cd7'}
    return status_code, response


def get_fake_ping():
    return 200, "OK"


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


def post_fake_resize_container():
    status_code = 200
    response = {'Id': FAKE_CONTAINER_ID}
    return status_code, response


def post_fake_create_container():
    status_code = 200
    response = {'Id': FAKE_CONTAINER_ID}
    return status_code, response


def get_fake_inspect_container(tty=False):
    status_code = 200
    response = {
        'Id': FAKE_CONTAINER_ID,
        'Config': {'Labels': {'foo': 'bar'}, 'Privileged': True, 'Tty': tty},
        'ID': FAKE_CONTAINER_ID,
        'Image': 'busybox:latest',
        'Name': 'foobar',
        "State": {
            "Status": "running",
            "Running": True,
            "Pid": 0,
            "ExitCode": 0,
            "StartedAt": "2013-09-25T14:01:18.869545111+02:00",
            "Ghost": False
        },
        "HostConfig": {
            "LogConfig": {
                "Type": "json-file",
                "Config": {}
            },
        },
        "MacAddress": "02:42:ac:11:00:0a"
    }
    return status_code, response


def get_fake_inspect_image():
    status_code = 200
    response = {
        'Id': FAKE_IMAGE_ID,
        'Parent': "27cf784147099545",
        'Created': "2013-03-23T22:24:18.818426-07:00",
        'Container': FAKE_CONTAINER_ID,
        'Config': {'Labels': {'bar': 'foo'}},
        'ContainerConfig':
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
    response = (b'\x01\x00\x00\x00\x00\x00\x00\x00'
                b'\x02\x00\x00\x00\x00\x00\x00\x00'
                b'\x01\x00\x00\x00\x00\x00\x00\x11Flowering Nights\n'
                b'\x01\x00\x00\x00\x00\x00\x00\x10(Sakuya Iyazoi)\n')
    return status_code, response


def get_fake_diff():
    status_code = 200
    response = [{'Path': '/test', 'Kind': 1}]
    return status_code, response


def get_fake_events():
    status_code = 200
    response = [{'status': 'stop', 'id': FAKE_CONTAINER_ID,
                 'from': FAKE_IMAGE_ID, 'time': 1423247867}]
    return status_code, response


def get_fake_export():
    status_code = 200
    response = 'Byte Stream....'
    return status_code, response


def post_fake_exec_create():
    status_code = 200
    response = {'Id': FAKE_EXEC_ID}
    return status_code, response


def post_fake_exec_start():
    status_code = 200
    response = (b'\x01\x00\x00\x00\x00\x00\x00\x11bin\nboot\ndev\netc\n'
                b'\x01\x00\x00\x00\x00\x00\x00\x12lib\nmnt\nproc\nroot\n'
                b'\x01\x00\x00\x00\x00\x00\x00\x0csbin\nusr\nvar\n')
    return status_code, response


def post_fake_exec_resize():
    status_code = 201
    return status_code, ''


def get_fake_exec_inspect():
    return 200, {
        'OpenStderr': True,
        'OpenStdout': True,
        'Container': get_fake_inspect_container()[1],
        'Running': False,
        'ProcessConfig': {
            'arguments': ['hello world'],
            'tty': False,
            'entrypoint': 'echo',
            'privileged': False,
            'user': ''
        },
        'ExitCode': 0,
        'ID': FAKE_EXEC_ID,
        'OpenStdin': False
    }


def post_fake_stop_container():
    status_code = 200
    response = {'Id': FAKE_CONTAINER_ID}
    return status_code, response


def post_fake_kill_container():
    status_code = 200
    response = {'Id': FAKE_CONTAINER_ID}
    return status_code, response


def post_fake_pause_container():
    status_code = 200
    response = {'Id': FAKE_CONTAINER_ID}
    return status_code, response


def post_fake_unpause_container():
    status_code = 200
    response = {'Id': FAKE_CONTAINER_ID}
    return status_code, response


def post_fake_restart_container():
    status_code = 200
    response = {'Id': FAKE_CONTAINER_ID}
    return status_code, response


def post_fake_rename_container():
    status_code = 204
    return status_code, None


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


def get_fake_get_image():
    status_code = 200
    response = 'Byte Stream....'
    return status_code, response


def post_fake_load_image():
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


def get_fake_stats():
    status_code = 200
    response = fake_stat.OBJ
    return status_code, response


def get_fake_top():
    return 200, {
        'Processes': [
            [
                'root',
                '26501',
                '6907',
                '0',
                '10:32',
                'pts/55',
                '00:00:00',
                'sleep 60',
            ],
        ],
        'Titles': [
            'UID',
            'PID',
            'PPID',
            'C',
            'STIME',
            'TTY',
            'TIME',
            'CMD',
        ],
    }


def get_fake_volume_list():
    status_code = 200
    response = {
        'Volumes': [
            {
                'Name': 'perfectcherryblossom',
                'Driver': 'local',
                'Mountpoint': '/var/lib/docker/volumes/perfectcherryblossom',
                'Scope': 'local'
            }, {
                'Name': 'subterraneananimism',
                'Driver': 'local',
                'Mountpoint': '/var/lib/docker/volumes/subterraneananimism',
                'Scope': 'local'
            }
        ]
    }
    return status_code, response


def get_fake_volume():
    status_code = 200
    response = {
        'Name': 'perfectcherryblossom',
        'Driver': 'local',
        'Mountpoint': '/var/lib/docker/volumes/perfectcherryblossom',
        'Labels': {
            'com.example.some-label': 'some-value'
        },
        'Scope': 'local'
    }
    return status_code, response


def fake_remove_volume():
    return 204, None


def post_fake_update_container():
    return 200, {'Warnings': []}


def post_fake_update_node():
    return 200, None


def post_fake_join_swarm():
    return 200, None


def get_fake_network_list():
    return 200, [{
        "Name": "bridge",
        "Id": FAKE_NETWORK_ID,
        "Scope": "local",
        "Driver": "bridge",
        "EnableIPv6": False,
        "Internal": False,
        "IPAM": {
            "Driver": "default",
            "Config": [
                {
                    "Subnet": "172.17.0.0/16"
                }
            ]
        },
        "Containers": {
            FAKE_CONTAINER_ID: {
                "EndpointID": "ed2419a97c1d99",
                "MacAddress": "02:42:ac:11:00:02",
                "IPv4Address": "172.17.0.2/16",
                "IPv6Address": ""
            }
        },
        "Options": {
            "com.docker.network.bridge.default_bridge": "true",
            "com.docker.network.bridge.enable_icc": "true",
            "com.docker.network.bridge.enable_ip_masquerade": "true",
            "com.docker.network.bridge.host_binding_ipv4": "0.0.0.0",
            "com.docker.network.bridge.name": "docker0",
            "com.docker.network.driver.mtu": "1500"
        }
    }]


def get_fake_network():
    return 200, get_fake_network_list()[1][0]


def post_fake_network():
    return 201, {"Id": FAKE_NETWORK_ID, "Warnings": []}


def delete_fake_network():
    return 204, None


def post_fake_network_connect():
    return 200, None


def post_fake_network_disconnect():
    return 200, None


# Maps real api url to fake response callback
prefix = 'http+docker://localhost'
if constants.IS_WINDOWS_PLATFORM:
    prefix = 'http+docker://localnpipe'

fake_responses = {
    '{0}/version'.format(prefix):
    get_fake_version,
    '{1}/{0}/version'.format(CURRENT_VERSION, prefix):
    get_fake_version,
    '{1}/{0}/info'.format(CURRENT_VERSION, prefix):
    get_fake_info,
    '{1}/{0}/auth'.format(CURRENT_VERSION, prefix):
    post_fake_auth,
    '{1}/{0}/_ping'.format(CURRENT_VERSION, prefix):
    get_fake_ping,
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
    '{1}/{0}/containers/3cc2351ab11b/resize'.format(CURRENT_VERSION, prefix):
    post_fake_resize_container,
    '{1}/{0}/containers/3cc2351ab11b/json'.format(CURRENT_VERSION, prefix):
    get_fake_inspect_container,
    '{1}/{0}/containers/3cc2351ab11b/rename'.format(CURRENT_VERSION, prefix):
    post_fake_rename_container,
    '{1}/{0}/images/e9aa60c60128/tag'.format(CURRENT_VERSION, prefix):
    post_fake_tag_image,
    '{1}/{0}/containers/3cc2351ab11b/wait'.format(CURRENT_VERSION, prefix):
    get_fake_wait,
    '{1}/{0}/containers/3cc2351ab11b/logs'.format(CURRENT_VERSION, prefix):
    get_fake_logs,
    '{1}/{0}/containers/3cc2351ab11b/changes'.format(CURRENT_VERSION, prefix):
    get_fake_diff,
    '{1}/{0}/containers/3cc2351ab11b/export'.format(CURRENT_VERSION, prefix):
    get_fake_export,
    '{1}/{0}/containers/3cc2351ab11b/update'.format(CURRENT_VERSION, prefix):
    post_fake_update_container,
    '{1}/{0}/containers/3cc2351ab11b/exec'.format(CURRENT_VERSION, prefix):
    post_fake_exec_create,
    '{1}/{0}/exec/d5d177f121dc/start'.format(CURRENT_VERSION, prefix):
    post_fake_exec_start,
    '{1}/{0}/exec/d5d177f121dc/json'.format(CURRENT_VERSION, prefix):
    get_fake_exec_inspect,
    '{1}/{0}/exec/d5d177f121dc/resize'.format(CURRENT_VERSION, prefix):
    post_fake_exec_resize,

    '{1}/{0}/containers/3cc2351ab11b/stats'.format(CURRENT_VERSION, prefix):
    get_fake_stats,
    '{1}/{0}/containers/3cc2351ab11b/top'.format(CURRENT_VERSION, prefix):
    get_fake_top,
    '{1}/{0}/containers/3cc2351ab11b/stop'.format(CURRENT_VERSION, prefix):
    post_fake_stop_container,
    '{1}/{0}/containers/3cc2351ab11b/kill'.format(CURRENT_VERSION, prefix):
    post_fake_kill_container,
    '{1}/{0}/containers/3cc2351ab11b/pause'.format(CURRENT_VERSION, prefix):
    post_fake_pause_container,
    '{1}/{0}/containers/3cc2351ab11b/unpause'.format(CURRENT_VERSION, prefix):
    post_fake_unpause_container,
    '{1}/{0}/containers/3cc2351ab11b/restart'.format(CURRENT_VERSION, prefix):
    post_fake_restart_container,
    '{1}/{0}/containers/3cc2351ab11b'.format(CURRENT_VERSION, prefix):
    delete_fake_remove_container,
    '{1}/{0}/images/create'.format(CURRENT_VERSION, prefix):
    post_fake_image_create,
    '{1}/{0}/images/e9aa60c60128'.format(CURRENT_VERSION, prefix):
    delete_fake_remove_image,
    '{1}/{0}/images/e9aa60c60128/get'.format(CURRENT_VERSION, prefix):
    get_fake_get_image,
    '{1}/{0}/images/load'.format(CURRENT_VERSION, prefix):
    post_fake_load_image,
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
    post_fake_build_container,
    '{1}/{0}/events'.format(CURRENT_VERSION, prefix):
    get_fake_events,
    ('{1}/{0}/volumes'.format(CURRENT_VERSION, prefix), 'GET'):
    get_fake_volume_list,
    ('{1}/{0}/volumes/create'.format(CURRENT_VERSION, prefix), 'POST'):
    get_fake_volume,
    ('{1}/{0}/volumes/{2}'.format(
        CURRENT_VERSION, prefix, FAKE_VOLUME_NAME
    ), 'GET'):
    get_fake_volume,
    ('{1}/{0}/volumes/{2}'.format(
        CURRENT_VERSION, prefix, FAKE_VOLUME_NAME
    ), 'DELETE'):
    fake_remove_volume,
    ('{1}/{0}/nodes/{2}/update?version=1'.format(
        CURRENT_VERSION, prefix, FAKE_NODE_ID
    ), 'POST'):
    post_fake_update_node,
    ('{1}/{0}/swarm/join'.format(CURRENT_VERSION, prefix), 'POST'):
    post_fake_join_swarm,
    ('{1}/{0}/networks'.format(CURRENT_VERSION, prefix), 'GET'):
    get_fake_network_list,
    ('{1}/{0}/networks/create'.format(CURRENT_VERSION, prefix), 'POST'):
    post_fake_network,
    ('{1}/{0}/networks/{2}'.format(
        CURRENT_VERSION, prefix, FAKE_NETWORK_ID
    ), 'GET'):
    get_fake_network,
    ('{1}/{0}/networks/{2}'.format(
        CURRENT_VERSION, prefix, FAKE_NETWORK_ID
    ), 'DELETE'):
    delete_fake_network,
    ('{1}/{0}/networks/{2}/connect'.format(
        CURRENT_VERSION, prefix, FAKE_NETWORK_ID
    ), 'POST'):
    post_fake_network_connect,
    ('{1}/{0}/networks/{2}/disconnect'.format(
        CURRENT_VERSION, prefix, FAKE_NETWORK_ID
    ), 'POST'):
    post_fake_network_disconnect,
}
