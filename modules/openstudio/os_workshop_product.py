# -*- coding: utf-8 -*-

from gluon import *


class WorkshopProduct:
    """
        Class for workshop products
    """
    def __init__(self, wspID):
        db = current.db

        self.wspID = int(wspID)
        self.workshop_product = db.workshops_products(self.wspID)
        self.workshop = db.workshops(self.workshop_product.workshops_id)

        self.name = self.workshop_product.Name
        self.workshop_name = self.workshop.Name
        self.description = self.workshop_product.Description
        self.wsID = self.workshop.id
        self.tax_rates_id = self.workshop_product.tax_rates_id

        self._set_price()


    def _set_price(self):
        if self.workshop_product.Price:
            self.price = self.workshop_product.Price
        else:
            self.price = 0


    def get_price(self):
        """
        :return: price for event ticket
        """
        TODAY_LOCAL = current.TODAY_LOCAL

        price = self.workshop_product.Price
        # Check regular early bird
        if self.workshop_product.PriceEarlybird:
            if (not self.workshop_product.EarlybirdUntil or
                TODAY_LOCAL <= self.workshop_product.EarlybirdUntil):
                # No early bird end or before end date; use early bird price
                price = self.workshop_product.PriceEarlybird

        return price


    def get_price_for_customer(self, cuID=None):
        """
        :param cuID: db.auth_user.id
        :return: product price for customer
        """
        from .os_customer import Customer
        TODAY_LOCAL = current.globalenv['TODAY_LOCAL']

        # get regular price | early bird price
        price = self.get_price()
        if not cuID:
            return price

        customer = Customer(cuID)
        # Check subscription
        if customer.has_subscription_on_date(self.workshop.Startdate, from_cache=False):
            if self.workshop_product.PriceSubscription:
                price = self.workshop_product.PriceSubscription

            # Check subscription early bird
            if ( self.workshop_product.PriceSubscriptionEarlybird
                 and ( not self.workshop_product.EarlybirdUntil or
                       TODAY_LOCAL <= self.workshop_product.EarlybirdUntil )):
                # No early bird end or before end date; use early bird price
                price = self.workshop_product.PriceSubscriptionEarlybird

        return price


    def get_price_for_customer_formatted(self, cuID):
        """
        :param cuID: db.auth_user.id
        :return: display for ticket price
        """
        CURRSYM = current.globalenv['CURRSYM']

        return SPAN(CURRSYM, ' ', format(self.get_price_for_customer(cuID), '.2f'))

      
    def get_tax_rate_percentage(self):
        """
            Returns the tax percentage for a workshop product, if any
        """
        db = current.db

        if self.workshop_product.tax_rates_id:
            tax_rate = db.tax_rates(self.workshop_product.tax_rates_id)
            tax_rate_percentage = tax_rate.Percentage
        else:
            tax_rate_percentage = None

        return tax_rate_percentage


    def get_activities(self):
        """
            Returns all activities for a workshop product
        """
        db = current.db

        if self.workshop_product.FullWorkshop:
            query = (db.workshops_activities.workshops_id == self.workshop.id)
            left = None
        else:
            query = (db.workshops_products_activities.workshops_products_id == self.wspID)
            left = [db.workshops_activities.on(
                db.workshops_products_activities.workshops_activities_id ==
                db.workshops_activities.id)]

        rows = db(query).select(db.workshops_activities.ALL,
                                left=left,
                                orderby=db.workshops_activities.Activitydate | \
                                        db.workshops_activities.Starttime)

        return rows


    def is_in_shoppingcart(self, cuID):
        """
        :param cuID: db.auth_user.id
        :return: True when event ticket is in cart for customer, False when not
        """
        db = current.db

        query = (db.customers_shoppingcart.auth_customer_id == cuID) & \
                (db.customers_shoppingcart.workshops_products_id == self.wspID)
        count = db(query).count()

        if count:
            return True
        else:
            return False


    def is_sold_to_customer(self, cuID):
        """
            :param cuID: db.auth_user.id
            :return: True when sold to customer, False when not
        """
        db = current.db

        query = (db.workshops_products_customers.auth_customer_id == cuID) & \
                (db.workshops_products_customers.workshops_products_id == self.wspID)
        count = db(query).count()

        if count:
            return True
        else:
            return False


    def is_sold_out(self):
        """
            This function checks if a product is sold out
            It's sold out when any of the activities it contains is completely full
        """

        def activity_list_customers_get_list_activity_query(wsaID):
            """
                Returns a query that returns a set of all customers in a specific
                workshop activity, without the full workshop customers
            """
            query = (db.workshops_activities.id ==
                     db.workshops_products_activities.workshops_activities_id) & \
                    (db.workshops_products_customers.workshops_products_id ==
                     db.workshops_products_activities.workshops_products_id) & \
                    (db.workshops_products_activities.workshops_activities_id ==
                     wsaID) & \
                    (db.workshops_products_customers.Waitinglist == False)

            return query

        def activity_count_reserved(wsaID):
            # count full workshop customers
            query = (db.workshops_products_customers.workshops_products_id == fwsID)
            count_full_ws = db(query).count()
            # count activity customers
            query = activity_list_customers_get_list_activity_query(wsaID)
            count_activity = db(query).count()

            return count_full_ws + count_activity

        from general_helpers import workshops_get_full_workshop_product_id

        db = current.db
        check = False

        fwsID = workshops_get_full_workshop_product_id(self.workshop.id)

        if self.wspID == fwsID:
            # Full workshops check, check if any activity is full
            query = (db.workshops_activities.workshops_id == self.workshop.id)
            rows = db(query).select(db.workshops_activities.ALL)
            for row in rows:
                reserved = activity_count_reserved(row.id)
                if reserved >= row.Spaces:
                    check = True
                    break
        else:
            # Product check, check if any a activity is full
            left = [db.workshops_activities.on(
                db.workshops_products_activities.workshops_activities_id ==
                db.workshops_activities.id
            )]
            query = (db.workshops_products_activities.workshops_products_id == self.wspID)
            rows = db(query).select(db.workshops_products_activities.ALL,
                                    db.workshops_activities.Spaces,
                                    left=left)
            for row in rows:
                wsaID = row.workshops_products_activities.workshops_activities_id
                reserved = activity_count_reserved(wsaID)
                if reserved >= row.workshops_activities.Spaces:
                    check = True
                    break

        return check


    def add_to_shoppingcart(self, cuID):
        """
            Add a workshop product to the shopping cart of a customer
        """
        db = current.db

        db.customers_shoppingcart.insert(
            auth_customer_id=cuID,
            workshops_products_id=self.wspID
        )


    def sell_to_customer(self, cuID, waitinglist=False, invoice=True):
        """
            Sells a workshop to a customer and creates an invoice
            Creates an invoice when a workshop product is sold
        """
        from .os_mail import OsMail
        from .os_workshop import Workshop
        from .os_invoice import Invoice

        db = current.db
        T = current.T

        info = False
        if self.workshop.AutoSendInfoMail:
            info = True

        wspID = self.wspID
        wspcID = db.workshops_products_customers.insert(
            auth_customer_id=cuID,
            workshops_products_id=wspID,
            Waitinglist=waitinglist,
            WorkshopInfo=info)

        ##
        # Add invoice
        ##
        if invoice and not waitinglist and self.price > 0:
            igpt = db.invoices_groups_product_types(ProductType='wsp')

            description = self.workshop_name + ' - ' + self.name

            iID = db.invoices.insert(
                invoices_groups_id=igpt.invoices_groups_id,
                Description=description,
                Status='sent'
            )

            # create object to set Invoice# and due date
            invoice = Invoice(iID)
            invoice.link_to_customer(cuID)
            invoice.item_add_workshop_product(wspcID)
            invoice.set_amounts()

        ##
        # Send info mail to customer if we have some practical info
        ##
        if self.workshop.AutoSendInfoMail and not waitinglist:
            osmail = OsMail()
            msgID = osmail.render_email_template('workshops_info_mail', workshops_products_customers_id=wspcID)
            osmail.send_and_archive(msgID, cuID)

        if not waitinglist:
            # Check if sold out
            if self.is_sold_out():
                # Cancel all unpaid orders with a sold out product for this workshop
                ws = Workshop(self.wsID)
                ws.cancel_orders_with_sold_out_products()

        return wspcID

