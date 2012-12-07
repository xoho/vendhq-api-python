from VendHQ.api.lib.mapping import Mapping
from VendHQ.api.lib.filters import FilterSet, StringFilter, NumberFilter, DateFilter, BoolFilter
from . import ResourceObject
from pprint import pformat

class Products(ResourceObject):

    @classmethod
    def filter_set(cls):
        fs = FilterSet(before = DateFilter(),
            after = DateFilter(),
            to = DateFilter(),
        )
        fs["from"] = DateFilter()
        return fs

    def getInventory(self, outlet_name):

        outlet = None
        for i in self._fields.inventory:
            if i.outlet_name==outlet_name:
                outlet=i
                break

        if outlet:
            try:
                return round(float(outlet['count']),5)
            except:
                return None

        return None