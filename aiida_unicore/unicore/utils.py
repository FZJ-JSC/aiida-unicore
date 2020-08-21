'''
Created on May 14, 2019

@author: Tim Kreuzer
@mail: t.kreuzer@fz-juelich.de
'''

from flask_restful import abort

from app.utils_file_loads import get_j4j_unicore_token


def validate_auth(app_logger, uuidcode, intern_authorization):
    if not intern_authorization == None:
        token = get_j4j_unicore_token()
        if intern_authorization == token:
            app_logger.debug("uuidcode={} - Intern-Authorization validated".format(uuidcode))
            return
    app_logger.warning("uuidcode={} - Could not validate Token:\n{}".format(uuidcode, intern_authorization))
    abort(401)

def remove_secret(json_dict):
    if type(json_dict) != dict:
        return json_dict
    secret_dict = {}
    for key, value in json_dict.items():
        if type(value) == dict:
            secret_dict[key] = remove_secret(value)
        elif key.lower() in ["authorization", "accesstoken", "refreshtoken", "jhubtoken", "intern-authorization"]:
            secret_dict[key] = '<secret>'
        else:
            secret_dict[key] = value
    return secret_dict

class SpawnException(Exception):
    pass