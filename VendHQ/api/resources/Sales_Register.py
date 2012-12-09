from VendHQ.api.lib.mapping import Mapping
from VendHQ.api.lib.filters import FilterSet, StringFilter, NumberFilter, DateFilter, BoolFilter
from . import ResourceObject
from pprint import pformat

class Sales_Register(ResourceObject):

    @classmethod
    def filter_set(cls):
        fs = FilterSet(since = DateFilter())
        return fs

    