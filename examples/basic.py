

STORE_HOST = "store.vendhq.com"
STORE_USERNAME = "username"
STORE_PWD = "password"

try:
    from settings import *
except:
    pass
import sys, os

sys.path.append(os.path.abspath('..'))

import logging
log = logging.getLogger(__file__)
log.setLevel(logging.DEBUG)

from datetime import datetime, timedelta
from VendHQ.api import ApiClient

logging.basicConfig(level=logging.INFO, 
                    stream=sys.stdout,
                    format='%(asctime)s %(levelname)-8s[%(name)s] %(message)s',
                    datefmt='%m/%d %H:%M:%S')
log = logging.getLogger("main")


if __name__ == "__main__":
    log.debug("HOST %s, USER: %s" % (STORE_HOST, STORE_USERNAME))
    api = ApiClient(STORE_HOST, STORE_USERNAME, STORE_PWD)

    # Create products
    #createProducts(api, 125)

    # Get  products starting at a product page
    for product in api.Products.enumerate(start=0, limit=3):
        print "Product: %s on hand: %s" % (product.id, product.getInventory('Main Outlet'))

    # Get products changed in the last hour
    q = {'since':datetime.now()-timedelta(hours=-1)}
    print 'products changed in the last hour:'
    for product in api.Products.enumerate(query=q):
        print "Product: %s on hand: %s" % (product.id, product.getInventory('Main Outlet'))


    # Get Register sales
    #for sale in api.Register_Sales.enumerate():
    #    print "Sale: %s" % sale.id

