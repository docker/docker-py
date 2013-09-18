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

import base64
import json
import os

import six

import utils

INDEX_URL = 'https://index.docker.io/v1/'

def swap_protocol(url):
    if url.startswith('http://'):
        return url.replace('http://', 'https://', 1)
    if url.startswith('https://'):
        return url.replace('https://', 'http://', 1)
    return url


def expand_registry_url(hostname):
    if hostname.startswith('http:') or hostname.startswith('https:'):
        if '/' not in hostname[9:]:
            hostname = hostname + '/v1/'
        return hostname
    if utils.ping('https://' + hostname + '_ping'):
        return 'https://' + hostname + '/v1/'
    return 'http://' + hostname + '/v1/'


def resolve_repository_name(repo_name):
    if '://' in repo_name:
        raise ValueError('Repository name can not contain a'
                         'scheme ({0})'.format(repo_name))
    parts = repo_name.split('/', 1)
    if not '.' in parts[0] and not ':' in parts[0] and parts[0] != 'localhost':
        # This is a docker index repo (ex: foo/bar or ubuntu)
        return INDEX_URL, repo_name
    if len(parts) < 2:
        raise ValueError('Invalid repository name ({0})'.format(repo_name))

    if 'index.docker.io' in parts[0]:
        raise ValueError('Invalid repository name,'
                         'try "{0}" instead'.format(parts[1]))

    return expand_registry_url(parts[0]), parts[1]


def resolve_authconfig(authconfig, registry):
    if registry == INDEX_URL or registry == '':
        # default to the index server
        return authconfig['Configs'][INDEX_URL]
    # if its not the index server there are three cases:
    #
    # 1. this is a full config url -> it should be used as is
    # 2. it could be a full url, but with the wrong protocol
    # 3. it can be the hostname optionally with a port
    #
    # as there is only one auth entry which is fully qualified we need to start
    # parsing and matching
    if '/' not in registry:
        registry = registry + '/v1/'
    if not registry.startswith('http:') and not registry.startswith('https:'):
        registry = 'https://' + registry

    if registry in authconfig['Configs']:
        return authconfig['Configs'][registry]
    elif swap_protocol(registry) in authconfig['Configs']:
        return authconfig['Configs'][swap_protocol(registry)]
    return {}


def decode_auth(auth):
    s = base64.b64decode(auth)
    login, pwd = s.split(':')
    return login, pwd


def encode_header(auth):
    auth_json = json.dumps(auth)
    return base64.b64encode(auth_json)


def load_config(root=None):
    if root is None:
        root = os.environ['HOME']
    config_file = {
        'Configs': {},
        'rootPath': root
    }
    f = open(os.path.join(root, '.dockercfg'))
    try:
        config_file['Configs'] = json.load(f)
        for k, conf in six.iteritems(config_file['Configs']):
            conf['Username'], conf['Password'] = decode_auth(conf['auth'])
            del conf['auth']
            config_file['Configs'][k] = conf
    except Exception:
        f.seek(0)
        buf = []
        for line in f:
            k, v = line.split(' = ')
            buf.append(v)
        if len(buf) < 2:
            raise Exception("The Auth config file is empty")
        user, pwd = decode_auth(buf[0])
        config_file['Configs'][INDEX_URL] = {
            'Username': user,
            'Password': pwd,
            'Email': buf[1]
        }
    finally:
        f.close()
    return config_file
