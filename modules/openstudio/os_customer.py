# -*- coding: utf-8 -*-

import datetime

from gluon import *


class Customer:
    """
        Class that contains functions for customer
    """
    def __init__(self, cuID):
        """
            Class init function which sets cuID
        """
        db = current.db

        self.cuID = cuID
        self.refresh_row()


    def refresh_row(self):
        db = current.db

        self.row = db.auth_user(self.cuID)


    def get_name(self):
        """
            Returns the name for a customer
        """
        return self.row.display_name


    def get_email_hash(self, hash_type='md5'):
        """

        """
        import hashlib

        md5 = hashlib.md5()
        md5.update(str.encode(self.row.email.lower()))

        return md5.hexdigest()


    def _get_subscriptions_on_date(self, date):
        """
            Returns subscription for a date
        """
        db = current.db
        cache = current.cache
        request = current.request
        web2pytest = current.globalenv['web2pytest']

        fields = [
            db.customers_subscriptions.id,
            db.customers_subscriptions.auth_customer_id,
            db.customers_subscriptions.Startdate,
            db.customers_subscriptions.Enddate,
            db.customers_subscriptions.payment_methods_id,
            db.customers_subscriptions.Note,
            db.school_subscriptions.id,
            db.school_subscriptions.Name,
            db.school_subscriptions.ReconciliationClasses,
            db.school_subscriptions.Unlimited,
            db.school_subscriptions.school_memberships_id,
            db.customers_subscriptions.CreditsRemaining,
        ]

        sql = """SELECT cs.id,
                        cs.auth_customer_id,
                        cs.Startdate,
                        cs.Enddate,
                        cs.payment_methods_id,
                        cs.Note,
                        ssu.id,
                        ssu.Name,
                        ssu.ReconciliationClasses,
                        ssu.Unlimited,
                        ssu.school_memberships_id,
(IFNULL(( SELECT SUM(csc.MutationAmount)
 FROM customers_subscriptions_credits csc
 WHERE csc.customers_subscriptions_id = cs.id AND
	   csc.MutationType = 'add'), 0) -
IFNULL(( SELECT SUM(csc.MutationAmount)
 FROM customers_subscriptions_credits csc
 WHERE csc.customers_subscriptions_id = cs.id AND
	   csc.MutationType = 'sub'), 0)) AS credits
FROM customers_subscriptions cs
LEFT JOIN
school_subscriptions ssu ON cs.school_subscriptions_id = ssu.id
WHERE cs.auth_customer_id = {cuID} AND
(cs.Startdate <= '{date}' AND (cs.Enddate >= '{date}' OR cs.Enddate IS NULL))
ORDER BY cs.Startdate""".format(cuID=self.cuID, date=date)

        rows = db.executesql(sql, fields=fields)

        #print db._lastsql[0]

        if len(rows) > 0:
            return_value = rows
        else:
            return_value = False

        return return_value


    def get_subscriptions_on_date(self, date, from_cache=True):
        """
            Get day rows with caching
        """
        web2pytest = current.globalenv['web2pytest']
        request = current.request

        # Don't cache when running tests
        if web2pytest.is_running_under_test(request, request.application) or not from_cache:
            rows = self._get_subscriptions_on_date(date)
        else:
            cache = current.cache
            DATE_FORMAT = current.DATE_FORMAT
            CACHE_LONG = current.globalenv['CACHE_LONG']
            cache_key = 'openstudio_customer_get_subscriptions_on_date_' + \
                        str(self.cuID) + '_' + \
                        date.strftime(DATE_FORMAT)
            rows = cache.ram(cache_key , lambda: self._get_subscriptions_on_date(date), time_expire=CACHE_LONG)

        return rows


    def get_school_subscriptions_ids_on_date(self, date, from_cache=True):
        """
        :param date: datetime.date
        :param from_cache: Boolean
        :return: list of subscription ids on date
        """
        rows = self.get_subscriptions_on_date(date, from_cache=from_cache)
        ids = []
        try:
            for row in rows:
                ids.append(row.school_subscriptions.id)
        except TypeError: # Bool is not iterable
            pass

        return ids


    def has_paid_a_subscription_registration_fee(self):
        """
        Check if this customer has ever paid a registration fee
        :return: True if so, else False
        """
        db = current.db

        query = ((db.customers_subscriptions.auth_customer_id == self.cuID) &
                 (db.customers_subscriptions.RegistrationFeePaid == True))

        has_paid_a_reg_fee = db(query).count()

        if has_paid_a_reg_fee:
            return True
        else:
            return False


    def has_subscription_on_date(self, date, from_cache=True):
        """
        :param date: datetime.date
        :return: Boolean
        """
        if self.get_subscriptions_on_date(date, from_cache=from_cache):
            return True
        else:
            return False


    def get_subscription_latest(self):
        """
            @return: Latest subscription for a customer
        """
        db = current.db
        os_gui = current.globalenv['os_gui']
        DATE_FORMAT = current.DATE_FORMAT

        fields = [
            db.auth_user.id,
            db.school_subscriptions.Name,
            db.customers_subscriptions.Startdate,
            db.customers_subscriptions.Enddate
        ]

        query = """
            SELECT au.id,
                   ssu.name,
                   cs.startdate,
                   cs.enddate
                   FROM auth_user au
            LEFT JOIN customers_subscriptions cs ON cs.auth_customer_id = au.id
            LEFT JOIN
                (SELECT auth_customer_id,
                        school_subscriptions_id,
                        max(startdate) as startdate,
                        enddate
                FROM customers_subscriptions GROUP BY auth_customer_id) chk
            ON au.id = chk.auth_customer_id
            LEFT JOIN
                (SELECT id, name FROM school_subscriptions) ssu
            ON ssu.id = cs.school_subscriptions_id
            WHERE cs.startdate = chk.startdate
                  AND au.id = {cuID} """.format(cuID=self.cuID)

        # show the latest subscription
        result = db.executesql(query, fields=fields)

        if len(result):
            record = result.first()
            try:
                return SPAN(os_gui.get_fa_icon('fa-clock-o'), ' ',
                            record.school_subscriptions.Name,
                            ' [',
                            record.customers_subscriptions.Startdate.strftime(DATE_FORMAT), ' - ',
                            record.customers_subscriptions.Enddate.strftime(DATE_FORMAT),
                            '] ',
                            _class='small_font',
                            _title='Latest subscription (past)')
            except AttributeError:
                return False

        else:
            return False


    def get_school_memberships_ids_on_date(self, date, from_cache=True):
        """
        :param date: datetime.date
        :param from_cache: Boolean
        :return: list of smembership ids on date
        """
        rows = self.get_memberships_on_date(date, from_cache=from_cache)
        ids = []
        try:
            for row in rows:
                print(row)
                ids.append(row.school_memberships_id)
        except TypeError: # Bool is not iterable
            pass

        return ids


    def _get_memberships_on_date(self, date):
        """
        :param date: datetime.date
        :return: db.customers_memberships rows for customer
        """
        db = current.db

        query = (db.customers_memberships.auth_customer_id == self.cuID) & \
                (db.customers_memberships.Startdate <= date) & \
                ((db.customers_memberships.Enddate >= date) |
                 (db.customers_memberships.Enddate == None))
        rows = db(query).select(db.customers_memberships.ALL,
                                orderby=db.customers_memberships.Startdate)

        return rows


    def get_memberships_on_date(self, date, from_cache=True):
        """
            Get day rows with caching
        """
        web2pytest = current.globalenv['web2pytest']
        request = current.request

        # Don't cache when running tests
        if web2pytest.is_running_under_test(request, request.application) or not from_cache:
            rows = self._get_memberships_on_date(date)
        else:
            cache = current.cache
            DATE_FORMAT = current.DATE_FORMAT
            CACHE_LONG = current.globalenv['CACHE_LONG']
            cache_key = 'openstudio_customer_get_memberships_on_date_' + \
                        str(self.cuID) + '_' + \
                        date.strftime(DATE_FORMAT)
            rows = cache.ram(cache_key, lambda: self._get_memberships_on_date(date), time_expire=CACHE_LONG)

        return rows


    def has_membership_on_date(self, date):
        """
        :param date: datetime.date
        :return: Boolean
        """
        if self.get_memberships_on_date(date):
            return True
        else:
            return False


    def has_given_membership_on_date(self, school_memberships_id, date):
        """
        :param school_memberships_id: db.school_memberships.id
        :param date: datetime.date
        :return: Boolean
        """
        ids = []
        for row in self.get_memberships_on_date(date):
            ids.append(int(row.school_memberships_id))

        if int(school_memberships_id) in ids:
            return True
        else:
            return False


    def _get_classcards(self, date):
        """
            Returns classcards for customer(cuID) on date
        """
        db = current.db
        cache = current.cache
        request = current.request
        web2pytest = current.globalenv['web2pytest']

        left = [ db.school_classcards.on(
            db.customers_classcards.school_classcards_id==\
            db.school_classcards.id)]
        query = (db.customers_classcards.auth_customer_id == self.cuID) & \
                (db.customers_classcards.Startdate <= date) & \
                ((db.customers_classcards.Enddate >= date) |
                 (db.customers_classcards.Enddate == None)) & \
                ((db.school_classcards.Classes > db.customers_classcards.ClassesTaken) |
                 (db.school_classcards.Classes == 0) |
                 (db.school_classcards.Unlimited == True))

        rows = db(query).select(db.customers_classcards.ALL,
                                db.school_classcards.Name,
                                db.school_classcards.Classes,
                                db.school_classcards.Unlimited,
                                db.school_classcards.school_memberships_id,
                                left=left,
                                orderby=db.customers_classcards.Enddate)

        if len(rows) > 0:
            return_value = rows
        else:
            return_value = False

        return return_value


    def get_classcards(self, date, from_cache=True):
        """
            Get day rows with caching
        """
        web2pytest = current.globalenv['web2pytest']
        request = current.request

        # Don't cache when running tests
        if web2pytest.is_running_under_test(request, request.application) or not from_cache:
            rows = self._get_classcards(date)
        else:
            cache = current.cache
            DATE_FORMAT = current.DATE_FORMAT
            CACHE_LONG = current.globalenv['CACHE_LONG']
            cache_key = 'openstudio_customer_get_classcards_' + \
                        str(self.cuID) + '_' + \
                        date.strftime(DATE_FORMAT)
            rows = cache.ram(cache_key , lambda: self._get_classcards(date), time_expire=CACHE_LONG)

        return rows


    def has_classcard_on_date(self, date):
        """
        :param date: datetime.date
        :return: Boolean
        """
        if self.get_classcards(date):
            return True
        else:
            return False


    def get_subscriptions_and_classcards_formatted(self,
                date,
                new_cards=True,
                show_subscriptions=True):
        """
            Returns a formatted list of subscriptions and classcards for
            a customer
        """
        from openstudio.os_customer_classcard import CustomerClasscard
        from openstudio.os_customer_subscriptions import CustomerSubscriptions

        DATE_FORMAT = current.DATE_FORMAT
        T = current.T
        os_gui = current.globalenv['os_gui']

        cuID = self.cuID
        subscription = ''
        has_subscription = False
        if show_subscriptions:
            subscriptions = self.get_subscriptions_on_date(date)
            if subscriptions:
                has_subscription = True
                subscription = DIV()
                for cs in subscriptions:
                    csID = cs.customers_subscriptions.id
                    # dates
                    subscr_dates = SPAN(' [', cs.customers_subscriptions.Startdate.strftime(DATE_FORMAT))
                    if cs.customers_subscriptions.Enddate:
                        subscr_dates.append(' - ')
                        subscr_dates.append(cs.customers_subscriptions.Enddate.strftime(DATE_FORMAT))
                    subscr_dates.append('] ')
                    # credits
                    #TODO: Add check for system setting if we should show the credits
                    subscr_credits = ''
                    if cs.customers_subscriptions.CreditsRemaining:
                        subscr_credits = SPAN(XML(' &bull; '), round(cs.customers_subscriptions.CreditsRemaining, 1), ' ',
                                              T('Credits'))
                    subscription.append(SPAN(cs.school_subscriptions.Name, subscr_dates, subscr_credits))

                    cs = CustomerSubscriptions(csID)
                    paused = cs.get_paused(date)
                    if paused:
                        pause_text = SPAN(' | ', paused, _class='bold')
                        subscription.append(pause_text)
                    subscription.append(BR())


        # get class card for customer
        has_classcard = False
        customer_classcards = self.get_classcards(date)
        if customer_classcards:
            has_classcard = True
            classcards = DIV()
            for card in customer_classcards:
                ccdID = card.customers_classcards.id
                classcard = CustomerClasscard(ccdID)
                remaining_classes = classcard.get_classes_remaining()
                if not remaining_classes:
                    continue

                try:
                    enddate = card.customers_classcards.Enddate.strftime(DATE_FORMAT)
                except AttributeError:
                    enddate = T('No expiry')

                classcards.append(
                    SPAN(card.school_classcards.Name, XML(' &bull; '),
                    T('expires'), ' ',
                    enddate, XML(' &bull; '),
                    remaining_classes)
                )

                if not card.school_classcards.Unlimited:
                    classcards.append(SPAN(' ', T("Classes remaining")))

                classcards.append(BR())

        else:
            classcards = T("")

        # format data for display
        subscr_cards = TABLE(_class='grey small_font')

        if not has_subscription and not has_classcard:
            if show_subscriptions:
                subscr_cards.append(DIV(T("No subscription or class card"),
                                         _class='red'))
                latest = self.get_subscription_latest()
                subscr_cards.append(latest if latest else '')

        else:
            if subscription and show_subscriptions:
                subscr_cards.append(TR(subscription))
            if classcards:
                subscr_cards.append(TR(classcards))

        return subscr_cards


    def get_trialclass_count(self):
        """
        :return: integer - count of trial classes
        """
        db = current.db

        query = (db.classes_attendance.auth_customer_id == self.cuID) & \
                (db.classes_attendance.AttendanceType == 1)

        return db(query).count()


    def get_had_trialclass(self):
        """
            Returns True if a customer has had a trialclass and false when not
        """
        count = self.get_trialclass_count()

        if count > 0:
            had_trial = True
        else:
            had_trial = False

        return had_trial


    def get_has_or_had_subscription(self):
        """
        Returns True if customer has or had a subscription
        """
        db = current.db

        query = (db.customers_subscriptions.auth_customer_id == self.cuID)
        if db(query).count():
            return True
        else:
            return False


    def get_has_or_had_classcard(self):
        """
        Returns True if customer has or had a subscription
        """
        db = current.db

        left = [
            db.school_classcards.on(
                db.customers_classcards.school_classcards_id ==
                db.school_classcards.id
            )
        ]

        query = (db.customers_classcards.auth_customer_id == self.cuID) & \
                (db.school_classcards.Trialcard == False)
        rows = db(query).select(db.customers_classcards.id)
        if len(rows):
            return True
        else:
            return False


    def get_has_or_had_subscription_or_classcard(self):
        """
        returns True when the customer has or has had a subscription or class card
        :return: boolean
        """
        if self.get_has_or_had_subscription() or self.get_has_or_had_classcard():
            return True
        else:
            return False


    def get_workshops_rows(self, upcoming=False):
        """
            Returns workshops for a customer
        """
        db = current.db
        TODAY_LOCAL = current.TODAY_LOCAL

        db_iicwspc = db.invoices_items_workshops_products_customers


        orderby = ~db.workshops.Startdate
        query = (db.workshops_products_customers.auth_customer_id == self.cuID)

        if upcoming:
            query &= (db.workshops.Startdate >= TODAY_LOCAL)
            orderby = db.workshops.Startdate

        rows = db(query).select(
            db.workshops_products_customers.ALL,
            db.workshops.ALL,
            db.workshops_products.Name,
            db.workshops_products.FullWorkshop,
            db.invoices.ALL,
            left=[db.workshops_products.on(
                db.workshops_products.id == \
                db.workshops_products_customers.workshops_products_id),
                db.workshops.on(db.workshops_products.workshops_id == \
                                db.workshops.id),
                db.invoices_items_workshops_products_customers.on(
                    db_iicwspc.workshops_products_customers_id ==
                    db.workshops_products_customers.id),
                db.invoices_items.on(
                    db_iicwspc.invoices_items_id ==
                    db.invoices_items.id
                ),
                db.invoices.on(db.invoices_items.invoices_id == db.invoices.id)
            ],
            orderby=~db.workshops.Startdate)

        return rows


    def get_invoices_rows(self,
                          public_group=True,
                          debit_only=False,
                          payments_only=False):
        """
            Returns invoices records for a customer as gluon.dal.rows object
        """
        from .tools import OsTools

        db = current.db

        left = [
            db.invoices_amounts.on(
                db.invoices_amounts.invoices_id == db.invoices.id),
            db.invoices_groups.on(
                db.invoices.invoices_groups_id == db.invoices_groups.id),
            db.invoices_customers.on(
                db.invoices_customers.invoices_id ==
                db.invoices.id
            )
        ]
        query = (db.invoices_customers.auth_customer_id == self.cuID) & \
                (db.invoices.Status != 'draft')
        if public_group:
                query &= (db.invoices_groups.PublicGroup == True)

        if payments_only:
            query &= ((db.invoices.TeacherPayment == True) |
                      (db.invoices.EmployeeClaim == True))

        if debit_only:
            query &= (
                ((db.invoices.TeacherPayment == False) |
                 (db.invoices.TeacherPayment == None)) &
                ((db.invoices.EmployeeClaim == False) |
                 (db.invoices.EmployeeClaim == None))
            )

        rows = db(query).select(db.invoices.ALL,
                                db.invoices_amounts.ALL,
                                left=left,
                                orderby=~db.invoices.DateCreated|~db.invoices.InvoiceID)

        return rows


    def get_orders_rows(self):
        """
            Returns orders for a customer
        """
        db = current.db

        query = (db.customers_orders.auth_customer_id == self.cuID)
        rows = db(query).select(
            db.customers_orders.ALL,
            db.customers_orders_amounts.ALL,
            db.invoices.ALL,
            db.invoices_amounts.ALL,
            left = [ db.customers_orders_amounts.on(db.customers_orders.id ==
                                                    db.customers_orders_amounts.customers_orders_id),
                     db.invoices_customers_orders.on(db.customers_orders.id ==
                                                     db.invoices_customers_orders.customers_orders_id),
                     db.invoices.on(db.invoices.id == db.invoices_customers_orders.invoices_id),
                     db.invoices_amounts.on(db.invoices_amounts.invoices_id == db.invoices.id)],
            orderby = ~db.customers_orders.id
        )

        return rows


    def get_orders_with_items_and_amounts(self):
        """
            Returns orders info for a customer with additional info
        """
        from openstudio.os_order import Order

        db = current.db

        orders = []
        rows = self.get_orders_rows()
        for i, row in enumerate(rows):
            repr_row = list(rows[i:i + 1].render())[0]

            order_obj = Order(row.customers_orders.id)
            order = {}
            order['row'] = row
            order['repr_row'] = repr_row
            order['items'] = order_obj.get_order_items_rows()

            orders.append(order)

        return orders


    def get_documents_rows(self):
        """
        :return: document rows for customer
        """
        db = current.db

        query = (db.customers_documents.auth_customer_id == self.cuID)
        return db(query).select(db.customers_documents.ALL)


    def has_recurring_reservation_for_class(self, clsID, date):
        """
        :param clsID: db.classes.id
        :param date: datetime.date
        :return: Boolean
        """
        db = current.db

        query = (db.classes_reservation.auth_customer_id == self.cuID) & \
                (db.classes_reservation.classes_id == clsID) & \
                (db.classes_reservation.Startdate <= date) & \
                ((db.classes_reservation.Enddate >= date) |
                 (db.classes_reservation.Enddate == None)) & \
                (db.classes_reservation.ResType == 'recurring')

        count = db(query).count()

        if count > 0:
            return True
        else:
            return False


    def get_reservations_rows(self, date=None, recurring_only=True):
        """
            Returns upcoming reservations for this customer
        """
        db = current.db

        left = [ db.classes.on(db.classes_reservation.classes_id == db.classes.id) ]

        query = (db.classes_reservation.auth_customer_id == self.cuID)
        if date:
            query &= (db.classes_reservation.Startdate <= date) & \
                     ((db.classes_reservation.Enddate >= date) |
                      (db.classes_reservation.Enddate == None))

        if recurring_only:
            query &= (db.classes_reservation.ResType == 'recurring')


        rows = db(query).select(db.classes_reservation.ALL,
                                db.classes.ALL,
                                left=left,
                                orderby=~db.classes_reservation.Startdate)

        return rows


    def get_classes_attendance_rows(self, limit=False, upcoming=False):
        """
            @param limit: (int) number of attendance records to return
            @return: gluon.dal.rows obj with classes attendance rows for
            customer
        """
        TODAY_LOCAL = current.TODAY_LOCAL
        db = current.db

        fields = [
            db.classes_attendance.id,
            db.classes_attendance.ClassDate,
            db.classes_attendance.AttendanceType,
            db.classes_attendance.customers_subscriptions_id,
            db.classes_attendance.customers_classcards_id,
            db.classes_attendance.auth_customer_id,
            db.classes_attendance.BookingStatus,
            db.classes.id,
            db.classes.school_locations_id,
            db.classes.school_classtypes_id,
            db.classes.school_levels_id,
            db.classes.Week_day,
            db.classes.Starttime,
            db.classes.Endtime,
            db.classes.Startdate,
            db.classes.Enddate,
            db.invoices.id,
            db.invoices.InvoiceID,
            db.invoices.Status,
            db.invoices.payment_methods_id,
            db.school_classcards.Name
        ]

        where_sql = ''
        if upcoming:
            where_sql = "AND clatt.ClassDate >= '{today}'".format(today=TODAY_LOCAL)
            limit = 20

        limit_sql = ''
        if limit:
            limit_sql = 'LIMIT ' + str(limit)

        orderby_sql = 'clatt.ClassDate DESC, cla.Starttime DESC'


        query = """
        SELECT clatt.id,
               clatt.ClassDate,
               clatt.AttendanceType,
               clatt.customers_subscriptions_id,
               clatt.customers_classcards_id,
               clatt.auth_customer_id,
               clatt.BookingStatus,
               cla.id,
               CASE WHEN cotc.school_locations_id IS NOT NULL
                    THEN cotc.school_locations_id
                    ELSE cla.school_locations_id
                    END AS school_locations_id,
               CASE WHEN cotc.school_classtypes_id IS NOT NULL
                    THEN cotc.school_classtypes_id
                    ELSE cla.school_classtypes_id
                    END AS school_classtypes_id,
               cla.school_levels_id,
               cla.Week_day,
               CASE WHEN cotc.Starttime IS NOT NULL
                    THEN cotc.Starttime
                    ELSE cla.Starttime
                    END AS Starttime,
               CASE WHEN cotc.Endtime IS NOT NULL
                    THEN cotc.Endtime
                    ELSE cla.Endtime
                    END AS Endtime,
               cla.Startdate,
               cla.Enddate,
               inv.id,
               inv.InvoiceID,
               inv.Status,
               inv.payment_methods_id,
               scd.Name
        FROM classes_attendance clatt
        LEFT JOIN classes cla on cla.id = clatt.classes_id
        LEFT JOIN customers_classcards cd ON cd.id = clatt.customers_classcards_id
        LEFT JOIN school_classcards scd ON scd.id = cd.school_classcards_id
        LEFT JOIN
            invoices_items_classes_attendance iica
            ON iica.classes_attendance_id = clatt.id
        LEFT JOIN
            invoices_items ii 
            ON iica.invoices_items_id = ii.id
        LEFT JOIN
            invoices inv ON ii.invoices_id = inv.id
        LEFT JOIN
            ( SELECT id,
                     classes_id,
                     ClassDate,
                     Status,
                     school_locations_id,
                     school_classtypes_id,
                     Starttime,
                     Endtime,
                     auth_teacher_id,
                     teacher_role,
                     auth_teacher_id2,
                     teacher_role2
              FROM classes_otc ) cotc
            ON clatt.classes_id = cotc.classes_id AND clatt.ClassDate = cotc.ClassDate
        WHERE clatt.auth_customer_id = {cuID}
        {where_sql}
        ORDER BY {orderby_sql}
        {limit_sql}
        """.format(orderby_sql = orderby_sql,
                   where_sql = where_sql,
                   limit_sql = limit_sql,
                   cuID = self.cuID)

        rows = db.executesql(query, fields=fields)

        # print db._lastsql
        # print rows

        return rows


    def get_shoppingcart_rows(self):
        """
            Get shopping cart rows for customer
        """
        db = current.db

        left = [
            db.workshops_products.on(db.workshops_products.id == db.customers_shoppingcart.workshops_products_id),
            db.workshops.on(db.workshops.id == db.workshops_products.workshops_id),
            db.school_classcards.on(db.school_classcards.id == db.customers_shoppingcart.school_classcards_id),
            db.classes.on(db.classes.id == db.customers_shoppingcart.classes_id)
        ]

        query = (db.customers_shoppingcart.auth_customer_id == self.cuID)
        rows = db(query).select(db.customers_shoppingcart.ALL,
                                db.workshops.Name,
                                db.workshops.Startdate,
                                db.workshops_products.id,
                                db.workshops_products.Name,
                                db.workshops_products.Price,
                                db.workshops_products.tax_rates_id,
                                db.school_classcards.id,
                                db.school_classcards.Name,
                                db.school_classcards.Price,
                                db.school_classcards.Classes,
                                db.school_classcards.Unlimited,
                                db.school_classcards.tax_rates_id,
                                db.classes.id,
                                db.classes.school_classtypes_id,
                                db.classes.school_locations_id,
                                db.classes.Starttime,
                                db.classes.Endtime,
                                left=left)

        return rows


    def shoppingcart_maintenance(self):
        """
            Do some housekeeping to keep things neat and tidy
        """
        messages = []
        message = self.shoppingcart_remove_past_classes()
        if message:
            messages.append(message)

        return messages


    def shoppingcart_remove_past_classes(self):
        """
            Check if a class is already past, if so, remove it from the shopping cart.
        """
        from .os_class import Class

        import pytz

        T = current.T
        db = current.db
        now = current.NOW_LOCAL
        TIMEZONE = current.TIMEZONE

        message = False

        query = (db.customers_shoppingcart.auth_customer_id == self.cuID) & \
                (db.customers_shoppingcart.classes_id != None)
        rows = db(query).select(db.customers_shoppingcart.id,
                                db.customers_shoppingcart.classes_id,
                                db.customers_shoppingcart.ClassDate)
        for row in rows:
            cls = Class(row.classes_id, row.ClassDate)

            if cls.is_past():
                del_query = (db.customers_shoppingcart.id == row.id)
                db(query).delete()

                message = T('One past class was removed from your shopping cart')

        return message


    def _get_payment_info_mandates_format(self, rows):
        """
        :param rows: gluon.dal.rows object of db.customers_payment_info_mandates
        :return:
        """
        from .os_gui import OsGui

        T = current.T
        auth = current.auth
        os_gui = OsGui()
        request = current.request

        delete_permission = (
            auth.has_membership(group_id='Admins') or
            auth.has_permission('delete', 'customers_payment_info_mandates')
        )

        edit_permission = (
            auth.has_membership(group_id='Admins') or
            auth.has_permission('update', 'customers_payment_info_mandates')
        )

        onclick = "return confirm('" + \
                     T('Do you really want to remove this mandate?') + "');"

        mandates = DIV()
        for row in rows.render():
            btn_delete = ''
            box_tools = DIV(_class='box-tools')
            if delete_permission and request.controller == 'customers':
                box_tools.append(
                    A(os_gui.get_fa_icon('fa-times'),
                      _href=URL('customers', 'bankaccount_mandate_delete',
                                vars={'cuID':self.cuID,
                                      'cpimID': row.id}),
                      _onclick=onclick,
                      _class='btn-box-tool text-red')
                )

            mandates.append(DIV(
                DIV(H3(T("Direct debit mandate"),
                       _class="box-title"),
                    box_tools,
                    _class="box-header"
                ),
                DIV(LABEL(T("Reference")),
                    DIV(row.MandateReference),
                    LABEL(T("Signed on")),
                    DIV(row.MandateSignatureDate),
                    LABEL(T("Mandate content")) if row.MandateText else '',
                    DIV(XML(row.MandateText) ),
                    _class="box-body"
                ),
                _class="box box-solid"
            ))

        return mandates


    def get_payment_info_mandates(self, formatted=False):
        """
        :param formatted: Boolean
        :return: gluon.dal.rows object if not formatted, else
        html
        """
        db = current.db

        payment_info = db.customers_payment_info(auth_customer_id = self.cuID)

        if not payment_info:
            if formatted:
                return ''
            else:
                return None

        query = (db.customers_payment_info_mandates.customers_payment_info_id == payment_info.id)
        rows = db(query).select(
            db.customers_payment_info_mandates.ALL,
            orderby=db.customers_payment_info_mandates.MandateSignatureDate
        )

        if formatted:
            return self._get_payment_info_mandates_format(rows)
        else:
            return rows


    def has_payment_info_mandate(self):
        """

        :return:
        """
        if self.get_payment_info_mandates():
            return True
        else:
            return False


    def get_mollie_mandates(self):
        """
            Returns mollie mandates
        """
        get_sys_property = current.globalenv['get_sys_property']

        from mollie.api.client import Client
        from mollie.api.error import Error as MollieError
        # init mollie
        mollie = Client()
        mollie_api_key = get_sys_property('mollie_website_profile')
        mollie.set_api_key(mollie_api_key)

        # check if we have a mollie customer id
        if self.row.mollie_customer_id:
            mollie_customer_id = self.row.mollie_customer_id
            #print mollie_customer_id
        else:
            # create one
            mollie_customer_id = self.register_mollie_customer(mollie)


        mandates = mollie.customer_mandates.with_parent_id(mollie_customer_id).list()

        return mandates


    def register_mollie_customer(self, mollie):
        """
            Registers this customer with mollie
        """
        if not self.row.mollie_customer_id:
            mollie_customer = mollie.customers.create({
                'name': self.row.display_name,
                'email': self.row.email
            })
            mollie_customer_id = mollie_customer['id']
            self.row.mollie_customer_id = mollie_customer_id
            self.row.update_record()

        return self.row.mollie_customer_id


    def get_mollie_mandates_formatted(self):
        """
            Returns mollie mandates
        """
        T = current.T

        get_sys_property = current.globalenv['get_sys_property']
        mollie_api_key = get_sys_property('mollie_website_profile')

        if not mollie_api_key:
            return T("Mollie not configured")

        mollie_mandates = self.get_mollie_mandates()
        if mollie_mandates['count'] == 0:
            return T("No active Mollie mandates")
        else:
            header = THEAD(TR(
                TH(T('Mandate')),
                TH(T('Created')),
                TH(T('Signature Date')),
                TH(T('Status')),
                TH(T('Method')),
            ))

            table = TABLE(header, _class="table table-striped table-hover")

            for m in mollie_mandates['_embedded']['mandates']:
                # 2018-06-14T10:35:01.0Z -- createdDatetime format

                table.append(TR(
                    TD(m['id']),
                    TD(m['createdAt']),
                    TD(m['signatureDate']),
                    TD(m['status']),
                    TD(m['method'])
                ))


        return table


    def get_accepted_documents(self):
        """
        :return: rows object with rows of accepted documents for this customer
        """
        db = current.db

        query = (db.log_customers_accepted_documents.auth_customer_id == self.cuID)
        rows = db(query).select(db.log_customers_accepted_documents.ALL,
                                orderby=db.log_customers_accepted_documents.CreatedOn)
        return rows


    def log_document_acceptance(self,
                                document_name,
                                document_description='',
                                document_version='',
                                document_url='',
                                document_content=''):
        """
            :return:
        """
        db = current.db

        version = db.sys_properties(Property='Version').PropertyValue
        release = db.sys_properties(Property='VersionRelease').PropertyValue

        db.log_customers_accepted_documents.insert(
            auth_customer_id = self.cuID,
            DocumentName = document_name,
            DocumentDescription = document_description,
            DocumentVersion = document_version,
            DocumentURL = document_url,
            DocumentContent = document_content,
            OpenStudioVersion = '.'.join([version, release])
        )


    def log_subscription_terms_acceptance(self, school_subscriptions_id):
        """
        :param school_subscriptions_id: db.school_subscriptions.id
        :return: None
        """
        from .os_school_subscription import SchoolSubscription
        from .tools import OsTools

        T = current.T
        os_tools = OsTools()
        ssu = SchoolSubscription(school_subscriptions_id, set_db_info=True)

        terms = [
            os_tools.get_sys_property('shop_subscriptions_terms') or '',  # general terms
            ssu.Terms or ''  # Subscription specific terms
        ]
        full_terms = '\n'.join(terms)

        self.log_document_acceptance(
            document_name=T("Subscription terms"),
            document_description=T("Terms for all subscriptions and subscription specific terms"),
            document_content=full_terms
        )


    def log_membership_terms_acceptance(self, school_memberships_id):
        """
        :param school_memberships_id: db.school_memberships.id
        :return: None
        """
        from .os_school_membership import SchoolMembership
        from .tools import OsTools

        T = current.T
        os_tools = OsTools()
        sm = SchoolMembership(school_memberships_id)

        terms = [
            os_tools.get_sys_property('shop_memberships_terms') or '',  # general terms
            sm.row.Terms or ''  # membership specific terms
        ]
        full_terms = '\n'.join(terms)

        self.log_document_acceptance(
            document_name=T("Membership terms"),
            document_description=T("Terms for all memberships and membership specific terms"),
            document_content=full_terms
        )


    def set_barcode_id(self):
        """
        Set barcode id field for customer
        """
        from .os_cache_manager import OsCacheManager

        if self.row.barcode_id is None or self.row.barcode_id == '':
            self.row.barcode_id = str(self.cuID).zfill(13)
            self.row.update_record()

            ocm = OsCacheManager()
            ocm.clear_customers()


    def set_barcode(self):
        """
            Create barcode file for this customer
        """
        import barcode
        from barcode.writer import ImageWriter
        from io import BytesIO

        db = current.db
        stream = BytesIO()

        CODE39 = barcode.get_barcode_class('code39')
        code39_barcode = CODE39(
            str(self.row.barcode_id).zfill(13),
            writer=ImageWriter(),
            add_checksum=False
        )

        '''
        Default options (here for future reference);
        
        default_writer_options = {
            'module_width': 0.2,
            'module_height': 15.0,
            'quiet_zone': 6.5,
            'font_size': 10,
            'text_distance': 5.0,
            'background': 'white',
            'foreground': 'black',
            'write_text': True,
            'text': '',
        }
        '''

        code39_barcode.default_writer_options['module_width'] = 0.2
        code39_barcode.default_writer_options['module_height'] = 12
        code39_barcode.default_writer_options['font_size'] = 10
        code39_barcode.default_writer_options['text_distance'] = 0.5

        code39_barcode.write(stream)
        stream.seek(0)

        self.row.update_record(
            barcode = db.auth_user.barcode.store(
                stream,
                filename=str(self.cuID) + '_barcode.png'
            )
        )


    def get_barcode_label(self):
        """
            Print friendly display of a barcode label
        """
        get_sys_property = current.globalenv['get_sys_property']
        response = current.response

        template = get_sys_property('branding_default_template_barcode_label_customer') or \
                  'barcode_label_customer/default.html'
        template_file = 'templates/' + template

        if not self.row.barcode_id:
            self.set_barcode_id()

        if not self.row.barcode:
            self.set_barcode()
        barcode_image_url = URL('default', 'download', args=self.row.barcode, host=True, scheme=True)

        html = response.render(template_file,
                               dict(customer=self.row,
                                    barcode_image_url=barcode_image_url,
                                    logo=self._get_barcode_label_get_logo()))

        return html


    def _get_barcode_label_get_logo(var=None):
        """
            Returns logo for template
        """
        import os

        request = current.request

        branding_logo = os.path.join(request.folder,
                                     'static',
                                     'plugin_os-branding',
                                     'logos',
                                     'branding_logo_invoices.png')
        if os.path.isfile(branding_logo):
            abs_url = URL('static', 'plugin_os-branding/logos/branding_logo_invoices.png',
                          scheme=True,
                          host=True)
            logo_img = IMG(_src=abs_url)
        else:
            logo_img = ''

        return logo_img


    def get_notes(self, note_type=None):
        """

        :return:
        """
        db = current.db

        query = (db.customers_notes.auth_customer_id == self.cuID)

        if note_type == 'backoffice':
            query &= (db.customers_notes.BackofficeNote == True)

        if note_type == 'teachers':
            query &= (db.customers_notes.TeacherNote == True)

        rows = db(query).select(
            db.customers_notes.ALL,
            orderby=~db.customers_notes.NoteDate | \
                    ~db.customers_notes.NoteTime
        )

        return rows


    def get_notes_formatted(self, note_type, permission_edit=False, permission_delete=False):
        """
        :param note_type: ['backoffice', 'teachers']
        :return: HTML formatted notes using AdminLTE chat layout
        """
        from openstudio.os_gui import OsGui
        os_gui = OsGui()

        T = current.T
        delete_onclick = "return confirm('" + T('Are you sure you want to delete this note?') + "');"

        rows = self.get_notes(note_type=note_type)

        notes = DIV(_class='direct-chat-messages direct-chat-messages-high')
        for i, row in enumerate(rows):
            repr_row = list(rows[i:i + 1].render())[0]

            edit = ''
            delete = ''

            if permission_delete:
                delete = A(T('Delete'),
                           _href=URL('customers', 'note_delete', vars={'cnID': row.id,
                                                                       'cuID': self.cuID}),
                           _onclick=delete_onclick,
                           _class='text-red')

            if permission_edit:
                edit = A(T('Edit'),
                           _href=URL('customers', 'notes', vars={'cnID': row.id,
                                                                 'cuID': self.cuID,
                                                                 'note_type': note_type}),
                           )

            status = ""
            if row.Processed:
                status = SPAN(
                    os_gui.get_fa_icon('fa-check'), ' ',
                    T("Processed"),
                    _class="direct-chat-scope pull-right text-green"
                )

            note = DIV(
                DIV(SPAN(repr_row.auth_user_id,
                         _class="direct-chat-name pull-left"),
                    SPAN(delete,
                         _class="direct-chat-scope pull-right"),
                    SPAN(edit,
                         _class="direct-chat-scope pull-right"),
                    status,
                    SPAN(repr_row.NoteDate, ' ', repr_row.NoteTime, ' ',
                         _class="direct-chat-timestamp pull-right"),
                    _class="direct-chat-info clearfix"
                    ),
                IMG(_src=URL('static', 'images/person_inverted_small.png'), _class="direct-chat-img"),
                DIV(XML(repr_row.Note.replace('\n', '<br>')), _class="direct-chat-text"),
                _class="direct-chat-msg"
            )

            notes.append(note)

        return notes
