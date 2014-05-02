#Payment_types
#Registers
from VendHQ.api.lib.mapping import Mapping
from VendHQ.api.lib.filters import FilterSet, StringFilter, NumberFilter, DateFilter, BoolFilter
from . import ResourceObject


class Payment_types(ResourceObject):
    
    @classmethod
    def filter_set(cls):
        fs = FilterSet(before = DateFilter(),
                         after = DateFilter(),
                         to = DateFilter(),
                         ) 
        fs["from"] = DateFilter()
        return fs