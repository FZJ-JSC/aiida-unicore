'''
Created on May 14, 2019

@author: Tim Kreuzer
@mail: t.kreuzer@fz-juelich.de
'''

from contextlib import closing
import requests

# UNICORE/X Requests
def request(app_logger, uuidcode, method, method_args):
    app_logger.debug("uuidcode={} - UNICORE/X communication. {} {}".format(uuidcode, method_args.get('url', '<no url>'), method))
    app_logger.trace("uuidcode={} - UNICORE/X communication. Method_args: {}".format(uuidcode, method_args))
    if method == "GET":
        with closing(requests.get(method_args.get("url"),
                                  headers=method_args.get("headers", {}),
                                  verify=method_args.get("certificate", False),
                                  timeout=1800)) as r:
            if r.status_code != 432 and r.status_code != 500: # 432 -> SecuritySession expired. 500 -> Internal Server Error, maybe GPFS made bs?
                if 'return_content' in method_args:
                    app_logger.trace("uuidcode={} - UNICORE/X communication response Status code: {}".format(uuidcode, r.status_code))
                    app_logger.trace("uuidcode={} - UNICORE/X communication response Content: {}".format(uuidcode, r.content.decode("utf-8")))
                    app_logger.trace("uuidcode={} - UNICORE/X communication response Headers: {}".format(uuidcode, r.headers))
                    return r.content.decode("utf-8"), r.status_code, r.headers
                else:
                    app_logger.trace("uuidcode={} - UNICORE/X communication response Status code: {}".format(uuidcode, r.status_code))
                    app_logger.trace("uuidcode={} - UNICORE/X communication response Content: {}".format(uuidcode, r.text))
                    app_logger.trace("uuidcode={} - UNICORE/X communication response Headers: {}".format(uuidcode, r.headers))
                    return r.text, r.status_code, r.headers
        app_logger.debug("uuidcode={} - Session expired. Use accesstoken instead".format(uuidcode))
        try:
            del method_args['headers']['X-UNICORE-SecuritySession']
        except:
            pass
        with closing(requests.get(method_args.get("url"),
                                  headers=method_args.get("headers", {}),
                                  verify=method_args.get("certificate", False),
                                  timeout=1800)) as r2:
            if 'return_content' in method_args:
                app_logger.trace("uuidcode={} - UNICORE/X communication response Status code: {}".format(uuidcode, r2.status_code))
                app_logger.trace("uuidcode={} - UNICORE/X communication response Content: {}".format(uuidcode, r2.content.decode("utf-8")))
                app_logger.trace("uuidcode={} - UNICORE/X communication response Headers: {}".format(uuidcode, r2.headers))
                return r2.content.decode("utf-8"), r2.status_code, r2.headers
            else:
                app_logger.trace("uuidcode={} - UNICORE/X communication response Status code: {}".format(uuidcode, r2.status_code))
                app_logger.trace("uuidcode={} - UNICORE/X communication response Content: {}".format(uuidcode, r2.text))
                app_logger.trace("uuidcode={} - UNICORE/X communication response Headers: {}".format(uuidcode, r2.headers))
                return r2.text, r2.status_code, r2.headers


    elif method == "DELETE":
        with closing(requests.delete(method_args.get("url"),
                                     headers=method_args.get("headers", {}),
                                     data=method_args.get("data", "{}"),
                                     verify=method_args.get("certificate", False),
                                     timeout=1800)) as r:
            if r.status_code != 432 and r.status_code != 500: # 432 -> SecuritySession expired. 500 -> Internal Server Error, maybe GPFS made bs?
                if 'return_content' in method_args:
                    app_logger.trace("uuidcode={} - UNICORE/X communication response Status code: {}".format(uuidcode, r.status_code))
                    app_logger.trace("uuidcode={} - UNICORE/X communication response Content: {}".format(uuidcode, r.content.decode("utf-8")))
                    app_logger.trace("uuidcode={} - UNICORE/X communication response Headers: {}".format(uuidcode, r.headers))
                    return r.content.decode("utf-8"), r.status_code, r.headers
                else:
                    app_logger.trace("uuidcode={} - UNICORE/X communication response Status code: {}".format(uuidcode, r.status_code))
                    app_logger.trace("uuidcode={} - UNICORE/X communication response Content: {}".format(uuidcode, r.text))
                    app_logger.trace("uuidcode={} - UNICORE/X communication response Headers: {}".format(uuidcode, r.headers))
                    return r.text, r.status_code, r.headers 
        app_logger.debug("uuidcode={} - Session expired. Use accesstoken instead".format(uuidcode))
        try:
            del method_args['headers']['X-UNICORE-SecuritySession']
        except:
            pass
        with closing(requests.delete(method_args.get("url"),
                                     headers=method_args.get("headers", {}),
                                     data=method_args.get("data", "{}"),
                                     verify=method_args.get("certificate", False),
                                     timeout=1800)) as r2:
            if 'return_content' in method_args:
                app_logger.trace("uuidcode={} - UNICORE/X communication response Status code: {}".format(uuidcode, r2.status_code))
                app_logger.trace("uuidcode={} - UNICORE/X communication response Content: {}".format(uuidcode, r2.content.decode("utf-8")))
                app_logger.trace("uuidcode={} - UNICORE/X communication response Headers: {}".format(uuidcode, r2.headers))
                return r2.content.decode("utf-8"), r2.status_code, r2.headers
            else:
                app_logger.trace("uuidcode={} - UNICORE/X communication response Status code: {}".format(uuidcode, r2.status_code))
                app_logger.trace("uuidcode={} - UNICORE/X communication response Content: {}".format(uuidcode, r2.text))
                app_logger.trace("uuidcode={} - UNICORE/X communication response Headers: {}".format(uuidcode, r2.headers))
                return r2.text, r2.status_code, r2.headers
    elif method == "POST":
        with closing(requests.post(method_args.get("url"),
                                   headers=method_args.get("headers"),
                                   data=method_args.get("data", "{}"),
                                   verify=method_args.get("certificate", False),
                                   timeout=1800)) as r:
            if r.status_code != 432 and r.status_code != 500: # 432 -> SecuritySession expired. 500 -> Internal Server Error, maybe GPFS made bs?
                if 'return_content' in method_args:
                    app_logger.trace("uuidcode={} - UNICORE/X communication response Status code: {}".format(uuidcode, r.status_code))
                    app_logger.trace("uuidcode={} - UNICORE/X communication response Content: {}".format(uuidcode, r.content.decode("utf-8")))
                    app_logger.trace("uuidcode={} - UNICORE/X communication response Headers: {}".format(uuidcode, r.headers))
                    return r.content.decode("utf-8"), r.status_code, r.headers
                else:
                    app_logger.trace("uuidcode={} - UNICORE/X communication response Status code: {}".format(uuidcode, r.status_code))
                    app_logger.trace("uuidcode={} - UNICORE/X communication response Content: {}".format(uuidcode, r.text))
                    app_logger.trace("uuidcode={} - UNICORE/X communication response Headers: {}".format(uuidcode, r.headers))
                    return r.text, r.status_code, r.headers 
        app_logger.debug("uuidcode={} - Session expired. Use accesstoken instead".format(uuidcode))
        try:
            del method_args['headers']['X-UNICORE-SecuritySession']
        except:
            pass
        with closing(requests.post(method_args.get("url"),
                                   headers=method_args.get("headers", {}),
                                   data=method_args.get("data", "{}"),
                                   verify=method_args.get("certificate", False),
                                   timeout=1800)) as r2:
            if 'return_content' in method_args:
                app_logger.trace("uuidcode={} - UNICORE/X communication response Status code: {}".format(uuidcode, r2.status_code))
                app_logger.trace("uuidcode={} - UNICORE/X communication response Content: {}".format(uuidcode, r2.content.decode("utf-8")))
                app_logger.trace("uuidcode={} - UNICORE/X communication response Headers: {}".format(uuidcode, r2.headers))
                return r2.content.decode("utf-8"), r2.status_code, r2.headers
            else:
                app_logger.trace("uuidcode={} - UNICORE/X communication response Status code: {}".format(uuidcode, r2.status_code))
                app_logger.trace("uuidcode={} - UNICORE/X communication response Content: {}".format(uuidcode, r2.text))
                app_logger.trace("uuidcode={} - UNICORE/X communication response Headers: {}".format(uuidcode, r2.headers))
                return r2.text, r2.status_code, r2.headers
    elif method == "PUT":
        with closing(requests.put(method_args.get("url"),
                                  headers=method_args.get("headers"),
                                  data=method_args.get("data", "{}"),
                                  verify=method_args.get("certificate", False),
                                  timeout=1800)) as r:
            if r.status_code != 432 and r.status_code != 500: # 432 -> SecuritySession expired. 500 -> Internal Server Error, maybe GPFS made bs?
                if 'return_content' in method_args:
                    app_logger.trace("uuidcode={} - UNICORE/X communication response Status code: {}".format(uuidcode, r.status_code))
                    app_logger.trace("uuidcode={} - UNICORE/X communication response Content: {}".format(uuidcode, r.content.decode("utf-8")))
                    app_logger.trace("uuidcode={} - UNICORE/X communication response Headers: {}".format(uuidcode, r.headers))
                    return r.content.decode("utf-8"), r.status_code, r.headers
                else:
                    app_logger.trace("uuidcode={} - UNICORE/X communication response Status code: {}".format(uuidcode, r.status_code))
                    app_logger.trace("uuidcode={} - UNICORE/X communication response Content: {}".format(uuidcode, r.text))
                    app_logger.trace("uuidcode={} - UNICORE/X communication response Headers: {}".format(uuidcode, r.headers))
                    return r.text, r.status_code, r.headers 
        app_logger.debug("uuidcode={} - Session expired. Use accesstoken instead".format(uuidcode))
        try:
            del method_args['headers']['X-UNICORE-SecuritySession']
        except:
            pass
        with closing(requests.put(method_args.get("url"),
                                  headers=method_args.get("headers", {}),
                                  data=method_args.get("data", "{}"),
                                  verify=method_args.get("certificate", False),
                                  timeout=1800)) as r2:
            if 'return_content' in method_args:
                app_logger.trace("uuidcode={} - UNICORE/X communication response Status code: {}".format(uuidcode, r2.status_code))
                app_logger.trace("uuidcode={} - UNICORE/X communication response Content: {}".format(uuidcode, r2.content.decode("utf-8")))
                app_logger.trace("uuidcode={} - UNICORE/X communication response Headers: {}".format(uuidcode, r2.headers))
                return r2.content.decode("utf-8"), r2.status_code, r2.headers
            else:
                app_logger.trace("uuidcode={} - UNICORE/X communication response Status code: {}".format(uuidcode, r2.status_code))
                app_logger.trace("uuidcode={} - UNICORE/X communication response Content: {}".format(uuidcode, r2.text))
                app_logger.trace("uuidcode={} - UNICORE/X communication response Headers: {}".format(uuidcode, r2.headers))
                return r2.text, r2.status_code, r2.headers
