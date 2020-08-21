'''
Created on May 14, 2019

@author: Tim Kreuzer
@mail: t.kreuzer@fz-juelich.de
'''

import requests

from contextlib import closing

from app.utils_file_loads import get_j4j_orchestrator_token

def set_spawning(app_logger, uuidcode, orchestrator_url, servername, value):
    app_logger.debug("uuidcode={} - Call Orchestrator to finish spawning for servername {} (value: {})".format(uuidcode, servername, value))
    header = { 'Intern-Authorization': get_j4j_orchestrator_token(),
               'uuidcode': uuidcode }
    data_json = { 'servername': servername,
                  'value': value }
    with closing(requests.post(orchestrator_url,
                               headers=header,
                               json = data_json,
                               timeout = 1800)) as r:
        if r.status_code == 202:
            return
        raise Exception("{} - Received wrong status code from J4J_Orchestrator: {} {} {}".format(uuidcode, r.status_code, r.text, r.headers))

def set_skip(app_logger, uuidcode, orchestrator_url, servername, value):
    app_logger.debug("uuidcode={} - Call Orchestrator to set skip for servername {} (value: {})".format(uuidcode, servername, value))
    header = { 'Intern-Authorization': get_j4j_orchestrator_token(),
               'uuidcode': uuidcode }
    data_json = { 'servername': servername,
                  'value': value }
    with closing(requests.post(orchestrator_url,
                               headers=header,
                               json = data_json,
                               timeout = 1800)) as r:
        if r.status_code == 202:
            return
        raise Exception("{} - Received wrong status code from J4J_Orchestrator: {} {} {}".format(uuidcode, r.status_code, r.text, r.headers))


def delete_database_entry(app_logger, uuidcode, orchestrator_url, servername):
    app_logger.debug("uuidcode={} - Call Orchestrator to delete database entry for servername {}".format(uuidcode, servername))
    header = { 'Intern-Authorization': get_j4j_orchestrator_token(),
               'uuidcode': uuidcode,
               'servername': servername }
    with closing(requests.delete(orchestrator_url,
                                 headers=header,
                                 data="{}",
                                 timeout = 1800)) as r:
        if r.status_code == 200 or r.status_code == 204:
            return
        raise Exception("{} - Received wrong status code from J4J_Orchestrator: {} {} {}".format(uuidcode, r.status_code, r.text, r.headers))
