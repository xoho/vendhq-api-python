

STORE_HOST = "nahnay.vendhq.com"
STORE_USERNAME = "***"
STORE_PWD = "****"

from pprint import pprint
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
    """
    for product in api.Products.enumerate(start=0, limit=3):
        print "Product: %s %s on hand: %s" % (product.id, product.name, product.getInventory('Main Outlet'))
    """
    print api.Products.get_count()
    # Get products changed in the last hour
    q = {'since':datetime.utcnow()-timedelta(days=2)}
    print q["since"]
    print 'products changed in the last hour:'
    for product in api.Products.enumerate(query=q):
        print "Product: %s %s on hand: %s" % (product.id, product.sku, product.getInventory('Main Outlet'))
        for inv in product.inventory:
            print "\t", inv["outlet_name"], inv["count"]
    
    p = api.Products.get("14338471-3ed3-11e2-b1f5-4040782fde00")
    print p.name
    for sales in api.Register_Sales.enumerate(query=q):
        for prod in sales.register_sale_products:
            print prod.id

    # Get Register sales
    #for sale in api.Register_Sales.enumerate():
    #    print "Sale: %s" % sale.id

