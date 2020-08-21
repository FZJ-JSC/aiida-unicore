'''
Created on May 14, 2019

@author: Tim Kreuzer
@mail: t.kreuzer@fz-juelich.de
'''


import datetime
import os
import uuid
import json


from app.utils_file_loads import get_unicorex, get_jlab_conf, get_inputs,\
    get_hub_port, get_fastnet_changes, get_base_url
from app.tunnel_communication import get_remote_node
from app.unity_communication import renew_token
from app import unicore_communication, utils_file_loads
from app.utils import remove_secret
import random

def abort_job(app_logger, uuidcode, kernelurl, unicore_header, cert):
    app_logger.debug("uuidcode={} - Try to abort job with kernelurl: {}".format(uuidcode, kernelurl))
    try:
        # If the API of UNICORE will change, the additional GET call might be necessary.
        # Since the action:abort url is (right now) always: kernelurl + /actions/abort we will just use this
        """
        method = "GET"
        method_args = { "url": kernelurl, "headers": unicore_header, "certificate", cert }
        text, status_code, response_header = unicore_communication.request(app_logger,
                                                                           uuidcode,
                                                                           method,
                                                                           method_args)
        if status_code != 200
            ...
        else:
            url = json.loads(text)['_links']['action:abort']['href']
        """
        method = "POST"
        method_args = {"url": kernelurl + '/actions/abort',
                       "headers": unicore_header,
                       "data": "{}",
                       "certificate": cert}

        app_logger.info("uuidcode={} - Abort UNICORE/X Job {}".format(uuidcode, kernelurl))
        text, status_code, response_header = unicore_communication.request(app_logger,
                                                                           uuidcode,
                                                                           method,
                                                                           method_args)

        if status_code < 200 or status_code > 299:
            app_logger.warning("uuidcode={} - Could not abort Job. Response from UNICORE/X: {} {} {}".format(uuidcode, text, status_code, remove_secret(response_header)))
        else:
            unicore_header['X-UNICORE-SecuritySession'] = response_header['X-UNICORE-SecuritySession']
    except:
        app_logger.exception("uuidcode={} - Could not abort Job.".format(uuidcode))


def destroy_job(app_logger, uuidcode, kernelurl, unicore_header, cert):
    app_logger.debug("uuidcode={} - Try to destroy Job with kernelurl: {}".format(uuidcode, kernelurl))
    method = "DELETE"
    method_args = {"url": kernelurl,
                   "headers": unicore_header,
                   "certificate": cert}
    try:
        app_logger.info("uuidcode={} - Destroy UNICORE/X Job".format(uuidcode))
        text, status_code, response_header = unicore_communication.request(app_logger,
                                                                           uuidcode,
                                                                           method,
                                                                           method_args)
        if status_code > 399:
            app_logger.warning("uuidcode={} - Could not destroy job. WorkDirectory may still exist. UNICORE/X Response: {} {} {}".format(uuidcode, text, status_code, remove_secret(response_header)))
    except:
        app_logger.exception("uuidcode={} - Could not destroy job.".format(uuidcode))

# Create Header Dict
def create_header(app_logger, uuidcode, request_headers, app_hub_url_proxy_route, app_hub_url_token, username, servername):
    app_logger.debug("uuidcode={} - Create UNICORE/X Header".format(uuidcode))
    accesstoken, expire = renew_token(app_logger,
                                      uuidcode,
                                      request_headers.get("tokenurl"),
                                      request_headers.get("authorizeurl"),
                                      request_headers.get("refreshtoken"),
                                      request_headers.get('accesstoken'),
                                      request_headers.get('expire'),
                                      request_headers.get('jhubtoken'),
                                      app_hub_url_proxy_route,
                                      app_hub_url_token,
                                      username,
                                      servername)
    unicore_header = {"Accept": "application/json",
                      "User-Agent": request_headers.get("User-Agent", "Jupyter@JSC"),
                      "X-UNICORE-User-Preferences": "uid:{},group:{}".format(request_headers.get('account'), request_headers.get('project')),
                      "Content-Type": "application/json",
                      "Authorization": "Bearer {}".format(accesstoken)}
    if request_headers.get('project') == "default":
        unicore_header["X-UNICORE-User-Preferences"] = "uid:{}".format(request_headers.get('account'))

    if request_headers.get('X-UNICORE-SecuritySession', None):
        unicore_header['X-UNICORE-SecuritySession'] = request_headers.get('X-UNICORE-SecuritySession')
        # "session": orig_header.get("session")
    app_logger.trace("uuidcode={} - UNICORE/X Header: {}".format(uuidcode, unicore_header))
    return unicore_header, accesstoken, expire

#
def create_unicore8_job(app_logger, uuidcode, request_json, project, unicore_input, escapedusername):
    app_logger.debug("uuidcode={} - Create UNICORE/X-8 Job.".format(uuidcode))
    env_list = []
    for key, value in request_json.get('Environment', {}).items():
        env_list.append('{}={}'.format(key, value))
    job = {'ApplicationName': 'Bash shell',
           'Environment': env_list,
           'Imports': []}
    unicorex_info = utils_file_loads.get_unicorex()
    if unicorex_info.get(request_json.get('system').upper(), {}).get('set_project', False):
        if unicorex_info.get(request_json.get('system').upper(), {}).get('projects', {}).get('ALL', '') != '':
            job['Project'] = unicorex_info.get(request_json.get('system').upper(), {}).get('projects', {}).get('ALL', '')
        elif unicorex_info.get(request_json.get('system').upper(), {}).get('projects', {}).get(project.lower(), '') != '':
            job['Project'] = unicorex_info.get(request_json.get('system').upper(), {}).get('projects', {}).get(project.lower(), '')
        elif unicorex_info.get(request_json.get('system').upper(), {}).get('projects_truncate', False):
            job['Project'] = project[1:]
        else:
            job['Project'] = project
    for inp in unicore_input:
        job['Imports'].append(
            {
                "From": "inline://dummy",
                "To"  : inp.get('To'),
                "Data": inp.get('Data')
            }
        )
    urls = utils_file_loads.get_urls()
    ux_notify = urls.get('hub', {}).get('url_ux', '<no_url_for_unicore_notification_configured>')
    ux_notify_server_name = "{}_{}_{}".format(len(uuidcode), uuidcode, request_json.get('Environment', {}).get('JUPYTERHUB_SERVER_NAME'))
    ux_notify = ux_notify.replace('<user>', escapedusername).replace('<server>', ux_notify_server_name)
    job['Notification'] = ux_notify
    if request_json.get('partition') in ['LoginNode', 'LoginNodeVis']:
        job['Executable'] = '/bin/bash'
        job['Arguments'] = ['.start.sh']
        job['Job type'] = 'interactive'
        if request_json.get('partition') in ['LoginNodeVis']:
            nodes = unicorex_info.get(request_json.get('system').upper(), {}).get('LoginNodeVis', [])
            if len(nodes) > 0:
                # get system list ... choose one ... use it
                node = random.choice(nodes)
                app_logger.trace("uuidcode={} - Use random VIS Node: {}".format(uuidcode, node))
                job['Login node'] = node
        elif 'LoginNodeVis' in unicorex_info.get(request_json.get('system').upper(), {}).keys():
            # this system supports vis nodes. So we have to set the non vis nodes explicitly
            nodes = unicorex_info.get(request_json.get('system').upper(), {}).get('LoginNode', [])
            if len(nodes) > 0:
                # get system list ... choose one ... use it
                node = random.choice(nodes)
                app_logger.trace("uuidcode={} - Use random non-VIS Node: {}".format(uuidcode, node))
                job['Login node'] = node
        app_logger.trace("uuidcode={} - UNICORE/X Job: {}".format(uuidcode, job))
        return job
    if unicorex_info.get(request_json.get('system').upper(), {}).get('queues', False):
        job['Resources'] = { 'Queue': request_json.get('partition')}
    else:
        job['Resources'] = {}
    if request_json.get('reservation', None):
        if len(request_json.get('reservation', '')) > 0 and request_json.get('reservation', 'none').lower() != 'none':
            job['Resources']['Reservation'] = request_json.get('reservation')
    for key, value in request_json.get('Resources').items():
        job['Resources'][key] = value
    job['Executable'] = '/bin/bash'
    job['Arguments'] = ['.start.sh']
    app_logger.debug("uuidcode={} - UNICORE/X-8 Job: {}".format(uuidcode, job))
    return job

def create_unicore8_job_dashboard(app_logger, uuidcode, request_json, project, unicore_input, escapedusername):
    app_logger.debug("uuidcode={} - Create UNICORE/X-8 Job.".format(uuidcode))
    env_list = []
    for key, value in request_json.get('Environment', {}).items():
        env_list.append('{}={}'.format(key, value))
    job = {'ApplicationName': 'Bash shell',
           'Environment': env_list,
           'Imports': []}
    unicorex_info = utils_file_loads.get_unicorex()
    if unicorex_info.get(request_json.get('system').upper(), {}).get('set_project', False):
        if unicorex_info.get(request_json.get('system').upper(), {}).get('projects', {}).get('ALL', '') != '':
            job['Project'] = unicorex_info.get(request_json.get('system').upper(), {}).get('projects', {}).get('ALL', '')
        elif unicorex_info.get(request_json.get('system').upper(), {}).get('projects', {}).get(project.lower(), '') != '':
            job['Project'] = unicorex_info.get(request_json.get('system').upper(), {}).get('projects', {}).get(project.lower(), '')
        elif unicorex_info.get(request_json.get('system').upper(), {}).get('projects_truncate', False):
            job['Project'] = project[1:]
        else:
            job['Project'] = project
    for inp in unicore_input:
        job['Imports'].append(
            {
                "From": "inline://dummy",
                "To"  : inp.get('To'),
                "Data": inp.get('Data')
            }
        )
    urls = utils_file_loads.get_urls()
    ux_notify = urls.get('hub', {}).get('url_ux', '<no_url_for_unicore_notification_configured>')
    ux_notify_server_name = "{}_{}_{}".format(len(uuidcode), uuidcode, request_json.get('Environment', {}).get('JUPYTERHUB_SERVER_NAME'))
    ux_notify = ux_notify.replace('<user>', escapedusername).replace('<server>', ux_notify_server_name)
    job['Notification'] = ux_notify
    if request_json.get('partition') in ['LoginNode', 'LoginNodeVis']:
        job['Executable'] = '/bin/bash'
        job['Arguments'] = ['.start.sh']
        job['Job type'] = 'interactive'
        if request_json.get('partition') in ['LoginNodeVis']:
            nodes = unicorex_info.get(request_json.get('system').upper(), {}).get('LoginNodeVis', [])
            if len(nodes) > 0:
                # get system list ... choose one ... use it
                node = random.choice(nodes)
                app_logger.trace("uuidcode={} - Use random VIS Node: {}".format(uuidcode, node))
                job['Login node'] = node
        elif 'LoginNodeVis' in unicorex_info.get(request_json.get('system').upper(), {}).keys():
            # this system supports vis nodes. So we have to set the non vis nodes explicitly
            nodes = unicorex_info.get(request_json.get('system').upper(), {}).get('LoginNode', [])
            if len(nodes) > 0:
                # get system list ... choose one ... use it
                node = random.choice(nodes)
                app_logger.trace("uuidcode={} - Use random non-VIS Node: {}".format(uuidcode, node))
                job['Login node'] = node
        app_logger.trace("uuidcode={} - UNICORE/X Job: {}".format(uuidcode, job))
        return job
    if unicorex_info.get(request_json.get('system').upper(), {}).get('queues', False):
        job['Resources'] = { 'Queue': request_json.get('partition')}
    else:
        job['Resources'] = {}
    if request_json.get('reservation', None):
        if len(request_json.get('reservation', '')) > 0 and request_json.get('reservation', 'none').lower() != 'none':
            job['Resources']['Reservation'] = request_json.get('reservation')
    for key, value in request_json.get('Resources').items():
        job['Resources'][key] = value
    job['Executable'] = '/bin/bash'
    job['Arguments'] = ['.start.sh']
    app_logger.debug("uuidcode={} - UNICORE/X-8 Job: {}".format(uuidcode, job))
    return job



# Create Job Dict
# deprecated
def create_job(app_logger, uuidcode, request_json, project, unicore_input):
    app_logger.debug("uuidcode={} - Create UNICORE/X-7 Job.".format(uuidcode))
    job = {'ApplicationName': 'Jupyter4JSC',
           'Environment': request_json.get('Environment', {}),
           'Imports': []}
    unicorex_info = utils_file_loads.get_unicorex()

    for inp in unicore_input:
        job['Imports'].append(
            {
                "From": "inline://dummy",
                "To"  : inp.get('To'),
                "Data": inp.get('Data'),
            }
        )

    if request_json.get('partition') == 'LoginNode':
        job['Environment']['UC_PREFER_INTERACTIVE_EXECUTION'] = 'true'
        job['Executable'] = 'bash .start.sh'
        app_logger.trace("uuidcode={} - UNICORE/X Job: {}".format(uuidcode, job))
        return job
    if unicorex_info.get(request_json.get('system').upper(), {}).get('queues', False):
        job['Resources'] = { 'Queue': request_json.get('partition')}
    else:
        job['Resources'] = {}
    if request_json.get('reservation', None):
        if len(request_json.get('reservation', '')) > 0 and request_json.get('reservation', 'none').lower() != 'none':
            job['Resources']['Reservation'] = request_json.get('reservation')
    for key, value in request_json.get('Resources').items():
        job['Resources'][key] = value
    job['Executable'] = '.start.sh'
    app_logger.debug("uuidcode={} - UNICORE/X-7 Job: {}".format(uuidcode, job))
    return job

# Create Inputs files
def create_inputs(app_logger, uuidcode, request_json, project, tunnel_url_remote, account):
    app_logger.debug("uuidcode={} - Create Inputs for UNICORE/X.".format(uuidcode))
    inp = []
    ux = get_unicorex()
    nodes = ux.get(request_json.get('system').upper(), {}).get('nodes', [])
    baseconf = get_jlab_conf()
    inps = get_inputs()
    node = get_remote_node(app_logger,
                           uuidcode,
                           tunnel_url_remote,
                           nodes)
    inp.append({ 'To': '.start.sh', 'Data': start_sh(app_logger,
                                                     uuidcode,
                                                     request_json.get('system'),
                                                     project,
                                                     request_json.get('Checkboxes'),
                                                     inps,
                                                     account) })

    inp.append({ 'To': '.config.py', 'Data': get_config(app_logger,
                                                        uuidcode,
                                                        baseconf,
                                                        request_json.get('port'),
                                                        node,
                                                        request_json.get('Environment', {}).get('JUPYTERHUB_USER'),
                                                        request_json.get('service'),
                                                        request_json.get('Environment', {}).get('JUPYTERHUB_SERVER_NAME')) })
    inp.append({ 'To': '.jupyter.token', 'Data': request_json.get('Environment').get('JUPYTERHUB_API_TOKEN') })
    try:
        del request_json['Environment']['JUPYTERHUB_API_TOKEN']
        del request_json['Environment']['JPY_API_TOKEN']
    except KeyError:
        pass
    app_logger.trace("uuidcode={} - Inputs for UNICORE/X: {}".format(uuidcode, inp))
    return inp


def get_config(app_logger, uuidcode, baseconf, port, hubapiurlnode, user, service, servername=''):
    app_logger.debug("uuidcode={} - Generate config".format(uuidcode))
    hubport = get_hub_port()
    ret = baseconf + '\nc.SingleUserNotebookApp.port = {}'.format(port)
    hubnode = get_fastnet_changes(hubapiurlnode)
    base_url = get_base_url()
    ret += '\nc.SingleUserNotebookApp.hub_api_url = "http://{}:{}{}hub/api"'.format(hubnode, hubport, base_url)
    ret += '\nc.SingleUserNotebookApp.hub_activity_url = "http://{}:{}{}hub/api/users/{}/activity"\n'.format(hubnode, hubport, base_url, user)
    if service == "JupyterLab":
        ret += '\nc.SingleUserNotebookApp.default_url = "/lab/workspaces/{}"\n'.format(servername)
    app_logger.trace("uuidcode={} - Config: {}".format(uuidcode, ret.replace("\n","/n")))
    return ret

# Create Inputs files
def create_inputs_dashboards(app_logger, uuidcode, request_json, project, tunnel_url_remote, account, dashboard_info, dashboard_name):
    app_logger.debug("uuidcode={} - Create Inputs for UNICORE/X.".format(uuidcode))
    inp = []
    ux = get_unicorex()
    nodes = ux.get(request_json.get('system').upper(), {}).get('nodes', [])
    try:
        with open(dashboard_info.get(request_json.get('system'), {}).get("config_file")) as f:
            baseconf = f.read().rstrip()
    except:
        baseconf = ""
    inps = get_inputs()
    node = get_remote_node(app_logger,
                           uuidcode,
                           tunnel_url_remote,
                           nodes)
    inp.append({ 'To': '.start.sh', 'Data': dashboard_start_sh(app_logger,
                                                               uuidcode,
                                                               request_json.get('system'),
                                                               project,
                                                               request_json.get('Checkboxes'),
                                                               inps,
                                                               account,
                                                               dashboard_info,
                                                               dashboard_name) })

    inp.append({ 'To': '.config.py', 'Data': get_config(app_logger,
                                                        uuidcode,
                                                        baseconf,
                                                        request_json.get('port'),
                                                        node,
                                                        request_json.get('Environment', {}).get('JUPYTERHUB_USER'),
                                                        request_json.get('service'),
                                                        request_json.get('Environment', {}).get('JUPYTERHUB_SERVER_NAME')) })
    inp.append({ 'To': '.jupyter.token', 'Data': request_json.get('Environment').get('JUPYTERHUB_API_TOKEN') })
    try:
        del request_json['Environment']['JUPYTERHUB_API_TOKEN']
        del request_json['Environment']['JPY_API_TOKEN']
    except KeyError:
        pass
    app_logger.trace("uuidcode={} - Inputs for UNICORE/X: {}".format(uuidcode, inp))
    return inp


def copy_log(app_logger, uuidcode, unicore_header, filedir, kernelurl, cert):
    app_logger.debug("uuidcode={} - Copy Log from {}".format(uuidcode, kernelurl))
    # in this directory we will write the complete log from the started server.
    directory = '/etc/j4j/j4j_mount/jobs/{}_{}'.format(kernelurl.split('/')[-1], datetime.datetime.today().strftime('%Y_%m_%d-%H_%M_%S'))
    for i in range(10):
        if os.path.exists(directory):
            add_uuid = uuid.uuid4().hex
            directory = directory + '_' + add_uuid
        if not os.path.exists(directory):
            os.makedirs(directory)
            break
        if i == 9:
            app_logger.warning("uuidcode={} - Could not find a directory to save files".format(uuidcode))
            return
    app_logger.debug("uuidcode={} - Copy Log to {}".format(uuidcode, directory))
    # Get children list
    try:
        app_logger.info("uuidcode={} - Get list of files of UNICORE/X Job".format(uuidcode))
        text, status_code, response_header = unicore_communication.request(app_logger,
                                                                           uuidcode,
                                                                           "GET",
                                                                           {"url": filedir, "headers": unicore_header, "certificate": cert})
        if status_code != 200:
            app_logger.warning("uuidcode={} - Could not save files from {}. Response from UNICORE: {} {} {}".format(uuidcode, kernelurl, text, status_code, remove_secret(response_header)))
            return
        # in UNICORE 8 the answer is a bit different
        children_json = json.loads(text)
        if 'children' in children_json.keys():
            children = json.loads(text).get('children', [])
        elif 'content' in children_json.keys():
            children = list(json.loads(text).get('content', {}).keys())
        else:
            app_logger.warning("uuidcode={} - Could not find any childrens in {}".format(uuidcode, text))
            children = []
        unicore_header['X-UNICORE-SecuritySession'] = response_header['X-UNICORE-SecuritySession']
    except:
        app_logger.exception("uuidcode={} - Could not save files from {}".format(uuidcode, kernelurl))
        return

    # For the file input we need another Accept in the header, save the old one
    hostname = ""
    accept = unicore_header.get('Accept', False)
    unicore_header['Accept'] = 'application/octet-stream'
    app_logger.info("uuidcode={} - Save files in directory {}".format(uuidcode, directory))
    for child in children:
        try:
            content, status_code, response_header = unicore_communication.request(app_logger,
                                                                                  uuidcode,
                                                                                  "GET",
                                                                                  {"url": filedir+'/'+child,
                                                                                   "headers": unicore_header,
                                                                                   "certificate": cert,
                                                                                   "return_content": True})
            if status_code != 200:
                app_logger.warning("uuidcode={} - Could not save file {} from {}. Try next. Response from UNICORE: {} {} {}".format(uuidcode, child, kernelurl, content, status_code, remove_secret(response_header)))
                continue
            with open(directory+'/'+child, 'w') as f:
                f.write(str(content.encode("utf-8")))
            if child == ".host" or child == "/.host":
                hostname = content.strip()
        except:
            app_logger.exception("uuidcode={} - Could not save file {} from {}".format(uuidcode, child, kernelurl))
            break
    if accept:
        unicore_header['Accept'] = accept
    else:
        del unicore_header['Accept']
    app_logger.debug("uuidcode={} - Log from {} to {} copied".format(uuidcode, kernelurl, directory))
    return hostname

def dashboard_start_sh(app_logger, uuidcode, system, project, checkboxes, inputs, account, dashboard_info, dashboard_name):
    app_logger.debug("uuidcode={} - Create start.sh file for dashboard".format(uuidcode))
    #dashboard_info = utils_file_loads.get_dashboards().get(dashboard_name, {})
    startjupyter = '#!/bin/bash\n_term() {\n  echo \"Caught SIGTERM signal!\"\n  kill -TERM \"$child\" 2>/dev/null\n}\ntrap _term SIGTERM\n'
    startjupyter += 'hostname>.host;\n'
    #hpc_type = dashboard_info.get(system, {}).get('hpctype', '<Please set hpc type in dashboards.json for {}:{}>'.format(dashboard_name, system))
    if 'precommands' in dashboard_info.get(system, {}).keys():
        precommand = dashboard_info.get(system, {}).get('precommands', '#precommands-{}'.format(dashboard_name))
    else:
        precommand = inputs.get(system.upper(), {}).get('start', {}).get('precommands', '#precommands')
    startjupyter += precommand + '\n'
    if 'modules' in dashboard_info.get(system, {}).keys():
        modules = dashboard_info.get(system, {}).get('modules', '#modules-{}'.format(dashboard_name))
    else:
        modules = inputs.get(system.upper(), {}).get('start', {}).get('defaultmodules', '#defaultmodules')
    startjupyter += modules +'\n'
    if 'postcommands' in dashboard_info.get(system, {}).keys():
        postcommands = dashboard_info.get(system, {}).get('postcommands', '#postcommands-{}'.format(dashboard_name))
    else:
        postcommands = inputs.get(system.upper(), {}).get('start', {}).get('postcommands', '#postcommands')
    startjupyter += postcommands +'\n'
    if 'downloadcommands' in dashboard_info.get(system, {}).keys():
        startjupyter += dashboard_info.get(system, {}).get('downloadcommands') + "\n"
    startjupyter += 'export JPY_API_TOKEN=`cat .jupyter.token`\n'
    startjupyter += 'export JUPYTERHUB_API_TOKEN=`cat .jupyter.token`\n'
    for cbname, cbinfos in checkboxes.items():
        script = "# {}\n".format(cbname)
        with open(cbinfos.get('scriptpath'), 'r') as f:            
            script += f.read()
        startjupyter += script+'\n'
    if 'jupyter_path' in dashboard_info.get(system, {}).keys():
        startjupyter += 'export JUPYTER_PATH={}:$JUPYTER_PATH\n'.format(dashboard_info.get(system, {}).get('jupyter_path', '/'))
    if 'executable' in dashboard_info.get(system, {}).keys():
        executable = dashboard_info.get(system, {}).get('executable', '#executable-{}'.format(dashboard_name))
    elif 'executable' in inputs.get(system.upper()).get('start').keys():
        executable = inputs.get(system.upper()).get('start').get('executable')
    else:
        executable = 'jupyter labhub $@ --config .config.py &\nchild=$!\nwait "$child"'
    startjupyter += executable + '\n'
    startjupyter += 'echo "end">.end\n'
    app_logger.trace("uuidcode={} - start.sh file: {}".format(uuidcode, startjupyter.replace("\n", "/n")))
    return startjupyter


def start_sh(app_logger, uuidcode, system, project, checkboxes, inputs, account):
    app_logger.debug("uuidcode={} - Create start.sh file".format(uuidcode))
    unicorex_info = utils_file_loads.get_unicorex()
    startjupyter = '#!/bin/bash\n_term() {\n  echo \"Caught SIGTERM signal!\"\n  kill -TERM \"$child\" 2>/dev/null\n}\ntrap _term SIGTERM\n'
    startjupyter += 'hostname>.host;\n'
    startjupyter += inputs.get(system.upper(), {}).get('start', {}).get('precommands', '#precommands')+'\n'
    project_link_list = unicorex_info.get(system.upper(), {}).get("projectLinks", [])
    if project in project_link_list:
        startjupyter += "if ! [ -e ${{HOME}}/PROJECT_{} ]; then\n".format(project)
        startjupyter += "  ln -s ${{PROJECT_{project}}} ${{HOME}}/PROJECT_{project}\n".format(project=project)
        startjupyter += "fi\n"
    if account in inputs.get(system.upper(), {}).get('start', {}).get('accountmodules', {}).keys():
        startjupyter += inputs.get(system.upper(), {}).get('start', {}).get('accountmodules', {}).get(account, '#usermodules: {}'.format(account))+'\n'
    else:
        startjupyter += inputs.get(system.upper(), {}).get('start', {}).get('defaultmodules', '#defaultmodules')+'\n'
    startjupyter += inputs.get(system.upper(), {}).get('start', {}).get('postcommands', '#postcommands')+'\n'
    startjupyter += 'export JPY_API_TOKEN=`cat .jupyter.token`\n'
    startjupyter += 'export JUPYTERHUB_API_TOKEN=`cat .jupyter.token`\n'
    for cbname, cbinfos in checkboxes.items():
        script = "# {}\n".format(cbname)
        with open(cbinfos.get('scriptpath'), 'r') as f:            
            script += f.read()
        startjupyter += script+'\n'
    if project in unicorex_info.get(system.upper(), {}).get("project_path", []):
        startjupyter += 'export JUPYTER_PATH=$PROJECT_{}/.local/share/jupyter:$JUPYTER_PATH\n'.format(project)
    if 'executable' in inputs.get(system.upper()).get('start').keys():
        startjupyter += inputs.get(system.upper()).get('start').get('executable')
    else:
        startjupyter += 'jupyter labhub $@ --config .config.py &'
        startjupyter += '\nchild=$!\nwait "$child"'
    startjupyter += '\necho "end">.end\n'
    app_logger.trace("uuidcode={} - start.sh file: {}".format(uuidcode, startjupyter.replace("\n", "/n")))
    return startjupyter

