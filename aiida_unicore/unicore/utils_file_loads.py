'''
Created on May 14, 2019

@author: Tim Kreuzer
@mail: t.kreuzer@fz-juelich.de
'''

import json 

def get_j4j_unicore_token():
    with open('/etc/j4j/j4j_mount/j4j_token/unicore.token') as f:
        token = f.read().rstrip()
    return token

def get_j4j_tunnel_token():
    with open('/etc/j4j/j4j_mount/j4j_token/tunnel.token') as f:
        token = f.read().rstrip()
    return token

def get_j4j_orchestrator_token():
    with open('/etc/j4j/j4j_mount/j4j_token/orchestrator.token') as f:
        token = f.read().rstrip()
    return token

def get_jhubtoken():
    with open('/etc/j4j/j4j_mount/j4j_token/jhub.token') as f:
        token = f.read().rstrip()
    return token

def get_base_url():
    with open('/etc/j4j/j4j_mount/j4j_unicore/base_url.json', 'r') as f:
        base = json.load(f)
    return base.get('base_url', '/')

def get_unicorex():
    with open('/etc/j4j/j4j_mount/j4j_common/unicore.json', 'r') as f:
        data = json.load(f)
    return data

def get_jlab_conf():
    with open('/etc/j4j/j4j_mount/j4j_unicore/jupyterlab.conf', 'r') as f:
        conf = f.read().rstrip()
    return conf

def get_inputs():
    with open('/etc/j4j/j4j_mount/j4j_unicore/inputs.json', 'r') as f:
        inps = json.load(f)
    return inps

def get_hub_port():
    with open('/etc/j4j/j4j_mount/j4j_unicore/hub.port', 'r') as f:
        hubport = f.read().rstrip()
    return hubport

def get_fastnet_changes(node):
    with open('/etc/j4j/j4j_mount/j4j_unicore/fastnet.json', 'r') as f:
        fastnet = json.load(f)
    return fastnet.get(node, node)

def get_unity():
    with open('/etc/j4j/j4j_mount/j4j_common/unity.json', 'r') as f:
        unity = json.load(f)
    return unity

def get_urls():
    with open('/etc/j4j/j4j_mount/j4j_common/urls.json', 'r') as f:
        unity = json.load(f)
    return unity

def map_error_messages():
    with open('/etc/j4j/j4j_mount/j4j_unicore/map_error_messages.json', 'r') as f:
        ret = json.load(f)
    return ret

def get_dashboards():
    with open('/etc/j4j/j4j_mount/j4j_common/dashboards.json', 'r') as f:
        data = json.load(f)
    return data

def get_cron_info():
    with open('/etc/j4j/j4j_mount/j4j_common/cronjob.json', 'r') as f:
        cron = json.load(f)
    return cron
