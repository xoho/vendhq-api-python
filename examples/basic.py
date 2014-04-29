

STORE_HOST = "nahnay.vendhq.com"
STORE_USERNAME = "***"
STORE_PWD = "****"

from pprint import pprint
import sys, os
import json
import random

userfn = 'users.json'
users = {}
if os.path.exists(userfn):
    f = open(userfn, 'r')
    try:
        users = json.load(f)
    except:
        pass

if users:
    user = "possync"
    STORE_HOST = users[user]['host']
    STORE_USERNAME = users[user]['username']
    STORE_PWD = users[user]['pwd']


sys.path.append(os.path.abspath('..'))

import logging
log = logging.getLogger(__file__)
log.setLevel(logging.DEBUG)

from datetime import datetime, timedelta
from VendHQ.api import ApiClient

log.debug("HOST %s, USER: %s" % (STORE_HOST, STORE_USERNAME))
api = ApiClient(STORE_HOST, STORE_USERNAME, STORE_PWD)


logging.basicConfig(level=logging.DEBUG, 
                    filename='/tmp/basic.log',
                    stream=sys.stdout,
                    format='%(asctime)s %(levelname)-8s[%(name)s] %(message)s',
                    datefmt='%m/%d %H:%M:%S')
log = logging.getLogger()


def create_register_sale(register_name, username, order, sale_status="SAVED", loyality_x=50):
    data = {'register_name':register_name,'username':username, 'sale_status':sale_status, 'loyality_x':loyality_x}
    api.update_order(order=order, cart_name="BigCommerce", data=data)


def get_register_sale(register_sale_id):

    register_sale = api.Register_sales.get(register_sale_id)
    pprint(register_sale)
    return True


def list_registers():
    for reg in api.Registers.enumerate():
        pprint(reg.to_dict())


def list_outlets():
    for outlet in api.Outlets.enumerate():
        pprint(outlet.to_dict())

def list_payment_types():
    for pt in api.Payment_types.enumerate():
        pprint(pt.to_dict())

##
# Tests to run
##

def run_test(testname, data={}):

    print '\n'*5
    print '*'*80
    print "running %s" % testname
    print '-'*80
    
    if testname=='product_enum':
        for product in api.Products.enumerate(start=0, limit=20):
            print product.name
        return True

    if testname=="product_get_by_sku":
        
        filters = api.Products.filters()

        for k,v in data.items():
            filters[k] = {'value':v}


        products = api.Products.inquire(query=filters)
        if not products:
            print 'Could not retrieve product data'
            return False

        if len(products)<1:
            print 'No products returned matching %s' % ','.join(data.values())
            return True

        if len(products)>1:
            print 'More than one product returned matching %s' % ','.join(data.values())
            return False

        product = products[0]
        pprint(product)

        return True

    if testname=='get_register_id':

        print 'Register %s id is %s' % (data['name'], api.get_register_id(data['name']))
        return True

    if testname=='get_customer':
        customer = api.get_customer_by_email(data['email'])
        pprint(customer)
        return True

    if testname=='create_customer':
        customer = api.create_customer(data)
        pprint(customer)
        return True


    if testname=='create_register_sale':

        create_register_sale(register_name=data['register_name'],
                            username='admin', 
                            order=data['order'])
        return True


    if testname=='get_register_sale':
        get_register_sale(data)
        return True
        
  
    if testname=='list_registers':
        list_registers()
        return True


    if testname=='list_outlets':
        list_outlets()
        return True

    if testname=='list_payment_types':
        list_payment_types()
        return True

    print '*'*80

if __name__ == "__main__":
    print '\n'*20
    # # Create products
    # #createProducts(api, 125)

    # # Get  products starting at a product page
    # """
    # for product in api.Products.enumerate(start=0, limit=3):
    #     print "Product: %s %s on hand: %s" % (product.id, product.name, product.getInventory('Main Outlet'))
    # """
    # print api.Products.get_count()
    # # Get products changed in the last hour
    # q = {'since':datetime.utcnow()-timedelta(days=2)}
    # print q["since"]
    # print 'products changed in the last hour:'
    # for product in api.Products.enumerate(query=q):
    #     print "Product: %s %s on hand: %s" % (product.id, product.sku, product.getInventory('Main Outlet'))
    #     for inv in product.inventory:
    #         print "\t", inv["outlet_name"], inv["count"]
    
    # p = api.Products.get("14338471-3ed3-11e2-b1f5-4040782fde00")
    # print p.name
    # for sales in api.Register_Sales.enumerate(query=q):
    #     for prod in sales.register_sale_products:
    #         print prod.id

    # # Get Register sales
    # #for sale in api.Register_Sales.enumerate():
    # #    print "Sale: %s" % sale.id

    customer = {
        "customer_code": "pat-rick",
        "company_name": "",
        "first_name": "Pat",
        "last_name": "Rick",
        "phone": "555-1235",
        "mobile": "",
        "fax": "",
        "email": "fame@email.com",
        "website": "",
        "physical_address1": "",
        "physical_address2": "",
        "physical_suburb": "",
        "physical_city": "",
        "physical_postcode": "",
        "physical_state": "",
        "physical_country_id": "",
        "postal_address1": "",
        "postal_address2": "",
        "postal_suburb": "",
        "postal_city": "",
        "postal_postcode": "",
        "postal_state": "",
        "postal_country_id": "US"
    }

    order = {}
    orderfn = 'order.json'
    if os.path.exists(orderfn):
        order = json.load(open(orderfn,'r'))

    tests = []

    # tests.append((0,'product_enum',{}))
    # tests.append((1,'product_get_by_sku',{'sku':'AW13-18-W-S','handle':'AnjuliCrop-White'}))
    # tests.append((2,'product_get_by_sku',{'sku':'vend-discount','handle':'vend-discount'}))
    # tests.append((3,'get_register_id',{'name':'Main Register'}))
    # tests.append((4,'create_customer',customer))
    # tests.append((5,'get_customer',{'email':customer['email']}))
    tests.append((6,'create_register_sale',{'register_name':'Main Register', 'order':order, 'username':'dev'}))
    # tests.append((7,'get_register_sale','21ff4367-c951-11e3-a0f5-b8ca3a64f8f4'))
    # tests.append((8,'list_registers',None))
    # tests.append((9,'list_payment_types',None))
    # tests.append((10,'list_outlets',None))

    status = []
    for test in sorted(tests, key=lambda x: x[0]):
        result = run_test(test[1], test[2])
        status.append((test[1], 'passed' if result else 'failed'))

    print '-'*80
    for stat in status:
        print "%s\t%s" % stat
    print '-'*80


