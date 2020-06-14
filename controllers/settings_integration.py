# -*- coding: utf-8 -*-
"""
    This file holds the settings for integrations
"""

def integration_get_menu(page):
    """
        Menu for system settings pages
    """
    pages = [
        [ 'mailchimp',
          T('MailChimp'),
          URL('mailchimp') ],
        ['mollie',
         T('Mollie'),
         URL('mollie')],
        ['recaptcha',
         T('reCAPTCHA'),
         URL('recaptcha')],
    ]

    return os_gui.get_submenu(pages, page, horizontal=True, htype='tabs')


@auth.requires(auth.has_membership(group_id='Admins') or
               auth.has_permission('read', 'settings'))
def mailchimp():
    """
        Page to set mailchimp API key
    """
    response.title = T("Settings")
    response.subtitle = T("Integration")
    response.view = 'general/tabs_menu.html'

    mailchimp_api_key = get_sys_property('mailchimp_api_key')
    mailchimp_username = get_sys_property('mailchimp_username')

    form = SQLFORM.factory(
        Field('mailchimp_username',
              requires=IS_NOT_EMPTY(),
              default=mailchimp_username,
              label=T('MailChimp User name')),
        Field('mailchimp_api_key',
              requires=IS_NOT_EMPTY(),
              default=mailchimp_api_key,
              label=T('MailChimp API key')),
        submit_button=T("Save"),
        formstyle='bootstrap3_stacked',
        separator=' ')

    form_id = "MainForm"
    form_element = form.element('form')
    form['_id'] = form_id

    elements = form.elements('input, select, textarea')
    for element in elements:
        element['_form'] = form_id

    submit = form.element('input[type=submit]')

    if form.accepts(request.vars, session):
        mailchimp_api_key = request.vars['mailchimp_api_key']
        set_sys_property('mailchimp_api_key', mailchimp_api_key)
        mailchimp_username = request.vars['mailchimp_username']
        set_sys_property('mailchimp_username', mailchimp_username)

        # User feedback
        session.flash = T('Saved')
        # reload so the user sees how the values are stored in the db now
        redirect(URL('mailchimp'))

    menu = integration_get_menu(request.function)

    return dict(content=form,
                menu=menu,
                save=submit)


@auth.requires(auth.has_membership(group_id='Admins') or
               auth.has_permission('read', 'settings'))
def mollie():
    """
        Page to set Mollie website profile
    """
    response.title = T("Settings")
    response.subtitle = T("Integration")
    response.view = 'general/tabs_menu.html'

    payment_providers = [
        [ 'disabled', T("Don't accept online payments") ],
        [ 'mollie', T('Mollie') ]
    ]

    online_payment_provider = get_sys_property('online_payment_provider')
    mollie_website_profile = get_sys_property('mollie_website_profile')

    form = SQLFORM.factory(
        Field('online_payment_provider',
              requires=IS_IN_SET(payment_providers),
              default=online_payment_provider,
              label=T("Payment provider")),
        Field('mollie_website_profile',
              default=mollie_website_profile,
              label=T('Mollie website profile (API-Key)')),
        submit_button=T("Save"),
        formstyle='bootstrap3_stacked',
        separator=' ')

    form_id = "MainForm"
    form_element = form.element('form')
    form['_id'] = form_id

    elements = form.elements('input, select, textarea')
    for element in elements:
        element['_form'] = form_id

    submit = form.element('input[type=submit]')

    mollie_signup = ''
    if not mollie_website_profile:
        create_mollie_account = A(T('Create Mollie account'),
                                  _href='https://www.mollie.com/nl/signup/2488481',
                                  _target="_blank",
                                  _class='btn btn-info')
        mollie_signup = os_gui.get_alert('info',
            SPAN(SPAN(T('Mollie website profile not found'), _class='bold'), BR(),
            T("Please click the button below to sign up with Mollie and create a website profile, or enter the website profile key below."), BR(),
            BR(),
            create_mollie_account))

    if form.accepts(request.vars, session):
        # check payment provider and profile id
        vars = [
            'online_payment_provider',
            'mollie_website_profile'
        ]
        for var in vars:
            value = request.vars[var]
            set_sys_property(var, value)

        online_payment_provider = request.vars['online_payment_provider']

        # User feedback
        session.flash = T('Saved')
        # reload so the user sees how the values are stored in the db now
        redirect(URL('mollie'))

    menu = integration_get_menu(request.function)

    return dict(content=DIV(mollie_signup, form),
                menu=menu,
                save=submit)


@auth.requires(auth.has_membership(group_id='Admins') or
               auth.has_permission('read', 'settings'))
def recaptcha():
    """
        Page to set Mollie website profile
    """
    response.title = T("Settings")
    response.subtitle = T("Integration")
    response.view = 'general/tabs_menu.html'

    recaptcha_enabled = get_sys_property('recaptcha_enabled')
    recaptcha_site_key = get_sys_property('recaptcha_site_key')
    recaptcha_secret_key = get_sys_property('recaptcha_secret_key')

    form = SQLFORM.factory(
        Field('recaptcha_enabled', 'boolean',
              default=recaptcha_enabled,
              label=T("Use reCAPTCHA for login, password reset and user account creation forms")),
        Field('recaptcha_site_key',
              default=recaptcha_site_key,
              label=T("Site key")),
        Field('recaptcha_secret_key',
              default=recaptcha_secret_key,
              label=T('Secret key')),
        submit_button=T("Save"),
        formstyle='bootstrap3_stacked',
        separator=' ')

    form_id = "MainForm"
    form_element = form.element('form')
    form['_id'] = form_id

    elements = form.elements('input, select, textarea')
    for element in elements:
        element['_form'] = form_id

    submit = form.element('input[type=submit]')

    if form.accepts(request.vars, session):
        # check payment provider and profile id
        vars = [
            'recaptcha_enabled',
            'recaptcha_site_key',
            'recaptcha_secret_key'
        ]
        for var in vars:
            value = request.vars[var]
            set_sys_property(var, value)

        # User feedback
        session.flash = T('Saved')
        # reload so the user sees how the values are stored in the db now
        redirect(URL('recaptcha'))

    info = ""
    if not recaptcha_site_key:
        info = DIV(
            T("Sign up for you reCAPTCHA keys "),
            A(T("here"),
              _href="https://www.google.com/recaptcha/"
            )
        )

    menu = integration_get_menu(request.function)

    return dict(content=DIV(form, info),
                menu=menu,
                save=submit)
