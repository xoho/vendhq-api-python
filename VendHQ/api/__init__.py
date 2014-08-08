import os
import sys
import base64
import logging
from datetime import datetime

from VendHQ.api.lib.connection import Connection
from resources import ResourceAccessor

from pprint import pprint, pformat

log = logging.getLogger("VendHQ.api")
pos_log = logging.getLogger("pos")
log.setLevel(logging.DEBUG)

class ApiClient(object):
    BASE_URL = '/api/'
    
    def __init__(self, host, username, pwd):
        auth = base64.b64encode("%s:%s" % (username,pwd))
        self._connection = Connection(host, self.BASE_URL, auth)
                
    def connection(self):
        pass

    
    def __getattr__(self, attrname):
        try:
            return ResourceAccessor(attrname, self._connection)
        except:
            raise AttributeError
        raise AttributeError


    