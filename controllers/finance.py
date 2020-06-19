# -*- coding: utf-8 -*-

from general_helpers import get_last_day_month
from general_helpers import get_payment_batches_statuses
from general_helpers import get_paused_subscriptions
from general_helpers import max_string_length

from openstudio.os_invoice import Invoice
from openstudio.os_invoices import Invoices
from openstudio.os_school_subscription import SchoolSubscription

import csv
import io


@auth.requires(auth.has_membership(group_id='Admins') or \
                auth.has_permission('read', 'payment_batches'))
def batches_index():
    """
        Lists payment batches
    """
    response.title = T("Batches")
    response.view = 'general/only_content.html'

    pbtype = request.vars['export']

    if pbtype == 'collection':
        query = (db.payment_batches.BatchType == 'collection')
        response.subtitle = T("Collection")
        add_url = URL('add_collection_batch_type', vars=request.vars)
    elif pbtype == 'payment':
        query = (db.payment_batches.BatchType == 'payment')
        response.subtitle = T("Payment")

        add_url = URL('add_payment_batch_type', vars=request.vars)
    else:
        query = (db.payment_batches.id > 0)
        response.subtitle = T("Collection & Payment")

    if session.show_location:
        db.payment_batches.school_locations_id.readable=True
        db.payment_batches.school_locations_id.writable=True

    db.payment_batches.Created_at.readable = True
    db.payment_batches.Description.readable = False
    db.payment_batches.IncludeZero.readable = False
    db.payment_batches.Note.readable = False

    maxtextlengths = {'payment_batches.Name' : 60}
    headers = { 'payment_batches.id':T("Batch") }

    links = [ lambda row: os_gui.get_button('list',
                                URL('batch_content', vars={'pbID':row.id}),
                                tooltip=T("View batch"),
                                title=T("View") ) ]

    delete_permission = auth.has_membership(group_id='Admins') or \
                        auth.has_permission('delete', 'payment_batches')

    grid = SQLFORM.grid(query, links=links,
        headers=headers,
        create=False,
        editable=False,
        details=False,
        searchable=False,
        deletable=delete_permission,
        csv=False,
        maxtextlengths=maxtextlengths,
        orderby=~db.payment_batches.Created_at,
        field_id=db.payment_batches.id,
        ui = grid_ui)
    grid.element('.web2py_counter', replace=None) # remove the counter
    grid.elements('span[title=Delete]', replace=None) # remove text from delete button

    add = os_gui.get_button('add', add_url, T("Add a batch"))
    content = grid

    return dict(content=content, add=add)


@auth.requires(auth.has_membership(group_id='Admins') or \
               auth.has_permission('read', 'payment_batches'))
def add_collection_batch_type():
    """
        Page to ask what kind of batch the user wants to add
        Can be invoices or category
    """
    export = request.vars['export']

    response.title = T("New batch")
    response.subtitle = ''
    response.view = 'general/only_content.html'

    return_url = URL('batches_index', vars={'export':export})

    question = T("What kind of batch would you like to create?")
    invoices = LI(A(
        B(T('Invoices')),
        _href=URL('batch_add', vars={'export':export,
                                     'what':'invoices'})), BR(),
        T("Create a batch containing all invoices with status 'sent' and payment method 'direct debit'."))
    category = LI(A(
        B(T('Direct debit extra')),
        _href=URL('batch_add', vars={'export':export,
                                     'what':'category'})), BR(),
        T("Create a batch containing items from a direct debit extra category."))
    back = os_gui.get_button('back', return_url)
    ul = UL(invoices, category)
    content = DIV(H3(question), ul)

    return dict(content=content,
                back=back)


@auth.requires(auth.has_membership(group_id='Admins') or \
               auth.has_permission('read', 'payment_batches'))
def add_payment_batch_type():
    """
        Page to ask what kind of batch the user wants to add
        Can be invoices or category
    """
    export = request.vars['export']

    response.title = T("New batch")
    response.subtitle = ''
    response.view = 'general/only_content.html'

    return_url = URL('batches_index', vars={'export':export})

    question = T("What kind of batch would you like to create?")

    teacher_payments = LI(A(
        B(T('Teacher payments')),
        _href=URL('batch_add', vars={'export': export,
                                     'what':'teacher_payments'})), BR(),
        T("Create a batch containing all teacher payment invoices with status 'sent'."))
    employee_expenses = LI(A(
        B(T('Employee expenses')),
        _href=URL('batch_add', vars={'export': export,
                                     'what':'employee_expenses'})), BR(),
        T("Create a batch containing all employee claim invoices with status 'sent'."))
    category = LI(A(
        B(T('Direct debit extra')),
        _href=URL('batch_add', vars={'export':export,
                                     'what':'category'})), BR(),
        T("Create a batch containing items from a direct debit extra category."))

    cancel = os_gui.get_button('noicon',
        return_url,
        title=T("Cancel"),
        _class='btn btn-default',
        btn_size='')

    back = os_gui.get_button('back', return_url)
    ul = UL(
        teacher_payments,
        employee_expenses,
        category
    )
    content = DIV(H3(question), ul)

    return dict(content=content,
                back=back)


@auth.requires_login()
def batch_add():
    """
        This function shows an add page for a batch
        request.vars['export'] can be 'collection' or 'payment'
        This variable sets the BatchType field with a default value
    """
    response.title = T("New batch")
    response.view = 'general/only_content.html'
    what = request.vars['what']

    batchtype = request.vars['export']
    if batchtype == 'collection':
        response.subtitle = SPAN(T('Collection'), ' - ')
        if what == 'invoices':
            db.payment_batches.BatchTypeDescription.default = 'invoices'
            db.payment_batches.ColYear.requires = ''
            db.payment_batches.ColMonth.requires = ''
            db.payment_batches.payment_categories_id.requires = None
            response.subtitle.append(T('Invoices batch'))

        elif what == 'category':
            db.payment_batches.BatchTypeDescription.default = 'category'
            response.subtitle.append(T('Direct debit category batch'))

        return_url = URL('add_collection_batch_type', vars=request.vars)

    elif batchtype == 'payment':
        if what == 'teacher_payments':
            db.payment_batches.BatchTypeDescription.default = 'teacher_payments'
            db.payment_batches.ColYear.requires = ''
            db.payment_batches.ColMonth.requires = ''
            db.payment_batches.payment_categories_id.requires = None
            response.subtitle = SPAN(T('Teacher payments'))
        elif what == 'employee_expenses':
            db.payment_batches.BatchTypeDescription.default = 'employee_expenses'
            db.payment_batches.ColYear.requires = ''
            db.payment_batches.ColMonth.requires = ''
            db.payment_batches.payment_categories_id.requires = None
            response.subtitle = SPAN(T('Employee expenses'))
        elif what == 'category':
            response.subtitle = SPAN(T('Payment'))
            db.payment_batches.BatchTypeDescription.default = 'category'

        return_url = URL('add_payment_batch_type', vars=request.vars)

    if session.show_location:
        db.payment_batches.school_locations_id.readable=True
        db.payment_batches.school_locations_id.writable=True

    db.payment_batches.BatchType.default = batchtype

    db.payment_batches.Status.readable=False
    db.payment_batches.Status.writable=False

    crud.messages.submit_button = T("Save")
    crud.messages.record_created = T("Added batch")
    crud.settings.formstyle = 'bootstrap3_stacked'
    crud.settings.create_onaccept = [ generate_batch_items ]
    crud.settings.create_next = '/finance/batch_content?pbID=[id]'
    form = crud.create(db.payment_batches)

    form_id = "MainForm"
    form_element = form.element('form')
    form['_id'] = form_id

    elements = form.elements('input, select, textarea')
    for element in elements:
        element['_form'] = form_id

    submit = form.element('input[type=submit]')

    locations = ''
    if session.show_location:
        locations = DIV(LABEL(form.custom.label.school_locations_id,
                         _class='control-label'),
                         form.custom.widget.school_locations_id,
                         _class='form-group')

    categories = ''
    if what == 'category':
        categories = DIV(LABEL(form.custom.label.payment_categories_id,
                         _class='control-label'),
                         form.custom.widget.payment_categories_id,
                         _class='form-group')

    if what == 'category':
        col_month = DIV(LABEL(form.custom.label.ColMonth,
                         _class='control-label'),
                   form.custom.widget.ColMonth,
                   _class='form-group')
        col_year = DIV(LABEL(form.custom.label.ColYear,
                         _class='control-label'),
                   form.custom.widget.ColYear,
                   _class='form-group')
    else:
        col_month  = ''
        col_year = ''

    form = DIV(XML('<form action="#" enctype="multipart/form-data" id="MainForm" method="post">'),
               DIV(LABEL(form.custom.label.Name,
                         _class='control-label'),
                         form.custom.widget.Name,
                         _class='form-group'
               ),
               categories,
               col_month,
               col_year,
               DIV(LABEL(form.custom.label.Exdate,
                         _class='control-label'),
                         form.custom.widget.Exdate,
                         _class='form-group'
               ),
               locations,
               DIV(LABEL(form.custom.label.Note,
                         _class='control-label'),
                         form.custom.widget.Note,
                         _class='form-group'
               ),
               DIV(LABEL(form.custom.label.IncludeZero,
                         _class='control-label'),
                         form.custom.widget.IncludeZero,
                         _class='form-group'
               ),
               form.custom.end,
               _id='payment_batches_add')

    back = os_gui.get_button('back', return_url)

    return dict(content=form, back=back, save=submit)


@auth.requires(auth.has_membership(group_id='Admins') or \
                auth.has_permission('read', 'payment_batches'))
def batch_content():
    """
        This function shows the content for a batch
        request.vars['pbID'] is expected to be the pbID
    """
    if 'pbID' in request.vars:
        pbID = request.vars['pbID']
        session.finance_batch_content_pbID = pbID
    elif session.finance_batch_content_pbID:
        pbID = session.finance_batch_content_pbID

    session.invoices_edit_back = 'finance_batch_content'
    session.customers_back = 'finance_batch_content'


    pb = db.payment_batches(pbID)
    response.title = T("Batch")
    response.subtitle = pb.Name
    response.view = 'general/only_content_no_box.html'

    return_url = URL('batches_index', vars={'export':pb.BatchType})

    ## batch info begin
    # info
    if pb.payment_categories_id is None:
        category = T("")
        description = pb.Description
    else:
        category = db.payment_categories(pb.payment_categories_id).Name
        description = T('')

    if pb.BatchType == 'collection':
        batchtype = T('Collection')
    elif pb.BatchType == 'payment':
        batchtype = T('Payment')

    if pb.IncludeZero:
        zero = T("Yes")
    else:
        zero = T("No")

    info_table = TABLE(TR(TD(LABEL(T("Name"))),
                          TD(pb.Name)),
                       TR(TD(LABEL(T("Batch type"))),
                          TD(batchtype)),
                       TR(TD(LABEL(T("Batch type description"))),
                          TD(represent_payment_batchtypes(pb.BatchTypeDescription, pb))),
                       TR(TD(LABEL(T("Category"))),
                          TD(category)),
                       TR(TD(LABEL(T('Default description'))),
                          TD(description or '')),
                       TR(TD(LABEL(T('Execution date'))),
                          TD(pb.Exdate.strftime(DATE_FORMAT))),
                       TR(TD(LABEL(T('Include 0'))),
                          TD(zero)),
                       _class='table')

    if session.show_location:
        if pb.school_locations_id:
            location_name = db.school_locations(pb.school_locations_id).Name
        else:
            location_name = T('All')


        location = TR(TD(LABEL(T("Location"))),
                      TD(location_name))
        info_table.append(location)

    # totals
    query = (db.payment_batches_items.payment_batches_id == pbID)
    total_items = str(db(query).count())

    sum_items = db.payment_batches_items.Amount.sum()
    total_amount = db(query).select(sum_items).first()[sum_items]
    try:
        total_amount = format(total_amount, '.2f')
    except:
        total_amount = 0

    totals_table = TABLE(TR(TD(LABEL(T("Lines"))),
                            TD(total_items)),
                       TR(TD(LABEL(T('Amount'))),
                          TD(CURRSYM, ' ',total_amount)),
                       _class='table')

    # exports
    db.auth_user._format = '%(display_name)s'
    query = (db.payment_batches_exports.payment_batches_id == pbID)
    rows = db(query).select(db.payment_batches_exports.ALL,
                            orderby=~db.payment_batches_exports.Created_at)
    exports = DIV(_class='payment_batches_padding')
    for row in rows.render():
        export_options = ''
        if row.FirstCustomers:
            export_options = ' - ' + T('FRST')
        if row.RecurringCustomers:
            export_options = ' - ' + T('RCUR')
        exports.append(SPAN(row.Created_at,
                            export_options,
                            SPAN(' - ', row.auth_user_id, _class='grey'))),
        exports.append(BR())

    info = DIV(DIV(os_gui.get_box_table(T('Batch info'),
                                    info_table),
                   _class='col-md-3 no_padding-left'),
               DIV(os_gui.get_box_table(T('Totals'),
                                    totals_table),
                   _class='col-md-3'),
               DIV(os_gui.get_box(T('Note'),
                                    DIV(pb.Note,
                                        _class='payment_batches_padding'),),
                   _class='col-md-3'),
               DIV(os_gui.get_box(T('Exports'),
                                    exports),
                   _class='col-md-3'))

    # batch info end

    # batch items begin
    table = TABLE(
        TR(TH(T('Line')),
           TH(T('CuID'), _title=T("Customers ID")),
           TH(T('AccountHolder')),
           TH(T('AccountNR')),
           TH(T('BIC')),
           TH(T('Mandate date')),
           TH(T('Mandate ref')),
           TH(T('Currency')),
           TH(T('Amount')),
           TH(T('Description')),
           TH(T('Execution date')),
           TH(T('Invoice')),
           _class='header'),
        _class='table table-hover table-condensed small_font')

    bi = get_batch_items(pbID, display=True)
    for item in bi:
        # remove ID
        invoice_id = item['invoice_id']
        if invoice_id:
            invoice_link = A(T("Invoice"),
                             _href=URL('invoices', 'edit',
                                       vars={'iID':invoice_id}))
        else:
            invoice_link = ''
        pbiID = item['id']

        cuID = item['cuID']
        cu_link = A(cuID,
                    _href=URL('customers', 'edit', args=cuID),
                    _title=T('Customers ID'))

        # fill the table

        # tr = TR(*item)
        tr = TR(
            TD(item['line']),
            TD(cu_link),
            TD(item['account_holder']),
            TD(item['account_number']),
            TD(item['bic']),
            TD(item['mandate_signature_date']),
            TD(item['mandate_reference']),
            TD(item['currency']),
            TD(item['amount']),
            TD(item['description']),
            TD(item['execution_date']),
            TD(item['invoice_InvoiceID']),
        )
        table.append(tr)

    # batch items end

    # status buttons begin
    status_buttons = content_get_status_buttons(pbID)

    # status buttons end
    content = DIV(info,
                  DIV(os_gui.get_box_table(T('Batch items'), table),
                      _class="col-md-12"),
                  _class='row')

    edit = os_gui.get_button('edit',
                             URL('batch_edit', vars=request.vars),
                             title='Edit')
    export = batch_content_get_export(pbID)

    back = os_gui.get_button('back', return_url)
    tools = SPAN(back, status_buttons, ' ', edit, export)

    return dict(content=content, back=tools)


def batch_content_get_export(pbID):
    """
    :return: export button for batch content page
    """
    export = os_gui.get_button('download',
                               URL('export_csv', vars={'pbID':pbID}),
                               title=T('Export'))

    dd_button = XML("""<button type="button" class="btn btn-default dropdown-toggle btn-sm" data-toggle="dropdown">
                       <span class="caret"></span></button>""")
    dd_ul = UL(_class='dropdown-menu dropdown-menu-right', _role='menu')

    links = [
        A(os_gui.get_fa_icon('fa-star-o'), T('First'), _href=URL('export_csv', vars={'pbID':pbID,
                                                                                     'first':True})),
        A(os_gui.get_fa_icon('fa-repeat'), T('Recurring'), _href=URL('export_csv', vars={'pbID':pbID,
                                                                                         'recurring':True}))
    ]

    for link in links:
        dd_ul.append(LI(link))

    return DIV(export, dd_button, dd_ul, _class='btn-group')


def content_items_get_invoices_link(invoices, item):
    """
        Returns add invoice link if none is found,
        otherwise returns link to invoice
    """
    pbiID = item[0]
    cuID  = item[2]
    csID  = item[3]

    link = ''

    for invoice_pbiID, iID, InvoiceID in invoices:
        if invoice_pbiID == pbiID:
            link = A('#' + InvoiceID,
                     _href=URL('invoices', 'edit', vars={'iID':iID}),
                     _class='small_font')
            break

    return link


def content_get_status_buttons(pbID):
    """
        Retuns the status buttons for batch content
    """
    pb = db.payment_batches(pbID)
    status = pb.Status

    onclick_sent_to_bank = "return confirm('" + \
     T("Set batch status to sent to bank?") + ' ' + \
     T('This cannot be undone.') + \
     "');"


    default_class = 'btn btn-sm btn-default'
    _class_sen = default_class
    _class_app = default_class
    _class_awa = default_class
    _class_rej = default_class

    if status == 'sent_to_bank':
        _class_sen = 'btn btn-sm btn-primary bold'
    elif status == 'approved':
        _class_app = 'btn btn-sm btn-success bold'
    if status == 'awaiting_approval':
        _class_awa = 'btn btn-sm btn-warning bold'
    if status == 'rejected':
        _class_rej = 'btn btn-sm btn-danger bold'

    btn_sent = A(T('Sent to Bank'),
                 _href=URL('batch_content_set_status',
                           vars={'pbID':pbID,
                                 'status':'sent_to_bank'}),
                 _onclick=onclick_sent_to_bank,
                 _class=_class_sen)

    btn_app = A(T("Approved"),
                _href=URL('batch_content_set_status',
                          vars={'pbID':pbID,
                                'status':'approved'}),
                _class=_class_app)

    btn_awa = A(T("Awaiting Approval"),
                _href=URL('batch_content_set_status',
                          vars={'pbID':pbID,
                                'status':'awaiting_approval'}),
                _class=_class_awa)

    btn_rej = A(T("Rejected"),
                _href=URL('batch_content_set_status',
                          vars={'pbID':pbID,
                                'status':'rejected'}),
                _class=_class_rej)

    if status == 'sent_to_bank':
        buttons = os_gui.get_label('primary', T('Sent to Bank'))
    else:
        buttons = DIV(btn_sent, btn_app, btn_awa, btn_rej,
                      _class='btn-group payment_batches_status')

    return SPAN(SPAN(T("Batch status"), _class='bold grey'), ' ',
               buttons,
               _class='right')


@auth.requires(auth.has_membership(group_id='Admins') or \
               auth.has_permission('update', 'payment_batches'))
def batch_content_set_status():
    """
        Sets the status for a batch
    """
    pbID = request.vars['pbID']
    status = request.vars['status']

    known_status = False

    for s, sd in get_payment_batches_statuses():
        if status == s:
            known_status = True

    pb = db.payment_batches(pbID)
    current_status = pb.Status

    if known_status:
        # add check for invoices batch
        if ( status == 'sent_to_bank' and
             not current_status == 'sent_to_bank' and
            (pb.BatchTypeDescription == 'invoices' or
             pb.BatchTypeDescription == 'teacher_payments')):
            # add payments
            content_add_payments(pb)

        pb.Status = status
        pb.update_record()
        session.flash = T('Status updated')
    else:
        session.flash = T('Invalid status requested')

    redirect(URL('batch_content', vars={'pbID':pbID}))


def content_add_payments(pb):
    """
        Add payments for invoices in payment batch
    """
    left = [ db.invoices_payments.on(db.payment_batches_items.invoices_id ==
                                     db.invoices_payments.id) ]

    query = (db.payment_batches_items.payment_batches_id == pb.id) & \
            (db.payment_batches_items.invoices_id != None)

    rows = db(query).select(db.payment_batches_items.ALL,
                            db.invoices_payments.ALL,
                            left=left)

    payment_methods_id = 3
    note = T("Direct debit batch: ")
    if pb.BatchTypeDescription == 'teacher_payments':
        payment_methods_id = 2
        note = T("Payment batch: ")

    for row in rows:
        iID = row.payment_batches_items.invoices_id
        amount = row.payment_batches_items.Amount

        db.invoices_payments.insert(
            invoices_id        = iID,
            Amount             = amount,
            PaymentDate        = pb.Exdate,
            payment_methods_id = payment_methods_id,
            Note               = note + pb.Name
        )

        invoice = Invoice(iID)
        invoice.set_status('paid')


@auth.requires_login()
def batch_edit():
    """
        Shows edit page for a batch
        request.vars['pbID'] is expected to be payment_batches_id
    """
    response.title = T("Edit batch")
    pbID = request.vars['pbID']
    pb = db.payment_batches(pbID)
    response.subtitle = pb.Name
    response.view = 'general/only_content.html'

    db.payment_batches.Status.readable=False
    db.payment_batches.Status.writable=False
    db.payment_batches.payment_categories_id.writable=False
    db.payment_batches.payment_categories_id.readable=False
    db.payment_batches.Description.readable=False
    db.payment_batches.Description.writable=False
    db.payment_batches.BatchTypeDescription.readable=False
    db.payment_batches.BatchTypeDescription.writable=False
    db.payment_batches.Exdate.readable=False
    db.payment_batches.Exdate.writable=False
    db.payment_batches.ColYear.readable=False
    db.payment_batches.ColYear.writable=False
    db.payment_batches.ColMonth.readable=False
    db.payment_batches.ColMonth.writable=False
    db.payment_batches.IncludeZero.readable=False
    db.payment_batches.IncludeZero.writable=False

    return_url = URL('batch_content', vars=request.vars)

    crud.messages.submit_button = T("Save")
    crud.messages.record_updated = T('Saved batch')
    crud.settings.formstyle = 'bootstrap3_stacked'
    crud.settings.update_next = return_url
    crud.settings.update_deletable = False
    form = crud.update(db.payment_batches, pbID)

    form_id = "MainForm"
    form_element = form.element('form')
    form['_id'] = form_id

    elements = form.elements('input, select, textarea')
    for element in elements:
        element['_form'] = form_id

    submit = form.element('input[type=submit]')

    back = os_gui.get_button('back', return_url)

    return dict(content=form,
                save=submit,
                back=back)


def generate_batch_items(form):
    """
        Generates payment batch items
    """
    # set some general values
    pbID = form.vars.id
    pb = db.payment_batches(pbID)

    if db.sys_properties(Property='Currency'):
        currency = db.sys_properties(Property='Currency').PropertyValue
    else:
        currency = "EUR"


    # Default export (No category)
    if pb.BatchTypeDescription == 'invoices':
        generate_batch_items_invoices(pbID,
                                      pb,
                                      currency)
    elif ( pb.BatchTypeDescription == 'teacher_payments' or
           pb.BatchTypeDescription == 'employee_expenses' ):
        from openstudio.os_payment_batch import PaymentBatch
        pb = PaymentBatch(pbID)
        pb.generate_batch_items()
    else:
        # Category
        coldate = datetime.date(pb.ColYear, int(pb.ColMonth), 1)
        firstdaythismonth = coldate
        lastdaythismonth = get_last_day_month(coldate)

        generate_batch_items_category(pbID,
                                      pb,
                                      firstdaythismonth,
                                      lastdaythismonth,
                                      currency)


def generate_batch_items_invoices(pbID,
                                  pb,
                                  currency):
    """
        Generate invoices batch and write to db.payment_batches_items
    """
    query = (db.invoices.Status == 'sent') & \
            ((db.invoices.TeacherPayment == False) |
             (db.invoices.TeacherPayment == None)) & \
            ((db.invoices.EmployeeClaim == False) |
             (db.invoices.EmployeeClaim == None)) & \
            (db.invoices.payment_methods_id == 3) # 3 = Direct Debit

    if not pb.school_locations_id is None and pb.school_locations_id != '':
        query &= (db.auth_user.school_locations_id==pb.school_locations_id)

    left = [
        db.invoices_amounts.on(
            db.invoices_amounts.invoices_id ==
            db.invoices.id
        ),
        db.invoices_customers.on(
            db.invoices_customers.invoices_id ==
            db.invoices.id
        ),
        # db.invoices_items.on(
        #     db.invoices_items.invoices_id ==
        #     db.invoices.id
        # ),
        # db.invoices_items_customers_subscriptions.on(
        #     db.invoices_items_customers_subscriptions.invoices_items_id ==
        #     db.invoices_items.id
        # ),
        db.auth_user.on(
            db.invoices_customers.auth_customer_id ==
            db.auth_user.id
        ),
        db.customers_payment_info.on(
            db.customers_payment_info.auth_customer_id ==
            db.invoices_customers.auth_customer_id
        ),
        db.customers_payment_info_mandates.on(
            db.customers_payment_info_mandates.customers_payment_info_id ==
            db.customers_payment_info.id
        ),
        db.school_locations.on(
            db.auth_user.school_locations_id ==
            db.school_locations.id
        )
    ]

    rows = db(query).select(db.invoices.ALL,
                            db.invoices_amounts.ALL,
                            # db.invoices_items_customers_subscriptions.ALL,
                            db.customers_payment_info.ALL,
                            db.customers_payment_info_mandates.ALL,
                            db.school_locations.Name,
                            db.auth_user.id,
                            left=left,
                            orderby=db.auth_user.id)

    for row in rows:
        cuID = row.auth_user.id
        csID = ""
        iID  = row.invoices.id

        amount = row.invoices_amounts.TotalPriceVAT

        # check for zero amount
        if not pb.IncludeZero and amount == 0:
            continue

        # set description
        description = row.invoices.Description
        if not description:
            description = pb.Description

        try:
            description = description.strip()
        except:
            pass

        try:
            description = description.replace(',', '')
        except:
            pass

        # set account number
        try:
            accountnr = row.customers_payment_info.AccountNumber.strip()
        except AttributeError:
            accountnr = ''
        # set BIC
        try:
            bic = row.customers_payment_info.BIC.strip()
        except AttributeError:
            bic = ''

        msdate = row.customers_payment_info_mandates.MandateSignatureDate

        # set bank name
        if row.customers_payment_info.BankName == '':
            row.customers_payment_info.BankName = None

        db.payment_batches_items.insert(
            payment_batches_id = pbID,
            auth_customer_id = cuID,
            customers_subscriptions_id = csID, # This field is no longer used due to compatibility issues with linking invoice items to subscriptions (sometimes duplicates)
            invoices_id = iID,
            AccountHolder = row.customers_payment_info.AccountHolder,
            BIC = bic,
            AccountNumber = accountnr,
            MandateSignatureDate = msdate,
            MandateReference = row.customers_payment_info_mandates.MandateReference,
            Amount = amount,
            Currency = currency,
            Description = description,
            BankName = row.customers_payment_info.BankName,
            BankLocation = row.customers_payment_info.BankLocation
        )


def generate_batch_items_category(pbID,
                                  pb,
                                  firstdaythismonth,
                                  lastdaythismonth,
                                  currency):
    """
        Generates batch items for a category
    """
    category_id = pb.payment_categories_id
    query = (db.alternativepayments.payment_categories_id == category_id) & \
            (db.alternativepayments.PaymentYear == pb.ColYear) & \
            (db.alternativepayments.PaymentMonth == pb.ColMonth)

    if not pb.school_locations_id is None and pb.school_locations_id != '':
        query &= (db.auth_user.school_locations_id==pb.school_locations_id)

    left = [
        db.auth_user.on(
            db.auth_user.id ==
            db.alternativepayments.auth_customer_id
        ),
        db.school_locations.on(
            db.school_locations.id ==
            db.auth_user.school_locations_id
        ),
        db.customers_payment_info.on(
            db.customers_payment_info.auth_customer_id ==
            db.alternativepayments.auth_customer_id
        ),
        db.customers_payment_info_mandates.on(
            db.customers_payment_info_mandates.customers_payment_info_id ==
            db.customers_payment_info.id
        )
    ]

    rows = db(query).select(db.alternativepayments.Amount,
                            db.alternativepayments.Description,
                            db.alternativepayments.auth_customer_id,
                            db.auth_user.id,
                            db.auth_user.first_name,
                            db.auth_user.last_name,
                            db.school_locations.Name,
                            db.customers_payment_info.ALL,
                            db.customers_payment_info_mandates.ALL,
                            left=left,
                            orderby=db.auth_user.id)
    for row in rows:
        # check for 0 amount, skip if it's not supposed to be included
        if row.alternativepayments.Amount == 0 and not pb.IncludeZero:
            continue
        cuID = row.auth_user.id
        amount = format(row.alternativepayments.Amount, '.2f')
        description = row.alternativepayments.Description

        try:
            description = description.strip()
        except:
            pass

        # end alternative payments

        try:
            accountnr = row.customers_payment_info.AccountNumber.strip()
        except AttributeError:
            accountnr = ''
        try:
            bic = row.customers_payment_info.BIC.strip()
        except AttributeError:
            bic = ''

        msdate = row.customers_payment_info_mandates.MandateSignatureDate

        if row.customers_payment_info.BankName == '':
            row.customers_payment_info.BankName = None

        db.payment_batches_items.insert(
            payment_batches_id = pbID,
            auth_customer_id = row.auth_user.id,
            AccountHolder = row.customers_payment_info.AccountHolder,
            BIC = bic,
            AccountNumber = accountnr,
            MandateSignatureDate = msdate,
            MandateReference = row.customers_payment_info_mandates.MandateReference,
            Amount = amount,
            Currency = currency,
            Description = description,
            BankName = row.customers_payment_info.BankName,
            BankLocation = row.customers_payment_info.BankLocation
        )


def get_batch_items_recurring_set(pbID):
    """
    :param pbID: db.paymentbatches.id
    :return: list of auth_user_ids that have been in previous batches
    """
    pb = db.payment_batches(pbID)

    query = (db.payment_batches.id < pbID) & \
            (db.payment_batches.BatchType == pb.BatchType) & \
            (db.payment_batches.Status == 'sent_to_bank')

    left = [ db.payment_batches.on(db.payment_batches_items.payment_batches_id == db.payment_batches.id) ]

    rows = db(query).select(db.payment_batches_items.auth_customer_id,
                            left=left,
                            distinct=True)

    ids = []
    for row in rows:
        ids.append(row.auth_customer_id)

    return ids


def get_batch_items(pbID, display=False, first=False, recurring=False):
    """
        Returns a list of batch items for a payment batch ( pbID )
        Set display to true, when the result will be displayed on a web page
        The description will get a maximum length in that case
    """
    pb = db.payment_batches(pbID)

    if pb.school_locations_id:
        location = db.school_locations(pb.school_locations_id).Name
    else:
        location = 'All'

    query = (db.payment_batches_items.payment_batches_id == pbID)

    recurring_ids = get_batch_items_recurring_set(pbID)

    if first:
        # Append to query to only show first customers
        # list customers where status == sent to bank and pbID < this batch, & batchtype = same then only customer id's not in set
        query &= ~(db.payment_batches_items.auth_customer_id.belongs(recurring_ids))

    if recurring:
        # Append to query to only show recurring customers
        # list customers where status == sent to bank and pbID < this batch, & batchtype (col or pay) is same then only customer id's in set
        query &= (db.payment_batches_items.auth_customer_id.belongs(recurring_ids))

    left = [
        db.invoices.on(
            db.payment_batches_items.invoices_id ==
            db.invoices.id
        )
    ]

    bi = []
    rows = db(query).select(
        db.payment_batches_items.ALL,
        db.invoices.id,
        db.invoices.InvoiceID,
        left=left,
        orderby=db.payment_batches_items.id
    )

    for i, row in enumerate(rows):
        repr_row = list(rows[i:i+1].render())[0]

        if row.payment_batches_items.MandateSignatureDate:
            msdate = row.payment_batches_items.MandateSignatureDate.strftime(DATE_FORMAT)
        else:
            msdate = ''

        cuID = row.payment_batches_items.auth_customer_id
        csID = row.payment_batches_items.customers_subscriptions_id
        if not csID:
            csID = ''

        if display:
            mandate_reference = repr_row.payment_batches_items.MandateReference
            description = SPAN(max_string_length(row.payment_batches_items.Description, 24),
                               _title=row.payment_batches_items.Description)
        else:
            mandate_reference = row.payment_batches_items.MandateReference
            description = row.payment_batches_items.Description

        item = {
            'id': row.payment_batches_items.id,
            'line': i+1,
            'cuID': cuID,
            'csID': csID,
            'account_holder': row.payment_batches_items.AccountHolder,
            'account_number': row.payment_batches_items.AccountNumber.upper(),
            'bic': row.payment_batches_items.BIC,
            'mandate_signature_date': msdate,
            'mandate_reference': mandate_reference,
            'currency': row.payment_batches_items.Currency,
            'amount': row.payment_batches_items.Amount,
            'description': description,
            'execution_date': pb.Exdate.strftime(DATE_FORMAT),
            'bank_name': repr_row.payment_batches_items.BankName,
            'bank_location': repr_row.payment_batches_items.BankLocation,
            'invoice_id': row.payment_batches_items.invoices_id,
            'invoice_InvoiceID': repr_row.invoices.InvoiceID
        }

        if not display:
            item['location'] = location

        bi.append(item)

    return bi


@auth.requires(auth.has_membership(group_id='Admins') or \
               auth.has_permission('read', 'payment_batches'))
def export_csv():
    """
        Exports batch to CSV format
    """
    first = False
    recurring= False
    if request.vars['first']:
        first = True
    if request.vars['recurring']:
        recurring = True

    pbID = request.vars['pbID']
    pb = db.payment_batches(pbID)

    # log to database
    db.payment_batches_exports.insert(payment_batches_id=pbID,
                                      FirstCustomers=first,
                                      RecurringCustomers=recurring)

    # create writer and buffer to hold data
    stream = io.StringIO()
    writer = csv.writer(stream)

    # write the header
    writer.writerow(['customers_id',
                     'SubscriptionID',
                     'Account holder',
                     'Bank Location',
                     'Currency',
                     'Amount',
                     'Account number',
                     'BIC',
                     'Mandate Signature Date',
                     'Mandate Reference',
                     'Description',
                     'Execution Date',
                     'Location'])

    batch_items = get_batch_items(pbID, first=first, recurring=recurring)
    for item in batch_items:
        customers_id = item['cuID']
        customer_subscriptions_id = item['csID']
        account_holder = item['account_holder']
        bank_location = item['bank_location']
        currency = item['currency']
        amount = item['amount']
        account_number = item['account_number']
        bic = item['bic']
        mandate_signature_date = item['mandate_signature_date']
        mandate_reference = item['mandate_reference']
        description = item['description']
        execution_date = item['execution_date']

        row = [ customers_id,
                customer_subscriptions_id,
                account_holder,
                bank_location,
                currency,
                amount,
                account_number,
                bic,
                mandate_signature_date,
                mandate_reference,
                description,
                execution_date ]
        if session.show_location:
            row.append(item.get('location', ''))

        writer.writerow(row)

    batch_name = pb.Name.replace(' ', '_')
    fname = 'Batch_' + pbID + '_' + batch_name
    if first:
        fname += '_FRST'
    if recurring:
        fname += '_RCUR'
    fname += '.csv'
    response.headers['Content-Type']='application/vnd.ms-excel'
    response.headers['Content-disposition']='attachment; filename=' + fname

    return stream.getvalue()


@auth.requires(auth.has_membership(group_id='Admins') or \
               auth.has_permission('read', 'invoices'))
def invoices():
    """
        Overview page for invoices
    """
    response.title = T('Invoices')
    response.subtitle = T('All invoices')
    response.view = 'general/only_content.html'

    session.invoices_edit_back = 'finance_invoices'
    session.invoices_payment_add_back = 'finance_invoices'

    # enable search in load
    #request.vars['search_enabled'] = True

    invoices = Invoices()
    status_filter = invoices.list_get_status_filter()
    list = invoices.list_invoices(search_enabled=True)

    content = DIV(status_filter, list)
                  # DIV(LOAD('invoices', 'list_invoices.load',
                  #     ajax_trap=True,
                  #     vars=request.vars,
                  #     content=os_gui.get_ajax_loader())))


    # tools dropdown
    tool_links = [
        A(SPAN(os_gui.get_fa_icon('fa-search'), ' ',
               T("Open invoices on date")),
               _href=URL('invoices', 'open_on_date'))
    ]
    tools = os_gui.get_dropdown_menu(tool_links,
                                     T(''),
                                     btn_size='',
                                     btn_icon='wrench',
                                     menu_class='pull-right')

    export_links = [ A(SPAN(os_gui.get_fa_icon('fa-file-o'), ' ',
                            T('Invoices')),
                     _href=URL('invoices', 'export_invoices')) ]
    export = os_gui.get_dropdown_menu(export_links,
                                      '',
                                      btn_size='',
                                      btn_icon='download',
                                      menu_class='pull-right')

    return dict(content=content,
                header_tools=DIV(export, tools))


@auth.requires(auth.has_membership(group_id='Admins') or
               auth.has_permission('read', 'receipts'))
def receipts():
    """
    List receipts
    """
    from openstudio.os_receipts import Receipts

    response.title = T('Finance')
    response.subtitle = T('Receipts')
    response.view = 'general/only_content.html'

    receipts = Receipts()
    content = receipts.list(formatted=True)

    return dict(content=content)


@auth.requires(auth.has_membership(group_id='Admins') or
               auth.has_permission('read', 'receipts'))
def receipt():
    """
    Print friendly view of receipt
    """
    from openstudio.os_receipt import Receipt

    rID = request.vars['rID']
    receipt = Receipt(rID)

    return receipt.get_print_display()


def teacher_payments_get_menu(page, status='not_verified'):
    pages = []

    if ( auth.has_membership(group_id='Admins') or
         auth.has_permission('read', 'teachers_payment_classes_attendance') ):
        pages.append([ 'teacher_payment_classes_not_verified',
                       T('Not verified'),
                       URL('teacher_payment_classes', vars={'status': 'not_verified'}) ])
        pages.append([ 'teacher_payment_classes_verified',
                       T('Verified'),
                       URL('teacher_payment_classes', vars={'status': 'verified'}) ])
        pages.append([ 'teacher_payment_classes_processed',
                       T('Processed'),
                       URL('teacher_payment_classes', vars={'status': 'processed'}) ])


    pages.append(
        [
            'teacher_payments_invoices',
            T('Credit invoices'),
            URL('teacher_payments_invoices')
        ]
    )


    return os_gui.get_submenu(pages, page, horizontal=True, htype='tabs')


@auth.requires(auth.has_membership(group_id='Admins') or \
               auth.has_permission('read', 'invoices'))
def teacher_payments_invoices():
    """
        List teacher payments invoices by month and add button to add invoices for a
        selected month
    """
    response.title = T('Teacher payments')
    response.subtitle = T('')
    response.view = 'general/only_content_no_box.html'

    invoices = Invoices()
    status_filter = invoices.list_get_status_filter()
    list = invoices.list_invoices(only_teacher_credit_invoices=True)

    content = DIV(
        teacher_payments_get_menu(request.function),
         DIV(DIV(status_filter,
                 list,
                  _class='tab-pane active'),
             _class='tab-content'),
         _class='nav-tabs-custom')

    return dict(content=content)


# @auth.requires(auth.has_membership(group_id='Admins') or \
#                auth.has_permission('create', 'invoices'))
# def teacher_payments_generate_invoices_choose_month():
#     """
#         Choose year and month to create invoices
#     """
#     from openstudio.os_forms import OsForms
#
#     response.title = T('Teacher payments')
#     response.subtitle = T('')
#     response.view = 'general/only_content.html'
#
#     if 'year' in request.vars and 'month' in request.vars:
#         year = int(request.vars['year'])
#         month = int(request.vars['month'])
#         teacher_payments_generate_invoices(year, month)
#         redirect(URL('teacher_payments'))
#
#     os_forms = OsForms()
#     form = os_forms.get_month_year_form(
#         request.vars['year'],
#         request.vars['month'],
#         submit_button = T('Create invoices')
#     )
#
#     content = DIV(
#         H4(T('Create teacher credit invoices for month')),
#         DIV(form['form']),
#         _class='col-md-6'
#     )
#
#     back = os_gui.get_button('back', URL('teacher_payments'))
#
#     return dict(content=content,
#                 save=form['submit'],
#                 back=back)


#TODO move code from this function to integrate with attendance based payments
def teacher_payments_generate_invoices(year, month):
    """
        Actually generate teacher payment credit invoices
    """
    from openstudio.os_invoices import Invoices

    invoices = Invoices()
    nr_created = invoices.batch_generate_teachers_invoices(year, month)
    session.flash = SPAN(T('Created'), ' ', nr_created, ' ', T('invoice'))
    if nr_created > 1:
        session.flash.append('s')


@auth.requires(auth.has_membership(group_id='Admins') or \
               auth.has_permission('read', 'teachers_payment_attendance'))
def teacher_payment_classes():
    """

    :return:
    """
    from openstudio.os_teachers_payment_classes import TeachersPaymentClasses

    response.title = T('Teacher payments')
    response.subtitle = T('')
    response.view = 'general/only_content_no_box.html'

    status = request.vars['status']

    try:
        page = int(request.args[0])
    except IndexError:
        page = 0

    tpc = TeachersPaymentClasses()

    tools = ''
    if status == 'not_verified':
        create_permission = auth.has_membership(group_id='Admins') or \
                            auth.has_permission('create', 'teachers_payment_classes')
        update_permission = auth.has_membership(group_id='Admins') or \
                            auth.has_permission('update', 'teachers_payment_classes')

        verify_all = ''
        check_classes = ''

        if create_permission:
            verify_all = os_gui.get_button(
                'noicon',
                URL('teachers_payment_classes_verify_all'),
                title=T("Verify all"),
                tooltip="Verify all listed classes",
                btn_class='btn-primary'
            )

        if update_permission:
            check_classes = os_gui.get_button(
                'noicon',
                URL('teacher_payment_find_classes'),
                title=T("Find classes"),
                tooltip=T("Find classes in range of dates that are not yet registered for teacher payment")
            )

        tools = DIV(
            check_classes,
            verify_all,
        )

        table = tpc.get_not_verified(
            formatted=True,
            page=page,
        )

    elif status == 'verified':
        permission = auth.has_membership(group_id='Admins') or \
                     auth.has_permission('create', 'invoices')

        if permission:
            links = []
            # Process all
            links.append(A(os_gui.get_fa_icon('fa-check'), T("All verified classes"),
                           _href=URL('teachers_payment_classes_process_verified'),
                           _title=T("Create credit invoices")))
            links.append('divider')
            # Process between dates
            links.append(A(os_gui.get_fa_icon('fa-calendar-o'), T('Verified classes between dates'),
                           _href='teacher_payment_classes_process_choose_dates',
                           _title=T("Choose which verified classes to process")))

            tools = os_gui.get_dropdown_menu(
                links=links,
                btn_text=T('Process'),
                btn_size='btn-sm',
                btn_class='btn-primary',
                btn_icon='actions',
                menu_class='btn-group pull-right')

        table = tpc.get_verified(
            formatted=True,
            page=page
        )

    elif status == 'processed':
        session.invoices_edit_back = 'finance_teacher_payment_classes_processed'

        table = tpc.get_processed(
            formatted=True,
            page = page
        )

    content = DIV(
        teacher_payments_get_menu(request.function + '_' + status, status),
        DIV(DIV(table,
                 _class='tab-pane active'),
            _class='tab-content'),
        _class='nav-tabs-custom'
    )

    return dict(
        content=content,
        header_tools=tools
    )


@auth.requires(auth.has_membership(group_id='Admins') or \
               auth.has_permission('create', 'teachers_payment_classes'))
def teacher_payment_find_classes():
    """
    :return: None
    """
    from openstudio.os_teachers_payment_classes import TeachersPaymentClasses
    from general_helpers import set_form_id_and_get_submit_button

    response.title = T('Teacher payments')
    response.subtitle = T('Find classes')
    response.view = 'general/only_content.html'

    # Add some explanation
    content = DIV(
        B(T("Choose a period to check for classes not yet in Not verfied, verified or processed.")), BR(), BR(),
    )

    return_url = URL('teacher_payment_classes', vars={'status': 'not_verified'})

    # choose period and then do something
    form = SQLFORM.factory(
        Field('Startdate', 'date', required=True,
            requires=IS_DATE_IN_RANGE(format=DATE_FORMAT,
                                      minimum=datetime.date(1900,1,1),
                                      maximum=datetime.date(2999,1,1)),
            represent=represent_date,
            default=datetime.date(TODAY_LOCAL.year,
                                  TODAY_LOCAL.month,
                                  1),
            label=T("Start date"),
            widget=os_datepicker_widget),
        Field('Enddate', 'date', required=False,
            requires=IS_EMPTY_OR(IS_DATE_IN_RANGE(format=DATE_FORMAT,
                                  minimum=datetime.date(1900,1,1),
                                  maximum=datetime.date(2999,1,1))),
            represent=represent_date,
            default=get_last_day_month(TODAY_LOCAL),
            label=T("End date"),
            widget=os_datepicker_widget),
        formstyle='bootstrap3_stacked',
        submit_button=T("Find")
    )

    result = set_form_id_and_get_submit_button(form, 'MainForm')
    form = result['form']
    submit = result['submit']

    if form.process().accepted:
        start = form.vars.Startdate
        end = form.vars.Enddate

        tpc = TeachersPaymentClasses()
        result = tpc.check_missing(
            start,
            end
        )

        if result['error']:
            response.flash = result['message']
        else:
            session.flash = SPAN(result['message'], ' ', T("Class(es) added to Not verified"))
            redirect(return_url)

    content.append(form)

    back = os_gui.get_button('back', return_url)

    return dict(content=content,
                back=back,
                save=submit)


@auth.requires(auth.has_membership(group_id='Admins') or \
               auth.has_permission('update', 'teachers_payment_classes'))
def teachers_payment_classes_verify_all():
    """
    Verify all not-verified classes
    :return: None
    """
    from openstudio.os_teachers_payment_classes import TeachersPaymentClasses

    tpcs = TeachersPaymentClasses()
    number_verified = tpcs.verify_all()

    if number_verified:
        session.flash = T("All not verified classes have been verified")
    else:
        session.flash = T("No classes were verified")

    redirect(URL('teacher_payment_classes', vars={'status': 'verified'}))


@auth.requires(auth.has_membership(group_id='Admins') or \
               auth.has_permission('update', 'teachers_payment_classes'))
def teachers_payment_attendance_class_verify():
    """
    Verify attendance / payment
    :return: None
    """
    from openstudio.os_teachers_payment_class import TeachersPaymentClass

    tpcID = request.vars['tpcID']

    tpc = TeachersPaymentClass(tpcID)
    success = tpc.verify()

    if success:
        session.flash = T("Class verified")
    else:
        session.flash = T("Error verifying class")

    redirect(URL('teacher_payment_classes', vars={'status': 'verified'}))


@auth.requires(auth.has_membership(group_id='Admins') or \
               auth.has_permission('update', 'teachers_payment_classes'))
def teachers_payment_attendance_class_unverify():
    """
    Verify attendance / payment
    :return: None
    """
    from openstudio.os_teachers_payment_class import TeachersPaymentClass

    tpcID = request.vars['tpcID']

    tpc = TeachersPaymentClass(tpcID)
    success = tpc.unverify()

    if success:
        session.flash = T("Class moved to Not verified")
    else:
        session.flash = T("Error moving class to Not verified")

    redirect(URL('teacher_payment_classes', vars={'status': 'not_verified'}))


@auth.requires(auth.has_membership(group_id='Admins') or \
               auth.has_permission('create', 'invoices'))
def teachers_payment_classes_process_verified():
    """
    Process verified classes; create credit invoices based on verified classes
    :return:
    """
    from openstudio.os_teachers_payment_classes import TeachersPaymentClasses

    tpc = TeachersPaymentClasses()
    result = tpc.process_verified()
    count_processed = result['message']

    classes = T('classes')
    if count_processed == 1:
        classes = T("class")

    session.flash = SPAN(
        T("Processed"), ' ',
        count_processed, ' ',
        classes
    )

    redirect(URL('teacher_payment_classes', vars={'status': 'processed'}))


@auth.requires(auth.has_membership(group_id='Admins') or \
               auth.has_permission('create', 'invoices'))
def teacher_payment_classes_process_choose_dates():
    """
    :return: None
    """
    from openstudio.os_teachers_payment_classes import TeachersPaymentClasses
    from general_helpers import set_form_id_and_get_submit_button

    response.title = T('Teacher payments')
    response.subtitle = T('Process verified')
    response.view = 'general/only_content.html'

    # Add some explanation
    content = DIV(
        B(T("Choose a period within which to process verified classes.")), BR(), BR(),
    )

    return_url = URL('teacher_payment_classes', vars={'status': 'verified'})

    # choose period and then do something
    form = SQLFORM.factory(
        Field('Startdate', 'date', required=True,
            requires=IS_DATE_IN_RANGE(format=DATE_FORMAT,
                                      minimum=datetime.date(1900,1,1),
                                      maximum=datetime.date(2999,1,1)),
            represent=represent_date,
            default=datetime.date(TODAY_LOCAL.year,
                                  TODAY_LOCAL.month,
                                  1),
            label=T("Start date"),
            widget=os_datepicker_widget),
        Field('Enddate', 'date', required=False,
            requires=IS_EMPTY_OR(IS_DATE_IN_RANGE(format=DATE_FORMAT,
                                  minimum=datetime.date(1900,1,1),
                                  maximum=datetime.date(2999,1,1))),
            represent=represent_date,
            default=get_last_day_month(TODAY_LOCAL),
            label=T("End date"),
            widget=os_datepicker_widget),
        formstyle='bootstrap3_stacked',
        submit_button=T("Process")
    )

    result = set_form_id_and_get_submit_button(form, 'MainForm')
    form = result['form']
    submit = result['submit']

    if form.process().accepted:
        start = form.vars.Startdate
        end = form.vars.Enddate

        tpc = TeachersPaymentClasses()
        result = tpc.process_verified(
            date_from = start,
            date_until = end
        )

        if result['error']:
            response.flash = result['message']
        else:
            session.flash = SPAN(result['message'], ' ', T("Class(es) processed"))
            redirect(return_url)

    content.append(form)

    back = os_gui.get_button('back', return_url)

    return dict(content=content,
                back=back,
                save=submit)


def employee_expenses_get_menu(page):
    pages = []

    # print status

    if ( auth.has_membership(group_id='Admins') or
         auth.has_permission('read', 'employee_claims') ):
        pages.append([
            'employee_expenses',
            T('Pending'),
            URL('employee_expenses')
        ])
        pages.append([
            'employee_expenses_rejected',
            T('Rejected'),
            URL('employee_expenses_rejected')
        ])
        pages.append([
            'employee_expenses_accepted',
            T('Accepted'),
            URL('employee_expenses_accepted')
        ])
        pages.append([
            'employee_expenses_processed',
            T('Processed'),
            URL('employee_expenses_processed')
        ])

    pages.append([
        'employee_expenses_invoices',
        T('Credit invoices'),
        URL('employee_expenses_invoices')
    ])


    return os_gui.get_submenu(pages,page, horizontal=True, htype='tabs')


@auth.requires(auth.has_membership(group_id='Admins') or \
               auth.has_permission('read', 'invoices'))
def employee_expenses_invoices():
    """
        List teacher payments invoices by month and add button to add invoices for a
        selected month
    """
    response.title = T('Employee Expenses')
    response.subtitle = T('')
    response.view = 'general/only_content_no_box.html'

    invoices = Invoices()
    status_filter = invoices.list_get_status_filter()
    list = invoices.list_invoices(only_employee_claim_credit_invoices=True)

    content = DIV(
        employee_expenses_get_menu(request.function),
         DIV(DIV(status_filter,
                 list,
                  _class='tab-pane active'),
             _class='tab-content'),
         _class='nav-tabs-custom')

    return dict(content=content)


@auth.requires(auth.has_membership(group_id='Admins') or \
               auth.has_permission('read', 'employee_claims'))
def employee_expenses():
    """
    List all pending expenses
    """
    from openstudio.os_employee_claims import EmployeeClaims

    response.title = T('Employee Expenses')
    response.subtitle = T('')
    response.view = 'general/only_content_no_box.html'

    status = request.vars['status']

    try:
        page = int(request.args[0])
    except IndexError:
        page = 0

    ec = EmployeeClaims()

    tools = ''
    # if status == 'not_verified':
    update_permission = auth.has_membership(group_id='Admins') or \
                        auth.has_permission('update', 'employee_expenses')

    verify_all = ''

    if update_permission:
        verify_all = os_gui.get_button(
            'noicon',
            URL('employee_expenses_accept_all'),
            title=T("Accept all"),
            tooltip="Accept all listed expenses",
            btn_class='btn-primary'
        )

    tools = DIV(
        verify_all,
    )

    table = ec.get_pending(
        formatted = True,
        page = page
    )

    content = DIV(
        employee_expenses_get_menu(request.function),
        DIV(DIV(table,
                 _class='tab-pane active'),
            _class='tab-content'),
        _class='nav-tabs-custom'
    )

    return dict(
        content=content,
        header_tools=tools
    )


@auth.requires(auth.has_membership(group_id='Admins') or \
               auth.has_permission('read', 'employee_claims'))
def employee_expenses_accepted():
    """

    :return:
    """
    from openstudio.os_employee_claims import EmployeeClaims

    response.title = T('Employee Expenses')
    response.subtitle = T('')
    response.view = 'general/only_content_no_box.html'

    status = request.vars['status']

    try:
        page = int(request.args[0])
    except IndexError:
        page = 0

    tools = ''
    # if status == 'not_verified':
    create_permission = auth.has_membership(group_id='Admins') or \
                        auth.has_permission('create', 'invoices')

    verify_all = ''

    if create_permission:
        verify_all = os_gui.get_button(
            'noicon',
            URL('employee_expenses_process_accepted'),
            title=T("Process all"),
            tooltip="Process all accepted expenses and create invoices",
            btn_class='btn-primary'
        )
    tools = verify_all
    ec = EmployeeClaims()

    table = ec.get_accepted(
        formatted = True,
        page = page
    )

    content = DIV(
        employee_expenses_get_menu(request.function),
        DIV(DIV(table,
                 _class='tab-pane active'),
            _class='tab-content'),
        _class='nav-tabs-custom'
    )

    return dict(
        content=content,
        header_tools= tools
    )


@auth.requires(auth.has_membership(group_id='Admins') or \
               auth.has_permission('read', 'employee_claims'))
def employee_expenses_rejected():
    """

    :return:
    """
    from openstudio.os_employee_claims import EmployeeClaims

    response.title = T('Employee Expenses')
    response.subtitle = T('')
    response.view = 'general/only_content_no_box.html'

    status = request.vars['status']

    try:
        page = int(request.args[0])
    except IndexError:
        page = 0

    ec = EmployeeClaims()

    table = ec.get_rejected(
        formatted = True,
        page = page
    )

    content = DIV(
        employee_expenses_get_menu(request.function),
        DIV(DIV(table,
                 _class='tab-pane active'),
            _class='tab-content'),
        _class='nav-tabs-custom'
    )

    return dict(
        content=content
    )


@auth.requires(auth.has_membership(group_id='Admins') or \
               auth.has_permission('read', 'employee_claims'))
def employee_expenses_processed():
    """

    :return:
    """
    from openstudio.os_employee_claims import EmployeeClaims

    response.title = T('Employee Expenses')
    response.subtitle = T('')
    response.view = 'general/only_content_no_box.html'

    session.invoices_edit_back = 'finance_employee_expenses_processed'

    status = request.vars['status']

    try:
        page = int(request.args[0])
    except IndexError:
        page = 0

    ec = EmployeeClaims()

    table = ec.get_processed(
        formatted = True,
        page = page
    )

    content = DIV(
        employee_expenses_get_menu(request.function),
        DIV(DIV(table,
                 _class='tab-pane active'),
            _class='tab-content'),
        _class='nav-tabs-custom'
    )

    return dict(
        content=content
    )


@auth.requires(auth.has_membership(group_id='Admins') or \
               auth.has_permission('update', 'employee_claims'))
def employee_expenses_accept_all():
    """
    Verify all not-verified classes
    :return: None
    """
    from openstudio.os_employee_claims import EmployeeClaims

    ec = EmployeeClaims()
    number_accepted = ec.accept_all()

    if number_accepted:
        session.flash = T("All not accepted expenses have been accepted")
    else:
        session.flash = T("No classes were accepted")

    redirect(URL('employee_expenses'))


@auth.requires(auth.has_membership(group_id='Admins') or \
               auth.has_permission('update', 'employee_claims'))
def employee_expenses_accept():
    """
    Verify attendance / payment
    :return: None
    """
    from openstudio.os_employee_claim import EmployeeClaim

    ecID = request.vars['ecID']

    ec = EmployeeClaim(ecID)
    success = ec.accept()

    if success:
        session.flash = T("Expense accepted")
    else:
        session.flash = T("Error accepting claim")

    redirect(URL('employee_expenses'))


@auth.requires(auth.has_membership(group_id='Admins') or \
               auth.has_permission('update', 'employee_claims'))
def employee_expenses_reject():
    """
    Verify attendance / payment
    :return: None
    """
    from openstudio.os_employee_claim import EmployeeClaim

    ecID = request.vars['ecID']

    ec = EmployeeClaim(ecID)
    success = ec.reject()

    if success:
        session.flash = T("Expense moved to rejected")
    else:
        session.flash = T("Error rejecting expense")

    redirect(URL('employee_expenses'))


@auth.requires(auth.has_membership(group_id='Admins') or \
               auth.has_permission('update', 'employee_claims'))
def employee_expenses_pending():
    """
    Verify attendance / payment
    :return: None
    """
    from openstudio.os_employee_claim import EmployeeClaim

    ecID = request.vars['ecID']

    ec = EmployeeClaim(ecID)
    success = ec.pending()

    if success:
        session.flash = T("Expense moved to pending")
    else:
        session.flash = T("Error rejecting expense")

    redirect(URL('employee_expenses'))


@auth.requires(auth.has_membership(group_id='Admins') or \
               auth.has_permission('create', 'invoices'))
def employee_expenses_process_accepted():
    """
    Process verified classes; create credit invoices based on verified classes
    :return:
    """
    from openstudio.os_employee_claims import EmployeeClaims

    ec = EmployeeClaims()
    count_processed = ec.process_accepted()

    expenses = T('expenses')
    if count_processed == 1:
        expenses = T("expense")

    session.flash = SPAN(
        T("Processed"), ' ',
        count_processed, ' ',
        expenses
    )

    redirect(URL('employee_expenses_processed'))
