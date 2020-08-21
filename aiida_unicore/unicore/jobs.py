'''
Created on May 14, 2019

@author: Tim Kreuzer
@mail: t.kreuzer@fz-juelich.de
'''

import json

from threading import Thread
from flask import request
from flask_restful import Resource
from flask import current_app as app

from app.utils import validate_auth, remove_secret, SpawnException
from app.jobs_utils import stop_job
from app import unicore_utils, utils_file_loads, unicore_communication,\
    hub_communication, tunnel_utils, jobs_threads, orchestrator_communication
from time import sleep

class Jobs(Resource):
    def get(self):
        try:
            # Track actions through different webservices.
            uuidcode = request.headers.get('uuidcode', '<no uuidcode>')
            app.log.info("uuidcode={} - Get Server Status".format(uuidcode))
            app.log.trace("uuidcode={} - Headers: {}".format(uuidcode, request.headers))
    
            # Check for J4J intern token
            validate_auth(app.log,
                          uuidcode,
                          request.headers.get('intern-authorization'))
            servername = request.headers.get('servername')
    
            # Create UNICORE header and get certificate
            try:
                unicore_header, accesstoken, expire = unicore_utils.create_header(app.log,     # @UnusedVariable
                                                                                  uuidcode,
                                                                                  request.headers,
                                                                                  app.urls.get('hub', {}).get('url_proxy_route'),
                                                                                  app.urls.get('hub', {}).get('url_token'),
                                                                                  request.headers.get('escapedusername'),
                                                                                  servername)
            except (SpawnException, Exception):
                app.log.exception("uuidcode={} - Could not Create Header. Token from user {} might be revoked. Do nothing and return.".format(uuidcode, request.headers.get('escapedusername')))
                # Return positive status: Administrator is informed and there is nothing we can do here otherwise.
                return "", 200
            app.log.trace("uuidcode={} - FileLoad: UNICORE/X certificate path".format(uuidcode))
            unicorex = utils_file_loads.get_unicorex()
            cert = unicorex.get(request.headers.get('system', ''), {}).get('certificate', False)
            app.log.trace("uuidcode={} - FileLoad: UNICORE/X certificate path Result: {}".format(uuidcode, cert))
    
            # Get Properties of kernelurl
            kernelurl = request.headers.get('kernelurl')
            for i in range(5):  # @UnusedVariable
                properties_json = {}
                try:
                    method = "GET"
                    method_args = {"url": kernelurl,
                                   "headers": unicore_header,
                                   "certificate": cert}
                    app.log.info("uuidcode={} - Get Properties of UNICORE/X Job {}".format(uuidcode, kernelurl))
                    text, status_code, response_header = unicore_communication.request(app.log,
                                                                                       uuidcode,
                                                                                       method,
                                                                                       method_args)
                    if status_code == 200:
                        unicore_header['X-UNICORE-SecuritySession'] = response_header['X-UNICORE-SecuritySession']
                        properties_json = json.loads(text)
                        if properties_json.get('status') == 'UNDEFINED' and i < 4:
                            app.log.debug("uuidcode={} - Received status UNDEFINED. Try again in 2 seconds".format(uuidcode))
                            sleep(2)
                        else:
                            break
                    elif status_code == 404:
                        if i < 4:
                            app.log.debug("uuidcode={} - Could not get properties. 404 Not found. Sleep for 2 seconds and try again".format(uuidcode))
                            sleep(2)
                        else:
                            app.log.warning("uuidcode={} - Could not get properties. 404 Not found. Stop Job and return. {} {} {}".format(uuidcode, text, status_code, remove_secret(response_header)))
                            orchestrator_communication.set_skip(app.log,
                                                                uuidcode,
                                                                app.urls.get('orchestrator', {}).get('url_skip'),
                                                                request.headers.get('servername'),
                                                                'False')
                            try:
                                stop_job(app.log,
                                         uuidcode,
                                         servername,
                                         request.headers.get('system'),
                                         request.headers,
                                         app.urls,
                                         True,
                                         '',
                                         False)
                            except:
                                app.log.exception("uuidcode={} - Could not stop Job. It may still run".format(uuidcode))
                            return "", 539
                    elif status_code == 500:
                        if i < 4:
                            app.log.debug("uuidcode={} - Could not get properties. Sleep for 2 seconds and try again".format(uuidcode))
                            sleep(2)
                        else:
                            app.log.error("uuidcode={} - UNICORE RESTART REQUIRED!!. system: {}".format(uuidcode, request.headers.get('system', '<system_unknown>')))
                            app.log.warning("uuidcode={} - Could not get properties. UNICORE/X Response: {} {} {}".format(uuidcode, text, status_code, remove_secret(response_header)))
                            app.log.warning("uuidcode={} - Do not send update to JupyterHub.".format(uuidcode))
                            # If JupyterHub don't receives an update for a long time it can stop the job itself.
                            orchestrator_communication.set_skip(app.log,
                                                                uuidcode,
                                                                app.urls.get('orchestrator', {}).get('url_skip'),
                                                                request.headers.get('servername'),
                                                                'False')
                            return "", 539
                    else:
                        app.log.error("uuidcode={} - Unknown status_code received. Add case for this: {} {}".format(uuidcode, status_code, text))
                        if i < 4:
                            app.log.debug("uuidcode={} - Could not get properties. Sleep for 2 seconds and try again".format(uuidcode))
                            sleep(2)
                        else:
                            app.log.warning("uuidcode={} - Could not get properties. UNICORE/X Response: {} {} {}".format(uuidcode, text, status_code, remove_secret(response_header)))
                            raise Exception("{} - Could not get properties. Throw exception because of wrong status_code: {}".format(uuidcode, status_code))
                except:
                    app.log.exception("uuidcode={} - Could not get properties. JupyterLab will be still running. {} {}".format(uuidcode, method, remove_secret(method_args)))
                    app.log.warning("uuidcode={} - Do not send update to JupyterHub.".format(uuidcode))
                    # If JupyterHub don't receives an update for a long time it can stop the job itself.
                    orchestrator_communication.set_skip(app.log,
                                                        uuidcode,
                                                        app.urls.get('orchestrator', {}).get('url_skip'),
                                                        request.headers.get('servername'),
                                                        'False')
                    return "", 539
    
            if properties_json.get('status') in ['SUCCESSFUL', 'ERROR', 'FAILED', 'NOT_SUCCESSFUL']:
                # Job is Finished for UNICORE, so it should be for JupyterHub
                if request.headers.get('pollspawner', 'false').lower() == 'true':
                    app.log.error('uuidcode={} - Get (poll spawner): Job is finished or failed - JobStatus: {}. Send Information to JHub. {}'.format(uuidcode, properties_json.get('status'), properties_json))
                    if properties_json.get('statusMessage', '') == "Failed: Execution was not completed (no exit code file found), please check standard error file <stderr>":
                        app.log.error("uuidcode={} - UNICORE hotfix: do nothing because that's most likely a bug.".format(uuidcode))
                        return "", 200
                else:
                    if not properties_json.get('statusMessage') == 'Job was aborted by the user.':
                        app.log.error('uuidcode={} - At starting process: Job is finished or failed - JobStatus: {}. Send Information to JHub. {}'.format(uuidcode, properties_json.get('status'), properties_json))
                app.log.trace("uuidcode={} - Call stop_job".format(uuidcode))
                orchestrator_communication.set_skip(app.log,
                                                    uuidcode,
                                                    app.urls.get('orchestrator', {}).get('url_skip'),
                                                    request.headers.get('servername'),
                                                    'False')
                error_msg = ""
                try:
                    mem = utils_file_loads.map_error_messages()
                    if properties_json.get('status') in ['FAILED'] and properties_json.get('statusMessage') in mem.keys():
                        error_msg = mem.get(properties_json.get('statusMessage', ''), "Could not start your Job. Please check your configuration. An administrator is informed.")
                    else:
                        for key, value in mem.items():
                            if properties_json.get('statusMessage', '').startswith(key):
                                error_msg = value
                        if error_msg == "":
                            if request.headers.get('pollspawner', 'false').lower() == 'true':
                                app.log.error("uuidcode={} - StatusMessage from Failed UNICORE Job not found in /etc/j4j/j4j_mount/j4j_unicore/map_error_messages.json. Please update to have a better user experience".format(uuidcode))
                            error_msg = "Could not start your Job. Please check your configuration. An administrator is informed."
                except:
                    error_msg = "Could not start your Job. Please check your configuration. An administrator is informed."
                try:
                    stop_job(app.log,
                             uuidcode,
                             servername,
                             request.headers.get('system'),
                             request.headers,
                             app.urls,
                             True,
                             error_msg)
                except:
                    app.log.exception("uuidcode={} - Could not stop Job. It may still run".format(uuidcode))
                return "", 530
    
            # The Job is not finished yet (good)
            # Get Files in the filedir
            children = []
            for i in range(5):  # @UnusedVariable
                try:
                    method = "GET"
                    method_args = {"url": request.headers.get('filedir'),
                                   "headers": unicore_header,
                                   "certificate": cert}
                    app.log.info("uuidcode={} - Get list of files of UNICORE/X Job {}".format(uuidcode, kernelurl))
                    text, status_code, response_header = unicore_communication.request(app.log,
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
                            app.log.warning("uuidcode={} - Could not find any childrens in {}".format(uuidcode, text))
                            children = []
                        if len(children) == 0 and i < 4:
                            app.log.debug("uuidcode={} - Received empty children list. Try again in 2 seconds".format(uuidcode))
                            sleep(2)
                        else:
                            break
                    elif status_code == 404:
                        if i < 4:
                            app.log.debug("uuidcode={} - Could not get children list. 404 Not found. Try again in 2 seconds.".format(uuidcode))
                            sleep(2)
                        else:
                            app.log.error("uuidcode={} - Could not get children list. 404 Not found. Do nothing and return. {} {} {}".format(uuidcode, text, status_code, remove_secret(response_header)))
                            orchestrator_communication.set_skip(app.log,
                                                                uuidcode,
                                                                app.urls.get('orchestrator', {}).get('url_skip'),
                                                                request.headers.get('servername'),
                                                                'False')
                            return "", 539
                    elif status_code == 500:
                        if i < 4:
                            app.log.debug("uuidcode={} - Could not get children list. Status Code 500. Try again in 2 seconds.".format(uuidcode))
                            sleep(2)
                        else:
                            app.log.error("uuidcode={} - UNICORE/X RESTART REQUIRED".format(uuidcode))
                            orchestrator_communication.set_skip(app.log,
                                                                uuidcode,
                                                                app.urls.get('orchestrator', {}).get('url_skip'),
                                                                request.headers.get('servername'),
                                                                'False')
                            return "", 539
                    else:
                        if i < 4:
                            app.log.debug("uuidcode={} - Could not get children list. Try again in 2 seconds".format(uuidcode))
                            sleep(2)
                        else:
                            app.log.error("uuidcode={} - Unknown status code. Add case for this: {} {}".format(status_code, text))
                            app.log.error("uuidcode={} - Could not get children list. Do nothing and return. UNICORE/X Response: {} {} {}".format(uuidcode, text, status_code, remove_secret(response_header)))
                            orchestrator_communication.set_skip(app.log,
                                                                uuidcode,
                                                                app.urls.get('orchestrator', {}).get('url_skip'),
                                                                request.headers.get('servername'),
                                                                'False')
                            return "", 539
                except:
                    app.log.error("uuidcode={} - UNICORE/X RESTART REQUIRED".format(uuidcode))
                    app.log.exception("uuidcode={} - Could not get children list. {} {}".format(uuidcode, method, remove_secret(method_args)))
                    orchestrator_communication.set_skip(app.log,
                                                        uuidcode,
                                                        app.urls.get('orchestrator', {}).get('url_skip'),
                                                        request.headers.get('servername'),
                                                        'False')
                    return "", 539
    
    
            # get the 'real' status of the job from the files in the working_directory
            # 'real' means: We don't care about Queued, ready, running or something. We just want to know: Is it bad (failed or cancelled) or good (running or spawning)
            status = ''
            if properties_json.get('status') in ['QUEUED', 'READY', 'RUNNING', 'STAGINGIN']:
                if '.end' in children or '/.end' in children:
                    # It's not running anymore
                    status = 'stopped'
                elif '.tunnel' in children or '/.tunnel' in children:
                    # It's running and tunnel is up
                    status = 'running'
                elif '.host' in children or '/.host' in children:
                    if request.headers.get('pollspawner', 'false').lower() == 'true':
                        # If there's an error when collecting the children list it may happen, that we would try to create a tunnel for a server that's already running for a long time
                        app.log.error('uuidcode={} - Poll Spawner wants to create tunnel. Stop it. Children list: {}'.format(uuidcode, children))
                        status = 'running'
                    else:
                        # build up tunnel
                        try:
                            tunnel_utils.create(app.log,
                                                uuidcode,
                                                app.urls.get('hub', {}).get('url_proxy_route'),
                                                app.urls.get('tunnel', {}).get('url_tunnel'),
                                                app.urls.get('hub', {}).get('url_cancel'),
                                                kernelurl,
                                                request.headers.get('filedir'),
                                                unicore_header,
                                                request.headers.get('servername'),
                                                request.headers.get('system'),
                                                request.headers.get('port'),
                                                cert,
                                                request.headers.get('jhubtoken'),
                                                request.headers.get('escapedusername'),
                                                servername)
                        except:
                            app.log.error("uuidcode={} - Could not create Tunnel. Used Parameters: {} {} {} {} {} {} {} {} {} {}".format(uuidcode,
                                                                                                                                app.urls.get('tunnel', {}).get('url_tunnel'),
                                                                                                                                app.urls.get('hub', {}).get('url_cancel'),
                                                                                                                                kernelurl,
                                                                                                                                request.headers.get('filedir'),
                                                                                                                                remove_secret(unicore_header),
                                                                                                                                request.headers.get('servername'),
                                                                                                                                request.headers.get('system'),
                                                                                                                                request.headers.get('port'),
                                                                                                                                cert,
                                                                                                                                '<secret>'))
                            app.log.trace("uuidcode={} - Call stop_job".format(uuidcode))
                            orchestrator_communication.set_skip(app.log,
                                                                uuidcode,
                                                                app.urls.get('orchestrator', {}).get('url_skip'),
                                                                request.headers.get('servername'),
                                                                'False')
                            try:
                                stop_job(app.log,
                                         uuidcode,
                                         servername,
                                         request.headers.get('system'),
                                         request.headers,
                                         app.urls,
                                         True,
                                         "Jupyter@JSC internal error. An administrator is informed. Please try again in a few minutes.")
                            except:
                                app.log.exception("uuidcode={} - Could not stop Job. It may still run".format(uuidcode))
                            return "", 539
                    status = 'running'
                else:
                    if request.headers.get('pollspawner', 'false').lower() == 'true':
                        # If there's an error when collecting the children list it may happen, that we would create a thread to get better information. We just send running and hope for the next run
                        app.log.error('uuidcode={} - Poll Spawner wants to create get_status thread. Prevent it. Children list: {}'.format(uuidcode, children))
                        status = 'running'
                    else:
                        request_headers = {}
                        for key, value in request.headers.items():
                            if 'Token' in key:
                                key = key.replace('-', '_')
                            request_headers[key.lower()] = value
                        app.log.trace("uuidcode={} - New Header for Thread: {}".format(uuidcode, request_headers))
                        # no .host in children, let's start a thread which looks for it every second
                        t = Thread(target=jobs_threads.get,
                                   args=(app.log,
                                         uuidcode,
                                         request_headers,
                                         unicore_header,
                                         app.urls,
                                         cert))
                        t.start()
                        status = 'waitforhostname'
                app.log.info("uuidcode={} - Update JupyterHub status ({})".format(uuidcode, status))
                hub_communication.status(app.log,
                                         uuidcode,
                                         app.urls.get('hub', {}).get('url_proxy_route'),
                                         app.urls.get('hub', {}).get('url_status'),
                                         request.headers.get('jhubtoken'),
                                         status,
                                         request.headers.get('escapedusername'),
                                         servername)
                if status in ['running', 'stopped'] and request.headers.get('spawning', 'true').lower() == 'true': # spawning is finished
                    app.log.trace('uuidcode={} - Tell J4J_Orchestrator that the spawning is done'.format(uuidcode))
                    try:
                        orchestrator_communication.set_spawning(app.log,
                                                                uuidcode,
                                                                app.urls.get('orchestrator', {}).get('url_spawning'),
                                                                request.headers.get('servername'),
                                                                'False')
                    except:
                        app.log.exception("uuidcode={} - Could not set spawning to false in J4J_Orchestrator database for {}".format(uuidcode, request_headers.get('servername')))
    
            else:
                app.log.error('uuidcode={} - Unknown JobStatus: {}'.format(uuidcode, properties_json.get('status')))
                app.log.trace("uuidcode={} - Call stop_job".format(uuidcode))
                try:
                    stop_job(app.log,
                             uuidcode,
                             servername,
                             request.headers.get('system'),
                             request.headers,
                             app.urls,
                             True,
                             "A backend Service had a problem. An administrator is informed. Please try it again in a few minutes.")
                except:
                    app.log.exception("uuidcode={} - Could not stop Job. It may still run".format(uuidcode))
            if status != 'waitforhostname': # no thread was started, so the check is finished
                orchestrator_communication.set_skip(app.log,
                                                    uuidcode,
                                                    app.urls.get('orchestrator', {}).get('url_skip'),
                                                    request.headers.get('servername'),
                                                    'False')
        except:
            app.log.exception("Jobs.get failed. Bugfix required")
            

    def post(self):
        try:
            # Track actions through different webservices.
            uuidcode = request.headers.get('uuidcode', '<no uuidcode>')
            app.log.info("uuidcode={} - Spawn Server".format(uuidcode))
            app.log.trace("uuidcode={} - Headers: {}".format(uuidcode, request.headers))
            app.log.trace("uuidcode={} - Json: {}".format(uuidcode, request.json))
    
            # Check for J4J intern token
            validate_auth(app.log,
                          uuidcode,
                          request.headers.get('Intern-Authorization'))
    
            servername = request.headers.get('servername')
            # Create header for unicore job
            try:
                unicore_header, accesstoken, expire = unicore_utils.create_header(app.log,  # @UnusedVariable
                                                                                  uuidcode,
                                                                                  request.headers,
                                                                                  app.urls.get('hub', {}).get('url_proxy_route'),
                                                                                  app.urls.get('hub', {}).get('url_token'),
                                                                                  request.headers.get('escapedusername'),
                                                                                  servername)
            except (SpawnException, Exception) as e:
                if type(e).__name__ == "SpawnException":
                    err_msg = str(e)
                else:
                    err_msg = "Unknown Error. An administrator is informed. Please try again in a few minutes"
                app.log.exception("uuidcode={} - Could not create header for UNICORE/X Job. {} {}".format(uuidcode, remove_secret(request.json), app.urls.get('tunnel', {}).get('url_remote')))
                app.log.trace("uuidcode={} - Call stop_job".format(uuidcode))
                try:
                    stop_job(app.log,
                             uuidcode,
                             servername,
                             request.json.get('system'),
                             request.headers,
                             app.urls,
                             True,
                             err_msg,
                             False)
                except:
                    app.log.exception("uuidcode={} - Could not stop Job. It may still run".format(uuidcode))
                # Return positive status: Administrator is informed and there is nothing we can do here otherwise.
                return "", 200
    
            # Create input files for the job. A working J4J_tunnel webservice is required
            try:
                unicore_input = unicore_utils.create_inputs(app.log,
                                                            uuidcode,
                                                            request.json,
                                                            request.headers.get('project'),
                                                            app.urls.get('tunnel', {}).get('url_remote'),
                                                            request.headers.get('account'))
            except (SpawnException, Exception) as e:
                if type(e).__name__ == "SpawnException":
                    err_msg = str(e)
                else:
                    err_msg = "Unknown Error. An administrator is informed. Please try again in a few minutes."
                app.log.exception("uuidcode={} - Could not create input files for UNICORE/X Job. {} {}".format(uuidcode, remove_secret(request.json), app.urls.get('tunnel', {}).get('url_remote')))
                app.log.trace("uuidcode={} - Call stop_job".format(uuidcode))
                try:
                    stop_job(app.log,
                             uuidcode,
                             servername,
                             request.json.get('system'),
                             request.headers,
                             app.urls,
                             True,
                             err_msg,
                             False)
                except:
                    app.log.exception("uuidcode={} - Could not stop Job. It may still run".format(uuidcode))
                return "", 534
    
            # Create Job description
            unicore_file = utils_file_loads.get_unicorex()
            if unicore_file.get(request.json.get('system').upper(), {}).get("UNICORE8", False):
                unicore_json = unicore_utils.create_unicore8_job(app.log,
                                                                 uuidcode,
                                                                 request.json,
                                                                 request.headers.get('Project'),
                                                                 unicore_input,
                                                                 request.headers.get('escapedusername'))
            else:
                unicore_json = unicore_utils.create_job(app.log,
                                                        uuidcode,
                                                        request.json,
                                                        request.headers.get('Project'),
                                                        unicore_input)
    
            # Get URL and certificate to communicate with UNICORE/X
            app.log.trace("uuidcode={} - FileLoad: UNICORE/X url".format(uuidcode))
            unicorex = utils_file_loads.get_unicorex()
            url = unicorex.get(request.json.get('system', ''), {}).get('link', '<no_url_found_for_{}>'.format(request.json.get('system')))
            app.log.trace("uuidcode={} - FileLoad: UNICORE/X url Result: {}".format(uuidcode, url))
            cert = unicorex.get(request.json.get('system', ''), {}).get('certificate', False)
            app.log.trace("uuidcode={} - FileLoad: UNICORE/X certificate path Result: {}".format(uuidcode, cert))
    
            # Submit Job. It will not be started, because of unicore_json['haveClientStageIn']='true'
            kernelurl = ""
            try:
                hub_communication.status(app.log,
                                         uuidcode,
                                         app.urls.get('hub', {}).get('url_proxy_route'),
                                         app.urls.get('hub', {}).get('url_status'),
                                         request.headers.get('jhubtoken'),
                                         'submitunicorejob',
                                         request.headers.get('escapedusername'),
                                         servername)
                method = "POST"
                method_args = {"url": url + "/jobs",
                               "headers": unicore_header,
                               "data": json.dumps(unicore_json),
                               "certificate": cert}
                app.log.info("uuidcode={} - Submit UNICORE/X Job to {}".format(uuidcode, url+"/jobs"))
                text, status_code, response_header = unicore_communication.request(app.log,
                                                                                   uuidcode,
                                                                                   method,
                                                                                   method_args)
                if status_code != 201:
                    app.log.warning("uuidcode={} - Could not submit Job. Response from UNICORE/X: {} {} {}.".format(uuidcode, text, status_code, remove_secret(response_header)))
                    if status_code == 500:
                        app.log.error("uuidcode={} - UNICORE RESTART REQUIRED!! {}".format(uuidcode, request.json.get('system', '<system_unknown>')))
                    elif status_code == 403 or status_code == 432:
                        raise SpawnException("Invalid token. Please logout and login again.")
                    else:
                        app.log.error("uuidcode={} - Unexpected status_code. Add case for this status_code.".format(uuidcode))
                    raise SpawnException("A backend service has to be restarted. An administrator is informed. Please try again in a few minutes.")
                else:
                    unicore_header['X-UNICORE-SecuritySession'] = response_header['X-UNICORE-SecuritySession']
                    kernelurl = response_header['Location']
            except (SpawnException, Exception) as e:
                if type(e).__name__ == "SpawnException":
                    err_msg = str(e)
                else:
                    err_msg = "Unknown Error. An administrator is informed. Please try again in a few minutes"
                    app.log.exception("uuidcode={} - User message: {} - Could not submit Job. {} {}".format(uuidcode, err_msg, method, remove_secret(method_args)))
                app.log.trace("uuidcode={} - Call stop_job".format(uuidcode))
                try:
                    stop_job(app.log,
                             uuidcode,
                             servername,
                             request.json.get('system'),
                             request.headers,
                             app.urls,
                             True,
                             err_msg,
                             False)
                except:
                    app.log.exception("uuidcode={} - Could not stop Job. It may still run".format(uuidcode))
                return "", 539
    
            # get properties of job
            for i in range(5):  # @UnusedVariable        
                properties_json = {}
                try:
                    method = "GET"
                    method_args = {"url": kernelurl,
                                   "headers": unicore_header,
                                   "certificate": cert}
                    app.log.info("uuidcode={} - Get Properties of UNICORE/X Job {}".format(uuidcode, kernelurl))
                    text, status_code, response_header = unicore_communication.request(app.log,
                                                                                       uuidcode,
                                                                                       method,
                                                                                       method_args)
                    if status_code != 200:
                        if status_code == 500:
                            app.log.error("uuidcode={} - UNICORE RESTART REQUIRED!! {}".format(uuidcode, request.json.get('system', '<system_unknown>')))
                            raise SpawnException("A backend service has to be restarted. An administrator is informed. Please try again in a few minutes.")
                        else:
                            app.log.error("uuidcode={} - Unexpected status_code. Add case for this status_code.".format(uuidcode))
                        if i < 4:
                            app.log.debug("uuidcode={} - Could not get properties of Job. Try again in 2 seconds".format(uuidcode))
                            sleep(2)
                        else:
                            app.log.warning("uuidcode={} - Could not get properties of Job. Response from UNICORE/X: {} {} {}.".format(uuidcode, text, status_code, remove_secret(response_header)))
                            raise Exception("{} - Could not get properties of Job. Throw exception because of wrong status_code: {}".format(uuidcode, status_code))
                    else:
                        unicore_header['X-UNICORE-SecuritySession'] = response_header['X-UNICORE-SecuritySession']
                        properties_json = json.loads(text)
                        if properties_json.get('status') == 'UNDEFINED' and i < 4:
                            app.log.debug("uuidcode={} - Received status UNDEFINED. Try again in 2 seconds".format(uuidcode))
                            sleep(2)
                        else:
                            break
                except (SpawnException, Exception) as e:
                    if type(e).__name__ == "SpawnException":
                        err_msg = str(e)
                    else:
                        err_msg = "Unknown Error. An administrator is informed. Please try again in a few minutes"
                        app.log.exception("uuidcode={} - Could not get properties of Job. {} {}".format(uuidcode, method, remove_secret(method_args)))
                    app.log.trace("uuidcode={} - Call stop_job".format(uuidcode))
                    try:
                        stop_job(app.log,
                                 uuidcode,
                                 servername,
                                 request.json.get('system'),
                                 request.headers,
                                 app.urls,
                                 True,
                                 err_msg)
                    except:
                        app.log.exception("uuidcode={} - Could not stop Job. It may still run".format(uuidcode))
                    return "", 539
    
    
            # get file directory
            # this will be used in get. Ask it here once and send it to get() afterwards
            filedirectory = ""
            try:
                method = "GET"
                method_args = {"url": properties_json['_links']['workingDirectory']['href'],
                               "headers": unicore_header,
                               "certificate": cert}
                app.log.info("uuidcode={} - Get path of file directory of UNICORE/X Job".format(uuidcode))
                text, status_code, response_header = unicore_communication.request(app.log,
                                                                                   uuidcode,
                                                                                   method,
                                                                                   method_args)
                if status_code != 200:
                    app.log.error("uuidcode={} - Unknown status_code. Please add case for this status_code".format(uuidcode))
                    app.log.warning("uuidcode={} - Could not get filedirectory. UNICORE/X Response: {} {} {}".format(uuidcode, text, status_code, remove_secret(response_header)))
                    raise Exception("{} - Could not get filedirectory. Throw exception because of wrong status_code: {}".format(uuidcode, status_code))
                else:
                    unicore_header['X-UNICORE-SecuritySession'] = response_header['X-UNICORE-SecuritySession']
                    filedirectory = json.loads(text)['_links']['files']['href']
            except (SpawnException, Exception) as e:
                if type(e).__name__ == "SpawnException":
                    err_msg = str(e)
                else:
                    err_msg = "Unknown Error. An administrator is informed. Please try again in a few minutes"
                app.log.exception("uuidcode={} - Could not get filedirectory. {} {}".format(uuidcode, method, remove_secret(method_args)))
                app.log.trace("uuidcode={} - Call stop_job".format(uuidcode))
                try:
                    stop_job(app.log,
                             uuidcode,
                             servername,
                             request.json.get('system'),
                             request.headers,
                             app.urls,
                             True,
                             err_msg)
                except:
                    app.log.exception("uuidcode={} - Could not stop Job. It may still run".format(uuidcode))
                return "", 539
    
            return "", 201, {'kernelurl': kernelurl,
                             'filedir': filedirectory,
                             'X-UNICORE-SecuritySession': unicore_header.get('X-UNICORE-SecuritySession')}
        except:
            app.log.exception("Jobs.post failed. Bugfix required")

    def delete(self):
        try:
            # Track actions through different webservices.
            uuidcode = request.headers.get('uuidcode', '<no uuidcode>')
            app.log.info("uuidcode={} - Delete Server".format(uuidcode))
            app.log.trace("uuidcode={} - Headers: {}".format(uuidcode, request.headers))
    
            # Check for the J4J intern token
            validate_auth(app.log,
                          uuidcode,
                          request.headers.get('Intern-Authorization', None))
    
            accesstoken, expire, security_session = stop_job(app.log,
                                                             uuidcode,
                                                             request.headers.get('servername'),
                                                             request.headers.get('system'),
                                                             request.headers,
                                                             app.urls,
                                                             False)
            app.log.trace("uuidcode={} - Return: {};{};{}".format(uuidcode, accesstoken, expire, security_session))
    
            return "", 200, {'accesstoken': accesstoken,
                             'expire': str(expire),
                             'X-UNICORE-SecuritySession': security_session}
        except:
            app.log.exception("Jobs.delete failed. Bugfix required")
