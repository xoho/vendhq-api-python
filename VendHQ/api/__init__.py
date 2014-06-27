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
    key_field = "sku"
    def __init__(self, host, username, pwd):
        auth = base64.b64encode("%s:%s" % (username,pwd))
        self._connection = Connection(host, self.BASE_URL, auth)
        

        self.__taxes = []
        for t in self.Taxes.enumerate():
            self.__taxes.append(t)

        
    def connection(self):
        pass

    
    def get_url_registry(self):
        return self._connection.meta_data()

        
    def __getattr__(self, attrname):
        try:
            return ResourceAccessor(attrname, self._connection)
        except:
            raise AttributeError
        raise AttributeError


    def get_product(self, id):
        prod = {}
        try:
            product = self.Products.get(id)
            prod["name"] = product.name
            prod["sku"] = getattr(product, self.key_field)
            prod["id"] = product.id
            quantity = 0
            
            try:
                for inv in product.inventory:
                    quantity += int(float(inv["count"]))
            except:
                pass
             
            prod["quantity"] = quantity
            return prod
        except:
            pos_log.exception("Unable to get product %s" % id)
            
        return None
            
        
    def get_products(self, since):
        q = {}
        if since:
            q = {'since':since}
        
        for product in self.Products.enumerate(query=q):
            prod = {}
            prod["sku"] = getattr(product, self.key_field)
            prod["id"] = product.id
            prod["name"] = product.name
            quantity = 0
            
            try:
                for inv in product.inventory:
                    quantity += int(float(inv["count"]))
            except:
                pass 
            
            prod["quantity"] = quantity
            yield prod

    ##
    # Helper functions
    ##
    def get_register_id(self, name):
        reg = None
        for register in self.Registers.enumerate():
            if not reg: reg=register

            if register.name==name:
                reg = register
                break
        
        return reg.id if reg else None

    def get_customer_by_email(self, email):
        filters = self.Customers.filters()

        filters['email']  = {'value':email}

        customers = self.Customers.inquire(query=filters)
        if len(customers)>0:
            return customers[0]

        return None
        
    def create_customer(self, billing_address):

        mapping = {
            "phone": "phone",
            "email": "email",
            "first_name": "first_name",
            "last_name": "last_name",
            "physical_address1": "street_1",
            "physical_address2": "street_2",
            "physical_city": "city",
            "physical_postcode": "zip",
            "physical_state": "state",
            "physical_country_id": "country_iso2"
        }

        cust_data = {}
        for k,v in mapping.items():
            if v in billing_address.keys():
                cust_data[k] = billing_address[v]
            else:
                cust_data[k] = ''

        pos_log.info("Creating customer %s" % cust_data["last_name"])
        customer = self.Customers.create(cust_data)
        return customer

    def get_or_create_customer(self, billing_address):
        customer = self.get_customer_by_email(billing_address['email'])
        if not customer:
            self.create_customer(billing_address)
            customer = self.get_customer_by_email(billing_address['email'])

        return customer

    def get_tax(self, tax_rate):
        pos_log.debug("Finding Tax rate for %f" % tax_rate)
        tax = None
        for t in self.__taxes:
            if not tax: tax = t
            # find closest match
            if abs(tax_rate-t.rate)<0.002:
                tax=t
                break

        return tax


    def get_payment(self, payment_method):
        payment = None
        for p in self.Payment_types.enumerate():
            if not payment: payment = p 
            if p.name.lower()==payment_method.lower():
                payment = p 
                break
        return payment


    def get_product_by_sku(self, sku):
        filters = self.Products.filters()
        filters['sku'] = {'value':sku}

        products = self.Products.inquire(query=filters)
        if len(products)>0:
            return products[0]

        return None


    def get_or_create_product(self, product_data):
        product = self.get_product_by_sku(product_data['sku'])
        if not product:
            data = {}
            data['sku'] = product_data['sku']
            data['handle'] = data['handle'] if 'handle' in data.keys() else data['sku']
            data['name'] = product_data['name']
            data['retail_price'] =  product_data['base_price']
            pos_log.info("Creating product %s - %s" % (data["sku"], data["name"]))
            self.Products.create(data)
            product = self.get_product_by_sku(product_data['sku'])

        return product            
    
    
    def get_updated_products(self, since):
        
        prods = {}
        q = {"since": since}
        
        pos_log.info("Gathering products modified since %s" % since)
        
        pos_log.info("Checking stock movements")
        for st in self.Stock_Movements.enumerate(query=q):
            print st.updated_at, st.id, st.type, st.status
            if (st.type == "SUPPLIER" and st.status == "RECEIVED") or (st.type=="STOCKTAKE" and st.status=="STOCKTAKE_COMPLETE"):
                for prod in st.products:
                    id = prod.product_id
                    if not prods.has_key(id):
                        prods[id] = {"counted": False, "sold": False, "updated": False, "received": False}
                    
                    if st.type == "STOCKTAKE":
                        prods[id]["counted"] = True
                    
                    if st.type == "SUPPLIER":
                        prods[id]["received"] = True
        
        pos_log.info("Checking products")
        for product in self.Products.enumerate(query=q):
            id = product.id
            if not prods.has_key(id):
                prods[id] = {"counted": False, "sold": False, "updated": False, "received": False}
            prods[id]["updated"] = True
    
        pos_log.info("Checking register sales")
        for sales in self.Register_Sales.enumerate(query=q):
            for prod in sales.register_sale_products:
                id = prod.product_id
                if not prods.has_key(id):
                    prods[id] = {"counted": False, "sold": False, "updated": False, "received": False}
                prods[id]["sold"] = True

        pos_log.info("*** Checking for VOIDED Sales")
        q["status"] = "VOIDED"
        for sales in self.Register_Sales.enumerate(query=q):
            for prod in sales.register_sale_products:
                id = prod.product_id
                if not prods.has_key(id):
                    prods[id] = {"counted": False, "sold": False, "updated": False, "received": False}
                prods[id]["sold"] = True

        return prods     


    def update_order(self, order=None, cart_name=None, data={}):    
        register_name = '' if not 'register_name' in data.keys() else data['register_name']
        username = 'admin' if not 'username' in data.keys() else data['username']
        sale_status = "CLOSED" if not 'sale_status' in data.keys() else data['sale_status']
        loyality_x = 0 if not 'loyality_x' in data.keys() else data['loyality_x']

        register_id = self.get_register_id(register_name)
        customer = self.get_or_create_customer(order['billing_address'])

        for k in ['total_ex_tax','total_tax','id','date_modified', 'total_inc_tax', 'products']:
            if not k in order.keys():
                raise Exception("Invalid order data: could not find '%s' in order fields [%s]" % (k, ",".join(order.keys())))

        loyality_x = max(loyality_x,0)

        o = {}
        notes = []

        o['register_id'] = register_id
        o['customer_id'] = customer['id']
        o['user_name']  = username
        o['status'] = sale_status if sale_status in ['SAVED','CLOSED','OPEN'] else "SAVED"

        # Shipping costs
        try: shipping_cost = float(order['base_shipping_cost'])
        except: shipping_cost = 0
        try: shipping_tax = float(order['shipping_cost_inc_tax'])-shipping_cost
        except: shipping_tax=0

        total = float(order['total_ex_tax'])
        tax = float(order['total_tax']) + shipping_tax
        tax_pc = 0 if total==0 else tax/total

        o['tax_pc'] = tax_pc
        taxobj = self.get_tax(tax_pc)
        o['tax_name'] = taxobj.name
        pos_log.debug("Applying Tax %s %f" % (taxobj.name, taxobj.rate))

        # Get mapped items
        order_map = {
            "sale_date": {"field": "date_modified", "type":"datetime", "default":datetime.utcnow()},
            "total_price": {"field": "total_ex_tax", "type":"float", "default":0.0}, # total excluding tax
            "total_tax": {"field": "total_tax", "type":"float", "default":0.0},
            #"invoice_number": {"field": "id", "type":"int", "default":0},
            #"invoice_sequence": {"field": "id", "type":"int", "default":0},
            "note": {"field": 'customer_message', "type":"str", "default":""},
        }
        for k,v in order_map.items():
            o[k] = order[v['field']] if v['field'] in order.keys() else v['default']

        o['sale_date'] = o["sale_date"].strftime("%Y-%m-%d %H:%M:%S")
        notes.append('Online order id: %s' % order['id'])
        if o['note'] and len(o['note'])>0: notes.append('Customer message: %s' % o['note'])

        o['register_sale_products'] = []

        # Update shipping costs if any as a new entry
        if shipping_cost>0:
            entry = {
                'sku':'SHIPPING', 
                'name':"Shipping", 
                "base_price": shipping_cost,
                "quantity":1,
                "total_tax": shipping_tax,
                "price_ex_tax": shipping_cost,
                "price_tax": shipping_tax
                }
            try:order['products'].append(entry)
            except: pass

        if float(order['store_credit_amount'])>0:
            entry = {
                'sku':'vend-discount', 
                'name': 'Online store credit', 
                "base_price": -float(order['store_credit_amount']),
                "quantity":1,
                "total_tax":0        
            }
            order['products'].append(entry)

        # handle the entries
        entry_errors = []
        
        # entry map
        entry_map = {
            "quantity": "quantity",
            "price": 'base_price',
            "tax" : "total_tax",
            "total_tax": "total_inc_tax"
        }

        line_item_discount = 0.0
        for entry in order['products']:  
            if not 'sku' in entry.keys():
                if 'id' in entry.keys():
                    notes.append("Could not find sku for order entry %s" % entry['id'])
                else:
                    notes.append("Could not find details for order entry %s" % entry)
                continue

            register_sale_product = {}

            entry_total_ex_tax = float(entry['price_ex_tax'])
            entry_tax = float(entry['price_tax'])
            tax = self.get_tax(0 if entry_total_ex_tax==0 else entry_tax/entry_total_ex_tax)

            register_sale_product['quantity'] = entry['quantity']
            register_sale_product['price'] = entry_total_ex_tax
            register_sale_product['tax_total'] = entry_tax # Not sure why Vend has both tax and tax_total??
            register_sale_product['tax'] = entry_tax
            register_sale_product['tax_id'] = tax.id
            
            entry_product = self.get_or_create_product(entry)
            
            if entry_product:
                register_sale_product['product_id'] = entry_product['id']

                if 'applied_discounts' in entry.keys():
                    line_discount = 0
                    for discount in entry['applied_discounts']:
                        line_discount += float(discount['amount'])
                    register_sale_product['discount'] = line_discount
                    line_item_discount += line_discount
                    register_sale_product['price'] = float(register_sale_product['price'])-line_discount

                # Loyalty values, post-discount
                loyalty_value = 0
                if not entry_product['sku'] in ['SHIPPING', 'vend-discount']:
                    if loyality_x>0:
                        loyalty_value = float(register_sale_product['price'])/loyality_x

                    for pbe in entry_product['price_book_entries']:
                        if 'loyalty_value' in pbe.keys() and pbe['loyalty_value']:
                            loyalty_value = float(pbe['loyalty_value'])
                register_sale_product['loyalty_value'] = loyalty_value
                
                # Finalize line item
                register_sale_product['price_set'] = 1
                register_sale_product['status'] = "CONFIRMED"

                o['register_sale_products'].append(register_sale_product)


            # Update wrapping cost
            if 'base_wrapping_cost' in entry.keys() and float(entry['base_wrapping_cost'])>0:
                e = {}
                e['handle'] = "WRAPPING"
                wrap_name = "" if len(entry['wrapping_name'])<1 else "-%s" % entry['wrapping_name']
                e['sku'] = "WRAPPING%s" % wrap_name.strip().replace(" ","")
                e['name'] = ("Wrapping %s" % wrap_name).strip()
                e['base_price'] = entry['base_wrapping_cost']
                e['quantity'] = 1
                wraptax = float(entry['wrapping_cost_tax'])
                e['tax'] = wraptax
                e['total_tax'] = wraptax
                wrap_product = self.get_or_create_product(e)
                register_sale_product = {}
                for k,v in entry_map.items():
                    register_sale_product[k] = e[v]
                register_sale_product['tax_id'] = taxobj.id
                register_sale_product['product_id'] = wrap_product['id']
                register_sale_product['price_set'] = 1
                register_sale_product['status'] = "CONFIRMED"
                
                wrap_message = "" if len(entry['wrapping_message'])<1 else entry['wrapping_message']
                #notes.append("Wrapping message for %s-%s: %s" % (entry['sku'], entry['name'], wrap_message))
                register_sale_product['attributes'] = [{'name':'line_note','value':'Wrapping message: %s' % wrap_message}]
                o['register_sale_products'].append(register_sale_product)

        # Update overall discount if necessary
        if float(order['coupon_discount'])>line_item_discount:
                amount = float(order['coupon_discount'])-line_item_discount
                e = {}
                e['sku'] = 'vend-discount'
                e['name'] = 'Store discount'
                e['base_price'] = -amount
                e['quantity'] = -1
                e['tax'] = 0
                e['total_tax'] = 0
                discount_product = self.get_or_create_product(e)
                register_sale_product = {}
                for k,v in entry_map.items():
                    register_sale_product[k] = e[v]
                register_sale_product['tax_id'] = taxobj.id
                register_sale_product['product_id'] = discount_product['id']
                register_sale_product['price_set'] = 1
                register_sale_product['status'] = "CONFIRMED"

                o['register_sale_products'].append(register_sale_product)

        # Payment method
        payment = self.get_payment(order['payment_method'])
        o['register_sale_payments'] = []

        reg_sale_payment = {'retailer_payment_type_id':payment.id}
        reg_sale_payment['payment_date'] = order['date_modified'].strftime("%Y-%m-%d %H:%M:%S")
        reg_sale_payment['amount'] = order['total_inc_tax']

        o['register_sale_payments'].append(reg_sale_payment)

        # Notes
        o['note'] = "\r\n".join(notes)
        
        log.info("Creating order: %s" % pformat(o))
        rs = self.Register_sales.create(o)
        log.info("Order %s created" % rs.id)
        return True        
        
    def initialize(self):
        pass

    def finalize(self):
        pass


