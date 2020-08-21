'''
Created on May 14, 2019

@author: Tim Kreuzer
@mail: t.kreuzer@fz-juelich.de
'''

import base64
import time
import requests
from contextlib import closing

from app.utils_file_loads import get_unity
from app import hub_communication
from app.utils import remove_secret, SpawnException
import json


def renew_token(app_logger, uuidcode, token_url, authorize_url, refreshtoken, accesstoken, expire, jhubtoken, app_hub_url_proxy_route, app_hub_url_token, username, servername=''):
    if int(expire) - int(time.time()) > 60:
        return accesstoken, expire
    app_logger.info("uuidcode={} - Renew Token: Expire at {} , time: {}".format(uuidcode, int(expire), int(time.time())))
    unity = get_unity()
    if token_url == '':
        app_logger.warning("uuidcode={} - Use default token_url. Please send token_url in header".format(uuidcode))
        token_url = unity.get('links').get('token')
    tokeninfo_url = unity[token_url].get('links', {}).get('tokeninfo')
    cert_path = unity[token_url].get('certificate', False)
    scope = ' '.join(unity[authorize_url].get('scope'))
    b64key = base64.b64encode(bytes('{}:{}'.format(unity[token_url].get('client_id'), unity[token_url].get('client_secret')), 'utf-8')).decode('utf-8')
    data = {'refresh_token': refreshtoken,
            'grant_type': 'refresh_token',
            'scope': scope}
    headers = { 'Authorization': 'Basic {}'.format(b64key),
                'Accept': 'application/json' }
    app_logger.info("uuidcode={} - Post to {}".format(uuidcode, token_url))
    app_logger.trace("uuidcode={} - Header: {}".format(uuidcode, headers))
    app_logger.trace("uuidcode={} - Data: {}".format(uuidcode, data))
    try:
        with closing(requests.post(token_url,
                                   headers = headers,
                                   data = data,
                                   verify = cert_path,
                                   timeout = 1800)) as r:
            app_logger.trace("uuidcode={} - Unity Response: {} {} {} {}".format(uuidcode, r.text, r.status_code, remove_secret(r.headers), remove_secret(r.json)))
            if r.status_code == 400:
                # wrong refresh_token, send cancel
                error_msg = "Unknown Error. An Administrator is informed."
                try:
                    r_json = json.loads(r.text)
                    if r_json.get('error_description', '') != "Invalid request; wrong refresh token":
                        app_logger.error("uuidcode={} - Received unknown answer from Unity: {}".format(uuidcode, r.text))
                    else:
                        error_msg = "Invalid token. Please logout and login again."
                except:
                    try:
                        app_logger.exception("uuidcode={} - Could not check for Unity error description: {}".format(uuidcode, r.text))
                    except:
                        app_logger.exception("uuidcode={} - Could not check for Unity error description".format(uuidcode))
                raise SpawnException(error_msg)
            accesstoken = r.json().get('access_token')
        with closing(requests.get(tokeninfo_url,
                                  headers = { 'Authorization': 'Bearer {}'.format(accesstoken) },
                                  verify = cert_path,
                                  timeout = 1800)) as r:
            app_logger.trace("uuidcode={} - Unity Response: {} {} {} {}".format(uuidcode, r.text, r.status_code, remove_secret(r.headers), remove_secret(r.json)))
            expire = r.json().get('exp')
    except SpawnException as e:
        raise SpawnException(str(e))
    except:
        app_logger.exception("uuidcode={} - Could not update token".format(uuidcode))
        raise Exception("{} - Could not update token".format(uuidcode))
    app_logger.info("uuidcode={} - Update JupyterHub Token".format(uuidcode))
    hub_communication.token(app_logger,
                            uuidcode,
                            app_hub_url_proxy_route,
                            app_hub_url_token,
                            jhubtoken,
                            accesstoken,
                            expire,
                            username,
                            servername)
    return accesstoken, expire
