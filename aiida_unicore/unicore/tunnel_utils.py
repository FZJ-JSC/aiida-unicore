'''
Created on May 14, 2019

@author: Tim Kreuzer
@mail: t.kreuzer@fz-juelich.de
'''

from app import unicore_communication, hub_communication, unicore_utils,\
    utils_file_loads, tunnel_communication
from app.utils import remove_secret

def create(app_logger, uuidcode, app_hub_url_proxy_route, app_tunnel_url, app_hub_url_cancel, kernelurl, filedir, unicore_header, servername, system, port, cert, jhubtoken, username, servername_short):
    app_logger.trace("uuidcode={} - Try to create a tunnel".format(uuidcode))
    accept = unicore_header.get('Accept', False)
    unicore_header['Accept'] = 'application/octet-stream'
    hostname = ""
    try:
        method = "GET"
        method_args = {"url": filedir+'/.host',
                       "headers": unicore_header,
                       "certificate": cert,
                       "return_content": True}
        content, status_code, response_header = unicore_communication.request(app_logger,
                                                                              uuidcode,
                                                                              method,
                                                                              method_args)
        if status_code != 200:
            app_logger.warning("uuidcode={} - Could not get hostname. UNICORE/X Response: {} {} {}".format(uuidcode, content, status_code, remove_secret(response_header)))
            raise Exception("{} - Could not get hostname. Throw exception because of wrong status_code: {}".format(uuidcode, status_code))
        else:
            unicore_header['X-UNICORE-SecuritySession'] = response_header['X-UNICORE-SecuritySession']
            hostname = content.strip()
    except:
        app_logger.exception("uuidcode={} - Could not get hostname. {} {}".format(uuidcode, method, remove_secret(method_args)))
        app_logger.warning("uuidcode={} - Send cancel to JupyterHub.".format(uuidcode))
        hub_communication.cancel(app_logger,
                                 uuidcode,
                                 app_hub_url_proxy_route,
                                 app_hub_url_cancel,
                                 jhubtoken,
                                 "A mandatory backend service had a problem. An administrator is informed.",
                                 username,
                                 servername_short)
        unicore_utils.abort_job(app_logger,
                                uuidcode,
                                kernelurl,
                                unicore_header,
                                cert)
        unicore_utils.destroy_job(app_logger,
                                  uuidcode,
                                  kernelurl,
                                  unicore_header,
                                  cert)
        raise Exception("{} - Could not get hostname".format(uuidcode))
        
    tunnel_header = { 
        'Intern-Authorization': utils_file_loads.get_j4j_tunnel_token(),
        'uuidcode': uuidcode
        }
    if system == 'JUWELS' and hostname[:3] == 'jwc':
        hostname = hostname.split('.')[0]
    if system == 'JURON' and hostname[:6] == 'juronc':
        hostname = hostname.split('.')[0]
    tunnel_data = {
        'account': servername, # for internal tunnel database
        'system': system,
        'hostname': hostname,
        'port': port
        }
    
    tunnel_communication.j4j_start_tunnel(app_logger,
                                          uuidcode,
                                          app_tunnel_url,
                                          tunnel_header,
                                          tunnel_data)
    try:
        method = "PUT"
        method_args = {"url": filedir+'/.tunnel',
                       "headers": unicore_header,
                       "data": '{}'.format(port),
                       "certificate": cert}
        text, status_code, response_header = unicore_communication.request(app_logger,
                                                                           uuidcode,
                                                                           method,
                                                                           method_args)
        if status_code != 204:
            app_logger.warning("uuidcode={} - Could not create .tunnel file. UNICORE/X Response: {} {} {}".format(uuidcode, text, status_code, remove_secret(response_header)))
            raise Exception("{} - Could not create .tunnel file. Throw Exception because of wrong status_code: {}".format(uuidcode, status_code))
        else:
            unicore_header['X-UNICORE-SecuritySession'] = response_header['X-UNICORE-SecuritySession']
    except:
        app_logger.exception("uuidcode={} - Could not create .tunnel file. {} {}".format(uuidcode, method, remove_secret(method_args)))
        app_logger.warning("uuidcode={} - Send cancel to JupyterHub.".format(uuidcode))
        hub_communication.cancel(app_logger,
                                 uuidcode,
                                 app_hub_url_proxy_route,
                                 app_hub_url_cancel,
                                 jhubtoken,
                                 "A mandatory backend service had a problem. An administrator is informed.",
                                 username,
                                 servername_short)
        unicore_utils.abort_job(app_logger,
                                uuidcode,
                                kernelurl,
                                unicore_header,
                                cert)
        unicore_utils.destroy_job(app_logger,
                                  uuidcode,
                                  kernelurl,
                                  unicore_header,
                                  cert)
        raise Exception("{} - Could not create .tunnel file.".format(uuidcode))
 
    if accept:
        unicore_header['Accept'] = accept
    else:
        del unicore_header['Accept']
