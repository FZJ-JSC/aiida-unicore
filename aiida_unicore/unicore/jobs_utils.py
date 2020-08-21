from app import unicore_utils, utils_file_loads, tunnel_communication, hub_communication, orchestrator_communication

def stop_job(app_logger, uuidcode, servername, system, request_headers, app_urls, send_cancel=True, errormsg="", stop_unicore_job=True):
    app_logger.trace("uuidcode={} - Create UNICORE Header".format(uuidcode))
    if ':' not in servername:
        servername = "{}:{}".format(request_headers.get('escapedusername'), servername)
        
    if send_cancel:
        app_logger.debug("uuidcode={} - Send cancel to JupyterHub".format(uuidcode))
        hub_communication.cancel(app_logger,
                                 uuidcode,
                                 app_urls.get('hub', {}).get('url_proxy_route'),
                                 app_urls.get('hub', {}).get('url_cancel'),
                                 request_headers.get('jhubtoken'),
                                 errormsg,
                                 request_headers.get('escapedusername'),
                                 servername)
    unicore_header = {}
    accesstoken = ""
    expire = ""
    if stop_unicore_job:
        unicore_header, accesstoken, expire = unicore_utils.create_header(app_logger,
                                                                          uuidcode,
                                                                          request_headers,
                                                                          app_urls.get('hub', {}).get('url_proxy_route'),
                                                                          app_urls.get('hub', {}).get('url_token'),
                                                                          request_headers.get('escapedusername'),
                                                                          servername)
    
    
        # Get certificate path to communicate with UNICORE/X Server
        app_logger.trace("uuidcode={} - FileLoad: UNICORE/X certificate path".format(uuidcode))
        unicorex = utils_file_loads.get_unicorex()
        cert = unicorex.get(system, {}).get('certificate', False)
        app_logger.trace("uuidcode={} - FileLoad: UNICORE/X certificate path Result: {}".format(uuidcode, cert))
    
        # Get logs from the UNICORE workspace. Necessary for support
        app_logger.debug("uuidcode={} - Copy_log".format(uuidcode))
        try:
            unicore_utils.copy_log(app_logger,
                                   uuidcode,
                                   unicore_header,
                                   request_headers.get('filedir'),
                                   request_headers.get('kernelurl'),
                                   cert)
        except:
            app_logger.exception("uuidcode={} - Could not copy log.".format(uuidcode))
    
        # Abort the Job via UNICORE
        app_logger.debug("uuidcode={} - Abort Job".format(uuidcode))
        unicore_utils.abort_job(app_logger,
                                uuidcode,
                                request_headers.get('kernelurl'),
                                unicore_header,
                                cert)
        if unicorex.get(system, {}).get('destroyjobs', 'false').lower() == 'true':
            # Destroy the Job via UNICORE
            app_logger.debug("uuidcode={} - Destroy Job".format(uuidcode))
            unicore_utils.destroy_job(app_logger,
                                      uuidcode,
                                      request_headers.get('kernelurl'),
                                      unicore_header,
                                      cert)
        else:
            # if it's a cron job we want to delete it
            cron_info = utils_file_loads.get_cron_info()
            user, servernameshort = request_headers.get('servername', ':').split(':')  # @UnusedVariable
            if cron_info.get('systems', {}).get(request_headers.get('system').upper(), {}).get('servername', '<undefined>') == servernameshort:
                if cron_info.get('systems', {}).get(request_headers.get('system').upper(), {}).get('account', '<undefined>') == request_headers.get('account'):
                    if cron_info.get('systems', {}).get(request_headers.get('system').upper(), {}).get('project', '<undefined>') == request_headers.get('project'):
                        unicore_utils.destroy_job(app_logger,
                                                  uuidcode,
                                                  request_headers.get('kernelurl'),
                                                  unicore_header,
                                                  cert)
    
    # Kill the tunnel
    tunnel_info = { "servername": servername }
    try:
        app_logger.debug("uuidcode={} - Close ssh tunnel".format(uuidcode))
        tunnel_communication.close(app_logger,
                                   uuidcode,
                                   app_urls.get('tunnel', {}).get('url_tunnel'),
                                   tunnel_info)
    except:
        app_logger.exception("uuidcode={} - Could not stop tunnel. tunnel_info: {} {}".format(uuidcode, tunnel_info, app_urls.get('tunnel', {}).get('url_tunnel')))

    # Remove Database entry for J4J_Orchestrator
    app_logger.debug("uuidcode={} - Call J4J_Orchestrator to remove entry {} from database".format(uuidcode, servername))
    orchestrator_communication.delete_database_entry(app_logger,
                                                     uuidcode,
                                                     app_urls.get('orchestrator', {}).get('url_database'),
                                                     servername)

    return accesstoken, expire, unicore_header.get('X-UNICORE-SecuritySession')
