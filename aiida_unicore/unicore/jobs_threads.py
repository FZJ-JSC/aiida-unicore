'''
Created on May 14, 2019

@author: Tim Kreuzer
@mail: t.kreuzer@fz-juelich.de
'''

import time
import json

from app import unicore_communication, hub_communication,\
    tunnel_utils, orchestrator_communication, utils_file_loads
from app.unity_communication import renew_token
from app.utils import remove_secret
from app.jobs_utils import stop_job

def get(app_logger, uuidcode, request_headers, unicore_header, app_urls, cert):
    try:
        servername = request_headers.get('servername')
        if ':' in servername:
            servername = servername.split(':')[1]
        else:
            servername = ''
        counter = 0
        children = []
        status = ''
        accesstoken = request_headers.get('accesstoken')
        expire = request_headers.get('expire')
        while True:
            # start with sleep, this function is only called, if .host was not in children
            time.sleep(3)
            # renew token. This may be run for a long time, so the accesstoken can expire 
            accesstoken, expire = renew_token(app_logger,
                                              uuidcode,
                                              request_headers.get("tokenurl"),
                                              request_headers.get("authorizeurl"),
                                              request_headers.get("refreshtoken"),
                                              accesstoken,
                                              expire,
                                              request_headers.get('jhubtoken'),
                                              app_urls.get('hub', {}).get('url_proxy_route'),
                                              app_urls.get('hub', {}).get('url_token'),
                                              request_headers.get('escapedusername'),
                                              request_headers.get('servername'))
            unicore_header['Authorization'] = 'Bearer {}'.format(accesstoken)
    
            for i in range(3):  # @UnusedVariable
                properties_json = {}
                try:
                    method = "GET"
                    method_args = {"url": request_headers.get('kernelurl'),
                                   "headers": unicore_header,
                                   "certificate": cert}
                    app_logger.info("uuidcode={} - Get Properties of UNICORE/X Job {}".format(uuidcode, request_headers.get('kernelurl')))
                    text, status_code, response_header = unicore_communication.request(app_logger,
                                                                                       uuidcode,
                                                                                       method,
                                                                                       method_args)
                    if status_code == 200:
                        unicore_header['X-UNICORE-SecuritySession'] = response_header['X-UNICORE-SecuritySession']
                        properties_json = json.loads(text)
                        if properties_json.get('status') == 'UNDEFINED' and i < 4:
                            app_logger.debug("uuidcode={} - Received status UNDEFINED. Try again in 2 seconds".format(uuidcode))
                            time.sleep(2)
                        else:
                            break
                    elif status_code == 404:
                        if i < 4:
                            app_logger.debug("uuidcode={} - Could not get properties. 404 Not found. Sleep for 2 seconds and try again".format(uuidcode))
                            time.sleep(2)
                        else:
                            orchestrator_communication.set_skip(app_logger,
                                                                uuidcode,
                                                                app_urls.get('orchestrator', {}).get('url_skip'),
                                                                request_headers.get('servername'),
                                                                'False')
                            app_logger.error("uuidcode={} - Could not get properties. 404 Not found. Do nothing and return. {} {} {}".format(uuidcode, text, status_code, remove_secret(response_header)))
                            return "", 539
                    elif status_code == 500:
                        if i < 4:
                            app_logger.debug("uuidcode={} - Could not get properties. Sleep for 2 seconds and try again".format(uuidcode))
                            time.sleep(2)
                        else:
                            app_logger.error("uuidcode={} - UNICORE RESTART REQUIRED!!. system: {}".format(uuidcode, request_headers.get('system', '<system_unknown>')))
                            app_logger.warning("uuidcode={} - Could not get properties. UNICORE/X Response: {} {} {}".format(uuidcode, text, status_code, remove_secret(response_header)))
                            app_logger.warning("uuidcode={} - Do not send update to JupyterHub.".format(uuidcode))
                            # If JupyterHub don't receives an update for a long time it can stop the job itself.
                            orchestrator_communication.set_skip(app_logger,
                                                                uuidcode,
                                                                app_urls.get('orchestrator', {}).get('url_skip'),
                                                                request_headers.get('servername'),
                                                                'False')
                            return "", 539
                    else:
                        app_logger.error("uuidcode={} - Unknown status_code. Add case for this".format(uuidcode))
                        if i < 4:
                            app_logger.debug("uuidcode={} - Could not get properties. Sleep for 2 seconds and try again".format(uuidcode))
                            time.sleep(2)
                        else:
                            app_logger.warning("uuidcode={} - Could not get properties. UNICORE/X Response: {} {} {}".format(uuidcode, text, status_code, remove_secret(response_header)))
                            raise Exception("{} - Could not get properties. Throw exception because of wrong status_code: {}".format(uuidcode, status_code))
                except:
                    orchestrator_communication.set_skip(app_logger,
                                                        uuidcode,
                                                        app_urls.get('orchestrator', {}).get('url_skip'),
                                                        request_headers.get('servername'),
                                                        'False')
                    app_logger.exception("uuidcode={} - Could not get properties. Try to stop it {} {}".format(uuidcode, method, remove_secret(method_args)))
                    app_logger.trace("uuidcode={} - Call stop_job".format(uuidcode))
                    try:
                        stop_job(app_logger,
                                 uuidcode,
                                 servername,
                                 request_headers.get('system'),
                                 request_headers,
                                 app_urls,
                                 True,
                                 "Jupyter@JSC backend error. An administrator is informed. Please try again in a few minutes.")
                    except:
                        app_logger.exception("uuidcode={} - Could not stop Job. It may still run".format(uuidcode))
                    return "", 539
    
            if properties_json.get('status') in ['SUCCESSFUL', 'ERROR', 'FAILED', 'NOT_SUCCESSFUL']:
                # Job is Finished for UNICORE, so it should be for JupyterHub
                orchestrator_communication.set_skip(app_logger,
                                                    uuidcode,
                                                    app_urls.get('orchestrator', {}).get('url_skip'),
                                                    request_headers.get('servername'),
                                                    'False')
                if not properties_json.get('statusMessage') == 'Job was aborted by the user.':
                    app_logger.error('uuidcode={} - Get: Job is finished or failed - JobStatus: {}. Send Information to JHub.\n{}'.format(uuidcode, properties_json.get('status'), properties_json))
                app_logger.trace("uuidcode={} - Call stop_job".format(uuidcode))
                error_msg = ""
                try:
                    mem = utils_file_loads.map_error_messages()
                    if properties_json.get('status') in ['FAILED'] and properties_json.get('statusMessage') in mem.keys():
                        error_msg = mem.get(properties_json.get('statusMessage', ''), "Could not start your Job. Please check your configuration. An administrator is informed.")
                    else:
                        app_logger.error("uuidcode={} - StatusMessage from Failed UNICORE Job not found in /etc/j4j/j4j_mount/j4j_unicore/map_error_messages.json. Please update to have a better user experience".format(uuidcode))
                        error_msg = "Could not start your Job. Please check your configuration. An administrator is informed."
                except:
                    error_msg = "Could not start your Job. Please check your configuration. An administrator is informed."
                try:
                    stop_job(app_logger,
                             uuidcode,
                             servername,
                             request_headers.get('system'),
                             request_headers,
                             app_urls,
                             True,
                             error_msg)
                except:
                    app_logger.exception("uuidcode={} - Could not stop Job. It may still run".format(uuidcode))
                return "", 530
            
            try:
                method = "GET"
                method_args = {"url": request_headers.get('filedir'),
                               "headers": unicore_header,
                               "certificate": cert} 
                text, status_code, response_header = unicore_communication.request(app_logger,
                                                                                   uuidcode,
                                                                                   method,
                                                                                   method_args)
                if status_code == 200:
                    unicore_header['X-UNICORE-SecuritySession'] = response_header['X-UNICORE-SecuritySession']
                    # in UNICORE 8 the answer is a bit different
                    children_json = json.loads(text)
                    if 'children' in children_json.keys():
                        children = json.loads(text).get('children', [])
                    elif 'content' in children_json.keys():
                        children = list(json.loads(text).get('content', {}).keys())
                    else:
                        app_logger.warning("uuidcode={} - Could not find any childrens in {}".format(uuidcode, text))
                        children = []
                elif status_code == 404:
                    orchestrator_communication.set_skip(app_logger,
                                                        uuidcode,
                                                        app_urls.get('orchestrator', {}).get('url_skip'),
                                                        request_headers.get('servername'),
                                                        'False')
                    app_logger.warning("uuidcode={} - Could not get properties. 404 Not found. Do nothing and return. {} {} {}".format(uuidcode, text, status_code, remove_secret(response_header)))
                    return "", 539
                else:
                    app_logger.warning("uuidcode={} - Could not get information about filedirectory. UNICORE/X Response: {} {} {}".format(uuidcode, text, status_code, remove_secret(response_header)))
                    raise Exception("{} - Could not get information about filedirectory. Throw Exception because of wrong status_code: {}".format(uuidcode, status_code))
            except:
                counter += 1
                if counter > 10:
                    app_logger.error("uuidcode={} - Get filelist ({}) failed 10 times over 30 seconds. {} {}".format(uuidcode, request_headers.get('filedir'), method, remove_secret(method_args)))
                    app_logger.trace("uuidcode={} - Call stop_job".format(uuidcode))
                    try:
                        stop_job(app_logger,
                                 uuidcode,
                                 servername,
                                 request_headers.get('system'),
                                 request_headers,
                                 app_urls)
                    except:
                        app_logger.exception("uuidcode={} - Could not stop Job. It may still run".format(uuidcode))
                app_logger.info("uuidcode={} - Get filelist ({}) failed {} time(s)".format(uuidcode, request_headers.get('filedir'), counter))
                hub_communication.status(app_logger,
                                         uuidcode,
                                         app_urls.get('hub', {}).get('url_proxy_route'),
                                         app_urls.get('hub', {}).get('url_status'),
                                         request_headers.get('jhubtoken'),
                                         'waitforhostname',
                                         request_headers.get('escapedusername'),
                                         servername)
                continue
            if '.end' in children or '/.end' in children:
                # It's not running anymore
                status = 'stopped'
            elif '.host' in children or '/.host' in children:
                # running, build up tunnel
                try:
                    tunnel_utils.create(app_logger,
                                        uuidcode,
                                        app_urls.get('hub', {}).get('url_proxy_route'),
                                        app_urls.get('tunnel', {}).get('url_tunnel'),
                                        app_urls.get('hub', {}).get('url_cancel'),
                                        request_headers.get('kernelurl'),
                                        request_headers.get('filedir'),
                                        unicore_header,
                                        request_headers.get('servername'),
                                        request_headers.get('system'),
                                        request_headers.get('port'),
                                        cert,
                                        request_headers.get('jhubtoken'),
                                        request_headers.get('escapedusername'),
                                        servername)
                except:
                    orchestrator_communication.set_skip(app_logger,
                                                        uuidcode,
                                                        app_urls.get('orchestrator', {}).get('url_skip'),
                                                        request_headers.get('servername'),
                                                        'False')
                    app_logger.exception("uuidcode={} - Could not create tunnel".format(uuidcode))
                    app_logger.trace("uuidcode={} - Call stop_job".format(uuidcode))
                    try:
                        stop_job(app_logger,
                                 uuidcode,
                                 servername,
                                 request_headers.get('system'),
                                 request_headers,
                                 app_urls)
                    except:
                        app_logger.exception("uuidcode={} - Could not stop Job. It may still run".format(uuidcode))
                    return
                status = "running"
            else:
                app_logger.info("uuidcode={} - Update JupyterHub status ({})".format(uuidcode, "waitforhostname"))
                hub_communication.status(app_logger,
                                         uuidcode,
                                         app_urls.get('hub', {}).get('url_proxy_route'),
                                         app_urls.get('hub', {}).get('url_status'),
                                         request_headers.get('jhubtoken'),
                                         "waitforhostname",
                                         request_headers.get('escapedusername'),
                                         servername)
                continue
            app_logger.info("uuidcode={} - Update JupyterHub status ({})".format(uuidcode, status))
            hub_communication.status(app_logger,
                                     uuidcode,
                                     app_urls.get('hub', {}).get('url_proxy_route'),
                                     app_urls.get('hub', {}).get('url_status'),
                                     request_headers.get('jhubtoken'),
                                     status,
                                     request_headers.get('escapedusername'),
                                     servername)
            if status in ['running', 'stopped'] and request_headers.get('spawning', 'true').lower() == 'true': # spawning is finished
                app_logger.trace('uuidcode={} - Tell J4J_Orchestrator that the spawning is done'.format(uuidcode))
                try:
                    orchestrator_communication.set_spawning(app_logger,
                                                            uuidcode,
                                                            app_urls.get('orchestrator', {}).get('url_spawning'),
                                                            request_headers.get('servername'),
                                                            'False')
                except:
                    app_logger.exception("uuidcode={} - Could not set spawning to false in J4J_Orchestrator database for {}".format(uuidcode, request_headers.get('servername')))
            orchestrator_communication.set_skip(app_logger,
                                                uuidcode,
                                                app_urls.get('orchestrator', {}).get('url_skip'),
                                                request_headers.get('servername'),
                                                'False')
            return
    except:
        app_logger.exception("uuidcode={} - Bugfix required".format(uuidcode))
