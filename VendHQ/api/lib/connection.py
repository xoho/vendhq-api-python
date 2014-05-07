"""
Connection Module

Handles put and get operations to the a REST API
"""
import sys
import urllib
import logging
import json
from pprint import pformat
import requests
from httplib import HTTPException

log = logging.getLogger("VendHQ.com")


class EmptyResponseWarning(HTTPException):
    pass

class Connection():
    """
    Connection class manages the connection to the REST API.
    """
    
    def __init__(self, host, base_url, auth):
        """
        Constructor
        
        On creation, an initial call is made to load the mappings of resources to URLS
        """
        self.host = host
        self.base_url = "%s/%s" % (host,base_url)
        if not self.base_url.startswith('http://') or not self.base_url.startswith('https://'):
            self.base_url = "https://%s" % self.base_url

        self.auth = auth
        
        log.info("API Host: %s" % (self.base_url))
        log.debug("Accepting json, auth: Basic %s" % self.auth)
        self.__headers = {"Authorization": "Basic %s" % self.auth,
                        "Accept": "*/*",
                        "Content-Type": "application/json"}
        
        self.__resource_meta = {}
        #self.__connection = HTTPSConnection(self.host)
        
        
        
    def meta_data(self):
        """
        Return a string representation of resource-to-url mappings 
        """
        return simplejson.dumps(self.__resource_meta)    
        
        
    
    def get(self, url="", query={}):
        """
        Perform the GET request and return the parsed results
        """
        qs = urllib.urlencode(query)
        if qs:
            qs = "?%s" % qs
            
        url = "%s%s%s" % (self.base_url, url, qs)
        
        response = requests.get(url, data=None, headers=self.__headers)
        
        try:data = response.json()
        except Exception, e:
            log.debug("GET: %s" % url)
            raise HTTPException("Could not decode json data from response %s" % response.text)

        status_code = response.status_code
        
        log.debug("GET %s status %d" % (url,status_code))
        log.debug('Response headers:')
        log.debug(pformat(response.headers))
        
        result = {}
        reason = response.reason
        
        # Check the return status
        status_code = response.status_code
        if status_code == 200:
            result = data
            log.debug("OUTPUT: %s" % data)
            
        elif status_code == 204:
            raise EmptyResponseWarning("%d @ https://%s%s" % (status_code, url, reason))
        
        elif status_code == 404:
            log.debug("%s returned 404 status" % url)
            raise HTTPException("%d @ %s - %s" % (status_code, url, reason))
        
        elif status_code >= 400:
            try:_result = data
            except: _result = response.text
            log.debug("OUTPUT %s" % _result)
            raise HTTPException("%d @ %s - %s" % (status_code, url, reason))
        
        elif status_code >= 300:
            try:_result = data
            except: _result = response.text
            log.debug("OUTPUT %s" % _result)
            
        
        return result
    
    
    def get_url(self, resource_name):
        """
        Lookup the "url" for the resource name from the internally stored resource mappings
        """
        return self.__resource_meta.get(resource_name,{}).get("url", None)
    
    def get_resource_url(self, resource_name):
        """
        Lookup the "resource" for the resource name from the internally stored resource mappings
        """
        return self.__resource_meta.get(resource_name,{}).get("resource", None)
        
        
    def update(self, url, updates):
        """
        Make a PUT request to save updates
        """
        url = "%s%s" % (self.base_url, url)
        log.debug("PUT %s" % (url))
        
        
        put_headers = {"Content-Type": "application/json"}
        put_headers.update(self.__headers)
        response = requests.post(url, data=json.dumps(updates), headers=put_headers)
        try:data = response.json()
        except Exception, e:
            raise HTTPException("Could not decode json data from response %s" % response.text)

        
        status_code = response.status_code
        
        log.debug("PUT %s status %d" % (url,status_code))
        log.debug("OUTPUT: %s" % pformat(data))
        
        result = {}
        if status_code == 200:
            result = data
        
        elif status_code == 204:
            raise EmptyResponseWarning("%d @ https://%s%s" % (status_code, self.host, url))
        
        elif status_code == 404:
            log.debug("%s returned 404 status" % url)
            raise HTTPException("%d @ https://%s%s" % (status_code, self.host, url))
        
        elif status_code >= 400:
            try:_result = data
            except: _result = response.text
            log.debug("OUTPUT %s" % _result)
            raise HTTPException("%d @ https://%s%s" % (status_code, self.host, url))
        
        elif status_code >= 300:
            try:_result = data
            except: _result = response.text
            log.debug("OUTPUT %s" % _result)
            raise HTTPException("%d @ https://%s%s" % (status_code, self.host, url))        
        return result

    def create(self, url, data):
        """
        Posts data to the url to create a new object.
        """

        url = "%s%s" % (self.base_url, url)
        log.debug("POST %s" % (url))
        

        post_headers = {"Content-Type": "application/json"}
        post_headers.update(self.__headers)

        response = requests.post(url, data=json.dumps(data), headers=post_headers)
        try:data = response.json()
        except Exception, e:
            raise HTTPException("Could not decode json data from response %s" % response.text)
        
        status_code = response.status_code

        log.debug("POST %s status %d" % (url,status_code))
        log.debug("OUTPUT: %s" % data)

        result = {}
        if status_code == 200:
            result = data

        elif status_code == 204:
            raise EmptyResponseWarning("%d @ https://%s%s" % (status_code, self.host, url))

        elif status_code == 404:
            log.debug("%s returned 404 status" % url)
            raise HTTPException("%d @ https://%s%s" % (status_code, self.host, url))

        elif status_code >= 400:
            try:_result = data
            except: _result = response.text
            log.debug("OUTPUT %s" % _result)
            raise HTTPException("%d @ https://%s%s" % (status_code, self.host, url))
        
        elif status_code >= 300:
            try:_result = data
            except: _result = response.text
            log.debug("OUTPUT %s" % _result)
            raise HTTPException("%d @ https://%s%s" % (status_code, self.host, url))        
        
        return result

    def __repr__(self):
        return "Connection %s" % (self.host)
    
    


    