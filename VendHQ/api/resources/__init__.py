import sys
import logging
from VendHQ.api.lib.mapping import Mapping
from VendHQ.api.lib.filters import FilterSet
from VendHQ.api.lib.connection import EmptyResponseWarning
from datetime import datetime
from pprint import pformat
log = logging.getLogger("VendHQ.Resource")


class ResourceAccessor(object):
    """
    Provides methods that will create, get, and enumerate resourcesObjects.
    """
    
    def __init__(self, resource_name, connection):
        """
        Constructor
        
        @param resource_name: The name of the resource being accessed.  There must be a
                              corresponding ResourceObject class
        @type resource_name: String
        @param connection: Connection to the REST API
        @type connection: {Connection}
        """
        self._parent = None
        self.__resource_name = resource_name
        self._connection = connection
        
        try:
            mod = __import__('%s' % resource_name, globals(), locals(), [resource_name], -1)
            self._klass = getattr(mod, resource_name)
        except:
            self._klass = ResourceObject
         
        self._url = self.__resource_name.lower()
            
         
    def __get_page(self, page, limit, query={}):
        """
        Get specific pages
        """
        # VendHQ uses pretty urls for query
        query_url = []
        log.debug('query %s' % query)
        """
        for k,v in query.items():
            query_url.append(k)
            if isinstance(v,type(datetime.now())):
                query_url.append(v.strftime('%Y-%m-%d %H:%M:%S'))
            else:
                query_url.append(str(v))
        """
        q_dict = {}
        # cast the types
        for k,v in query.items():
            if isinstance(v,datetime):
                q_dict[k] = v.strftime('%Y-%m-%d %H:%M:%S')
            else:
                q_dict[k] = str(v)
                
        #url = '%s%s' % (self._url, ''.join(query_url) if query_url else '')

        _query = {"page": page, "per_page": limit}
        _query.update(q_dict)
        log.debug('url: %s' % self._url)
        log.debug( 'query: %s' % _query)

        data = self._connection.get("%s" % self._url, _query)
        return data
    
    
    def enumerate(self, start=0, limit=0, query={}, max_per_page=50):
        """
        Enumerate resources
        
        @param start: The instance to start on
        @type pages: int
        @param limit: The number of items to return, Set to 0 to return all items
        @type start_page: int
        @param query: Search criteria
        @type query: FilterSet
        @param max_per_page: Number of items to return per request
        @type max_per_page: int
        """
        requested_items = limit if limit else sys.maxint
        max_per_page = min(max_per_page, 250)
        max_per_page = min(requested_items, max_per_page)
        
        current_page = int( start / max_per_page )
        offset = start % max_per_page
         
        #while current_page < total_pages and requested_items:
        while requested_items:
            current_page += 1
            page_index = 0
            
            try:
                data = self.__get_page(current_page, max_per_page, query)
                if self.__resource_name.lower() in data.keys():
                    if len(data[self.__resource_name.lower()])==0:
                        # No more data is returned
                        break

                    for res in data[self.__resource_name.lower()]:
                        if offset <= page_index:
                            offset = 0  # Start on the first item for the next page
                            if not requested_items:
                                break
                            else:
                                requested_items -= 1
                                page_index += 1
                                yield self._klass(self._connection, self._url, res, self._parent)
                        else:
                            page_index += 1

                    if page_index < max_per_page:
                        requested_items = 0
                break
            # If the response was empty - we are done
            except EmptyResponseWarning:
                requested_items = 0
            except:
                raise
                    


    def get(self, id):
        url = "%s/%s" % (self._url, id)
        try:
            result = self._connection.get(url)
            data = {}
            for key in result.keys():
                log.debug("Looking for item in %s" % key)
                data = result[key][0]
                break
            return self._klass(self._connection, self._url, data, self._parent)
        except:
            return None

    def create(self, data):
        try:
            result = self._connection.create(self._url, data)
            return self._klass(self._connection, self._url, result, self._parent)
        except:
            return None
    
    def inquire(self, what=None, query={}):
        _query = {}
        if query:
            _query = query.query_dict()
        #_query["q"] = what
        
        result = self._connection.get(self._url, _query)
        
        resource_name = self.__resource_name.lower()

        if result and isinstance(result, dict) and resource_name in result.keys():
            return result[resource_name]

        return None
    
        
    def get_count(self, query={}):
        _query = {}
        if query:
            _query = query.query_dict()
        _query["q"] = "count"
        
        result = self._connection.get("%s.xml" % (self._url), _query)
        return result.get("count")
    
    def filters(self):
        try:
            return self._klass.filter_set()
        except:
            return FilterSet()
    
    def get_name(self):
        return self.__resource_name
    
    
    def get_subresources(self):
        return self._klass.sub_resources
    
    name = property(fget=get_name)
    
    
class SubResourceAccessor(ResourceAccessor):
    
    def __init__(self, klass, url, connection, parent):
        """
        """
        self._parent = parent
        self._connection = connection
        self._klass = klass
        self._url = url if isinstance(url, basestring) else url["resource"]
        
    

class ResourceObject(object):
    """
    The realized resource instance type.
    """
    writeable = [] # list of properties that are writeable
    read_only = [] # list of properties that are read_only
    sub_resources = {}  # list of properties that are subresources
    can_create = False  # If create is supported
    can_update = False
    
    def __init__(self, connection, url, fields, parent):
        #  Very important!! These two lines must be first to support 
        # customized getattr and setattr
        self._fields = fields or dict()
        self._fields = Mapping(self._fields)
        self._updates = {} # the fields to update
        
        self._parent = parent
        self._connection = connection
        self._url = "%s/%s" % (url, self.id) if self.id else url
        self._cast_list()
        
    def _cast_list(self):
        for k, v in self._fields.items():
            if isinstance(v, list):
                new_list = []
                for d in v:
                    new_list.append(Mapping(d))
                self._fields[k] = new_list
            if isinstance(v, dict):
                self._fields[k] = Mapping(v)
        
        
    def __getattr__(self, attrname):
        """
        Override get access to look up values in the updates first, 
        then from the fields, if the fields value indicates that
        its a sub resource that is not yet realized, make the call to
        inflate the subresource object.
        """
        
        # If the value was set, when asked give this value,
        # not the original value
        if self._updates.has_key(attrname):
            return self._updates[attrname]
        
        if not self._fields.has_key(attrname):
            raise AttributeError("%s not available" % attrname)
        # Look up the value in the _fields
        data = self._fields.get(attrname,None)
        
        if data is None:
            return data
        else:
            
            # if we are dealing with a sub resource and we have not 
            # already made the call to inflate it - do so
            if self.sub_resources.has_key(attrname) and isinstance(data, dict):
                
                _con = SubResourceAccessor(self.sub_resources[attrname].get("klass", ResourceObject), 
                                           data, self._connection, 
                                           self)
                
                # If the subresource is a list of objects
                if not self.sub_resources[attrname].get("single", False):
                    _list = []
                    for sub_res in _con.enumerate():
                        _list.append(sub_res)
                    self._fields[attrname] = _list
                
                # if the subresource is a single object    
                else:
                    self._fields[attrname] = _con.get("")
                    
            # Cast all dicts to Mappings - for . access
            elif isinstance(data, dict):
                log.debug("Getting dict %s" % attrname)
                val = Mapping(data)
                self._fields[attrname] = val
            
            return self._fields[attrname]
            
        raise AttributeError
    
    
    def __setattr__(self, name, value):
        """
        All sets on field properties are caches in the updates dictionary
        until saved
        """
        log.debug('setattr %s %s' % (name, value))
        if name == "_fields":
            object.__setattr__(self, name, value)
        
        elif self._fields.has_key(name):
            if name in self.read_only:
                raise AttributeError("Attempt to assign to a read-only property '%s'" % name)
            elif not self.writeable or name in self.writeable:
                self._updates.update({name:value})
        else:
            object.__setattr__(self, name, value)
            
        
    def get_url(self):
        return self._url
    
    def create(self, data):
        log.info("Creating %s" % self.get_url())
        results = self._connection.create(self.get_url(), data)
        return results
        
    
    def save(self):
        """
        Save any updates and set the fields to the values received 
        from the return value and clear the updates dictionary
        """
        log.debug("saving...")
        if self._updates:
            log.info("Updating %s" % self.get_url())
            log.debug("Data: %s" % self._updates)
            
            results = self._connection.update(self.get_url(), self._updates)
            self._updates.clear()
            self._fields = results
                     
        
    def __repr__(self):
        return str(self._fields)
    
    def to_dict(self):
        return self._fields
    
    
    def inquire(self, what, query={}):
        _query = {}
        if query:
            _query = query.query_dict()
        _query["q"] = what
        
        result = self._connection.get("%s.xml" % (self._url), _query)
        return result.get(what)
    
        
