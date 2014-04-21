import os
import sys
import base64
import logging

from VendHQ.api.lib.connection import Connection
from resources import ResourceAccessor

log = logging.getLogger("VendHQ.api")
log.setLevel(logging.DEBUG)

class ApiClient(object):
    BASE_URL = '/api/'
    
    def __init__(self, host, username, pwd):
        auth = base64.b64encode("%s:%s" % (username,pwd))
        self._connection = Connection(host, self.BASE_URL, auth)
        
        
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

        customer = self.Customers.create(cust_data)
        return customer

    def get_or_create_customer(self, billing_address):
        customer = self.get_customer_by_email(billing_address['email'])
        if not customer:
            self.create_customer(billing_address)
            customer = self.get_customer_by_email(billing_address['email'])

        return customer

    def get_tax(self, tax_rate):
        tax = None
        for t in self.Taxes.enumerate():
            if not tax: tax = t
            if tax_rate==tax.rate:
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
        sale_status = "SAVED" if not 'sale_status' in data.keys() else data['sale_status']
        loyality_x = 0 if not 'loyality_x' in data.keys() else data['loyality_x']

        register_id = self.get_register_id(register_name)
        customer = self.get_or_create_customer(order['billing_address'])

        loyality_x = max(loyality_x,0)

        o = {}
        notes = []

        o['register_id'] = register_id
        o['customer_id'] = customer['id']
        o['user_name']  = username
        o['status'] = sale_status if sale_status in ['SAVED','CLOSED','OPEN'] else "SAVED"
        total = float(order['total'])
        tax = float(order['total_tax'])
        taxobj = self.get_tax(tax/total if total>0 else 0)
        o['tax_name'] = taxobj.name

        # Get mapped items
        order_map = {
            "sale_date": "date_modified",
            "total_price": "total",
            "total_tax": "total_tax",
            "invoice_number": 'cartid',
            "invoice_sequence": 'cartid',
            "note": 'customer_message',
        }
        for k,v in order_map.items():
            o[k] = order[v]

        notes.append('Online order id: %s' % order['cartid'])
        if o['note'] and len(o['note'])>0: notes.append('Customer message: %s' % o['note'])

        o['register_sale_products'] = []

        # Update shipping costs if any as a new entry
        if order['shipping_address']['base_cost']>0:
            entry = {
                'sku':'SHIPPING', 
                'name':"Shipping", 
                "base_price":order['shipping_address']['base_cost'],
                "quantity":1,
                "tax": order['shipping_address']['cost_tax'],
                "total_tax":order['shipping_address']['cost_tax']
                }
            try:order['entries'].append(entry)
            except: pass

        if float(order['store_credit_amount'])>0:
            entry = {
                'sku':'vend-discount', 
                'name': 'Online store credit', 
                "base_price": -float(order['store_credit_amount']),
                "quantity":1,
                "tax": 0,
                "total_tax":0        
            }
            order['entries'].append(entry)

        # handle the entries
        entry_errors = []
        
        # entry map
        entry_map = {
            "quantity": "quantity",
            "price": 'base_price',
            "tax": 'tax',
            "tax_total": "total_tax"
        }

        line_item_discount = 0.0
        for entry in order['entries']:  
            register_sale_product = {}
            for k,v in entry_map.items():
                register_sale_product[k] = entry[v]
            register_sale_product['tax_id'] = taxobj.id
            
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
        reg_sale_payment['payment_date'] = order['updated']
        reg_sale_payment['amount'] = order['total']

        o['register_sale_payments'].append(reg_sale_payment)

        # Notes
        o['note'] = "\r\n".join(notes)

        rs = self.Register_sales.create(o)
        return True        
        

    