# -*- coding: utf-8 -*-
#!/usr/bin/env python

"""py.test test cases to test OpenStudio.
These tests run based on webclient and need web2py server running.
"""

def test_workflow(client, web2py):
    """
        Can we edit the workflow settings?
    """
    url = '/shop_manage/workflow'
    client.get(url)
    assert client.status == 200

    data = {
        'shop_requires_complete_profile_classes': 'on',
        'shop_requires_complete_profile_memberships': 'on',
        'shop_requires_complete_profile_classcards': 'on',
        'shop_requires_complete_profile_events': 'on',
        'shop_requires_complete_profile_subscriptions': 'on',
        'shop_classes_advance_booking_limit':'22',
        'shop_classes_cancellation_limit':'7',
        'shop_subscriptions_start':'today',
        'shop_subscriptions_payment_method': 'directdebit',
        'shop_allow_trial_classes_for_existing_customers': "on",
        'shop_classes_trial_limit': '1',
    }

    client.post(url, data=data)
    assert client.status == 200

    # Check that the settings have been saved in the db
    assert web2py.db.sys_properties(Property='shop_requires_complete_profile_classes').PropertyValue == \
           data['shop_requires_complete_profile_classes']
    assert web2py.db.sys_properties(Property='shop_requires_complete_profile_memberships').PropertyValue == \
           data['shop_requires_complete_profile_memberships']
    assert web2py.db.sys_properties(Property='shop_requires_complete_profile_classcards').PropertyValue == \
           data['shop_requires_complete_profile_classcards']
    assert web2py.db.sys_properties(Property='shop_requires_complete_profile_events').PropertyValue == \
           data['shop_requires_complete_profile_events']
    assert web2py.db.sys_properties(Property='shop_requires_complete_profile_subscriptions').PropertyValue == \
           data['shop_requires_complete_profile_subscriptions']
    assert web2py.db.sys_properties(Property='shop_classes_advance_booking_limit').PropertyValue == \
           data['shop_classes_advance_booking_limit']
    assert web2py.db.sys_properties(Property='shop_classes_cancellation_limit').PropertyValue == \
           data['shop_classes_cancellation_limit']
    assert web2py.db.sys_properties(Property='shop_subscriptions_start').PropertyValue == \
           data['shop_subscriptions_start']
    assert web2py.db.sys_properties(Property='shop_subscriptions_payment_method').PropertyValue == \
           data['shop_subscriptions_payment_method']
    assert web2py.db.sys_properties(Property='shop_allow_trial_classes_for_existing_customers').PropertyValue == \
           data['shop_allow_trial_classes_for_existing_customers']
    assert web2py.db.sys_properties(Property='shop_classes_trial_limit').PropertyValue == \
           data['shop_classes_trial_limit']


def test_products(client, web2py):
    """
        Is the products page listing products?
    """
    from populate_os_tables import populate_shop_products
    populate_shop_products(web2py)

    assert web2py.db(web2py.db.shop_products).count() == 1

    url = '/shop_manage/products'
    client.get(url)
    assert client.status == 200

    product = web2py.db.shop_products(1)
    assert product.Name in client.text


def test_product_add(client, web2py):
    """
        Can we add a product?
    """
    url = '/shop_manage/product_add'
    client.get(url)
    assert client.status == 200

    data = {
        'Name': 'Grapefruit',
        'Description': 'Also great as juice',
        'Visibility': 'in_stock'
    }

    client.post(url, data=data)
    assert client.status == 200

    assert web2py.db(web2py.db.shop_products).count() == 1


def test_product_add_no_product_set_default_variant(client, web2py):
    """
        Add a default variant when adding a product
    """
    url = '/shop_manage/product_add'
    client.get(url)
    assert client.status == 200

    data = {
        'Name': 'Grapefruit',
        'Description': 'Also great as juice',
        'Visibility': 'in_stock'
    }

    client.post(url, data=data)
    assert client.status == 200
    assert web2py.db(web2py.db.shop_products).count() == 1

    variant = web2py.db.shop_products_variants(1)
    assert variant.Name == 'Default'
    assert variant.DefaultVariant == True


def test_product_add_with_product_set_variants(client, web2py):
    """
        Add all variants when adding a product with a product set
    """
    from populate_os_tables import populate_shop_products_sets
    populate_shop_products_sets(web2py,
                                options=True,
                                values=True)

    url = '/shop_manage/product_add'
    client.get(url)
    assert client.status == 200

    data = {
        'Name': 'Grapefruit',
        'Description': 'Also great as juice',
        'Visibility': 'in_stock',
        'shop_products_sets_id': 1,
    }

    client.post(url, data=data)
    assert client.status == 200
    assert web2py.db(web2py.db.shop_products).count() == 1

    # Make sure the first variant is the default, by default
    variant = web2py.db.shop_products_variants(1)
    assert variant.DefaultVariant == True

    # All variants created?
    assert web2py.db(
        web2py.db.shop_products_variants
    ).count() == 2


def test_product_edit(client, web2py):
    """
        Can we edit a product?
    """
    from populate_os_tables import populate_shop_products
    populate_shop_products(web2py)

    assert web2py.db(web2py.db.shop_products).count() == 1

    url = '/shop_manage/product_edit?spID=1'
    client.get(url)
    assert client.status == 200

    data = {
        'id': '1',
        'Name': 'Grapefruit',
        'Description': 'Also great as juice',
        'Visibility': 'in_stock'
    }

    client.post(url, data=data)
    assert client.status == 200

    product = web2py.db.shop_products(1)
    assert product.Name == data['Name']


def test_product_variants(client, web2py):
    """
        Can we list product variants?
    """
    from populate_os_tables import populate_shop_products_variants
    populate_shop_products_variants(web2py,
                                    populate_products=True)
    assert web2py.db(web2py.db.shop_products_variants).count() == 2

    url = '/shop_manage/product_variants?spID=1'
    client.get(url)
    assert client.status == 200

    variant = web2py.db.shop_products_variants(1)
    assert variant.Name in client.text

    # Check disabling the button for the default variant
    assert 'disabled="disabled" href="#" id="" onclick=""' in client.text


def test_product_variants_with_products_set(client, web2py):
    """
        Is the delete message saying "disable" for products with a set?
    """
    from populate_os_tables import populate_shop_products_sets
    from populate_os_tables import populate_shop_products_variants
    populate_shop_products_sets(web2py)
    populate_shop_products_variants(web2py)

    product = web2py.db.shop_products(1)
    product.shop_products_sets_id = 1
    product.update_record()
    web2py.db.commit()

    url = '/shop_manage/product_variants?spID=1'
    client.get(url)
    assert client.status == 200

    assert "Do you really want to disable this variant" in client.text
    assert '<a class="btn btn-default btn-sm" href="/shop_manage/product_variant_add?spID=2" id="" style="" target="" title=""><span class="fa fa-plus"></span> Add</a>' not in client.text


def test_product_variants_no_products_set(client, web2py):
    """
        Is the delete message saying "disable" for products without a set?
    """
    from populate_os_tables import populate_shop_products_variants
    populate_shop_products_variants(web2py)

    url = '/shop_manage/product_variants?spID=1'
    client.get(url)
    assert client.status == 200

    assert "Do you really want to delete this variant" in client.text
    assert "Add" in client.text


def test_product_variant_set_default(client, web2py):
    """
        Can we set a variant is default?
    """
    from populate_os_tables import populate_shop_products_variants
    populate_shop_products_variants(web2py)

    url = '/shop_manage/product_variant_set_default?spID=1&spvID=2'
    client.get(url)
    assert client.status == 200

    variant_1 = web2py.db.shop_products_variants(1)
    variant_2 = web2py.db.shop_products_variants(2)
    assert variant_1.DefaultVariant == False
    assert variant_2.DefaultVariant == True


def test_product_variant_add(client, web2py):
    """
        Can we add a product variant?
    """
    from populate_os_tables import populate_shop_products, populate_tax_rates
    populate_shop_products(web2py)
    populate_tax_rates(web2py)
    assert web2py.db(web2py.db.shop_products).count() == 1

    url = '/shop_manage/product_variant_add?spID=1'
    client.get(url)
    assert client.status == 200

    data = {
        'id': '1',
        'Name': 'Grapefruit',
        'tax_rates_id':1
    }

    client.post(url, data=data)
    assert client.status == 200

    variant = web2py.db.shop_products_variants(1)
    assert variant.Name == data['Name']


def test_product_variant_add_with_products_set(client, web2py):
    """
        We shouldn't be allowed to add a variant to a product with a set
    """
    from populate_os_tables import populate_shop_products
    from populate_os_tables import populate_tax_rates
    from populate_os_tables import populate_shop_products_sets
    populate_shop_products_sets(web2py)
    populate_shop_products(web2py)
    populate_tax_rates(web2py)

    product = web2py.db.shop_products(1)
    product.shop_products_sets_id = 1
    product.update_record()
    web2py.db.commit()
    assert web2py.db(web2py.db.shop_products).count() == 1

    url = '/shop_manage/product_variant_add?spID=1'
    client.get(url)
    assert client.status == 200

    assert "Unable to add" in client.text


def test_product_variant_edit(client, web2py):
    """
        Can we edit a product variant
    """
    from populate_os_tables import populate_shop_products_variants
    populate_shop_products_variants(web2py,
                                    populate_products=True)
    assert web2py.db(web2py.db.shop_products_variants).count() == 2

    url = '/shop_manage/product_variant_edit?spID=1&spvID=1'
    client.get(url)
    assert client.status == 200

    data = {
        'id': '1',
        'Name': 'Grapefruit',
        'tax_rates_id':1
    }

    client.post(url, data=data)
    assert client.status == 200

    variant = web2py.db.shop_products_variants(1)
    assert variant.Name == data['Name']


def test_product_variant_edit_with_products_set_name_read_only(client, web2py):
    """
        Is the name of a variant read only when it comes from a products set?
    """
    from populate_os_tables import populate_shop_products_variants
    populate_shop_products_variants(web2py,
                                    populate_products_sets=True)

    url = '/shop_manage/product_variant_edit?spID=1&spvID=1'
    client.get(url)
    assert client.status == 200
    assert 'form="MainForm" id="shop_products_variants_Name"' not in client.text


def test_product_variant_delete(client, web2py):
    """
        Can we delete a variant?
        This function will delete when a variant is not linked to a product set
    """
    from populate_os_tables import populate_shop_products_variants
    populate_shop_products_variants(web2py)

    count_variants = web2py.db(web2py.db.shop_products_variants).count()

    url = '/shop_manage/product_variant_delete?spID=1&spvID=1'
    client.get(url)
    assert client.status == 200

    assert web2py.db(web2py.db.shop_products_variants).count() == count_variants - 1


def test_product_variant_disable(client, web2py):
    """
        Can we disable a variant
        This function will disable when a variant is linked to a product set
    """
    from populate_os_tables import populate_shop_products_variants
    populate_shop_products_variants(web2py,
                                    populate_products_sets=True)

    url = '/shop_manage/product_variant_delete?spID=1&spvID=1'
    client.get(url)
    assert client.status == 200

    variant = web2py.db.shop_products_variants(1)
    assert variant.Enabled == False


def test_product_variant_enable(client, web2py):
    """
        Can we enable a variant
    """
    from populate_os_tables import populate_shop_products_variants
    populate_shop_products_variants(web2py,
                                    populate_products_sets=True)

    variant = web2py.db.shop_products_variants(1)
    variant.Enabled = False
    variant.update_record()
    web2py.db.commit()

    url = '/shop_manage/product_variant_enable?spID=1&spvID=1'
    client.get(url)
    assert client.status == 200

    variant = web2py.db.shop_products_variants(1)
    assert variant.Enabled == True


def test_products_sets(client, web2py):
    """
        Is the products_sets page listing products_sets?
    """
    from populate_os_tables import populate_shop_products_sets
    populate_shop_products_sets(web2py)

    assert web2py.db(web2py.db.shop_products_sets).count() == 1

    url = '/shop_manage/products_sets'
    client.get(url)
    assert client.status == 200

    products_set = web2py.db.shop_products_sets(1)
    assert products_set.Name in client.text


def test_products_sets_add(client, web2py):
    """
        Can we add a products_set?
    """
    url = '/shop_manage/products_set_add'
    client.get(url)
    assert client.status == 200

    data = {
        'Name': 'Grapefruit',
        'Description': 'Also great as juice'
    }

    client.post(url, data=data)
    assert client.status == 200

    assert web2py.db(web2py.db.shop_products_sets).count() == 1


def test_products_set_edit(client, web2py):
    """
        Can we edit a products_set?
    """
    from populate_os_tables import populate_shop_products_sets
    populate_shop_products_sets(web2py)

    url = '/shop_manage/products_set_edit?spsID=1'
    client.get(url)
    assert client.status == 200

    data = {
        'id': '1',
        'Name': 'Grapefruit',
        'Description': 'Also great as juice'
    }

    client.post(url, data=data)
    assert client.status == 200

    products_set = web2py.db.shop_products_sets(1)
    assert products_set.Name == data['Name']


def test_products_set_delete(client, web2py):
    """
        Can we delete a product set?
    """
    from populate_os_tables import populate_shop_products_sets
    populate_shop_products_sets(web2py)

    url = '/shop_manage/products_set_delete?spsID=1'
    client.get(url)
    assert client.status == 200

    query = (web2py.db.shop_products_sets.id)
    assert web2py.db(query).count() == 0


def test_products_set_options(client, web2py):
    """
        Are options and values in a set listed correctly
    """
    from populate_os_tables import populate_shop_products_sets
    populate_shop_products_sets(web2py,
                                options=True,
                                values=True)

    url = '/shop_manage/products_set_options?spsID=1'
    client.get(url)
    assert client.status == 200

    option = web2py.db.shop_products_sets_options(1)
    value = web2py.db.shop_products_sets_options_values(1)

    assert option.Name in client.text
    assert value.Name in client.text


def test_products_set_options_remove_add_and_del_when_linked_to_product(client, web2py):
    """
        We shouldn't be able to add options when the set is linked to one
        or more products
    """
    from populate_os_tables import populate_shop_products_variants
    populate_shop_products_variants(web2py, populate_products_sets=True)

    url = '/shop_manage/products_set_options?spsID=1'
    client.get(url)
    assert client.status == 200

    assert "Add option" not in client.text
    assert 'shop_products_sets_options_delete' not in client.text


def test_products_set_options_add(client, web2py):
    """
        Can we add an options?
    """
    from populate_os_tables import populate_shop_products_sets
    populate_shop_products_sets(web2py)

    url = '/shop_manage/products_set_options?spsID=1'
    client.get(url)
    assert client.status == 200

    data = {
        'Name': 'Banana'
    }
    client.post(url, data=data)
    assert client.status == 200

    assert web2py.db(web2py.db.shop_products_sets_options).count() == 1
    assert data['Name'] in client.text


def test_products_set_options_value_add(client, web2py):
    """
        Can we add an option value?
    """
    from populate_os_tables import populate_shop_products_sets
    populate_shop_products_sets(web2py,
                                options=True)

    url = '/shop_manage/products_set_options?spsID=1'
    client.get(url)
    assert client.status == 200

    data = {
        'shop_products_sets_options_id': 1,
        'Name': 'Banana Value',
        '_formname': 'shop_products_sets_options_values/None'
    }
    client.post(url, data=data)
    assert client.status == 200

    assert web2py.db(web2py.db.shop_products_sets_options_values).count() == 1
    assert data['Name'] in client.text


def test_products_set_options_value_add_update_variants(client, web2py):
    """
        Can we add an option value?
    """
    from populate_os_tables import populate_shop_products_variants
    populate_shop_products_variants(web2py,
                                    populate_products_sets=True)

    count_variants = web2py.db(web2py.db.shop_products_variants).count()

    url = '/shop_manage/products_set_options?spsID=1'
    client.get(url)
    assert client.status == 200

    data = {
        'shop_products_sets_options_id': 1,
        'Name': 'Banana Value',
        '_formname': 'shop_products_sets_options_values/None'
    }
    client.post(url, data=data)
    assert client.status == 200

    assert web2py.db(web2py.db.shop_products_variants).count() > count_variants
    query = (web2py.db.shop_products_variants.Enabled == False)
    assert web2py.db(query).count() > 0


def test_products_sets_options_delete(client, web2py):
    """
        Can we delete an option?
    """
    from populate_os_tables import populate_shop_products_sets
    populate_shop_products_sets(web2py,
                                options=True)

    url = '/shop_manage/products_sets_options_delete?spsoID=1'
    client.get(url)
    assert client.status == 200

    assert web2py.db(web2py.db.shop_products_sets_options).count() == 0


def test_products_sets_options_value_delete(client, web2py):
    """
        Can we delete an option value?
    """
    from populate_os_tables import populate_shop_products_sets
    populate_shop_products_sets(web2py,
                                options=True,
                                values=True)

    value_count = web2py.db(
        web2py.db.shop_products_sets_options_values
    ).count()

    url = '/shop_manage/products_sets_options_value_delete?spsovID=1'
    client.get(url)
    assert client.status == 200

    assert web2py.db(web2py.db.shop_products_sets_options_values).count() == value_count - 1


def test_brands(client, web2py):
    """
        Is the brands page listing brands?
    """
    from populate_os_tables import populate_shop_brands
    populate_shop_brands(web2py)

    assert web2py.db(web2py.db.shop_brands).count() == 1

    url = '/shop_manage/brands'
    client.get(url)
    assert client.status == 200

    brand = web2py.db.shop_brands(1)
    assert brand.Name in client.text


def test_brand_add(client, web2py):
    """
        Can we add a brand?
    """
    url = '/shop_manage/brand_add'
    client.get(url)
    assert client.status == 200

    data = {
        'Name': 'Grapefruit',
        'Description': 'Also great as juice'
    }

    client.post(url, data=data)
    assert client.status == 200

    assert web2py.db(web2py.db.shop_brands).count() == 1


def test_brand_edit(client, web2py):
    """
        Can we edit a brand?
    """
    from populate_os_tables import populate_shop_brands
    populate_shop_brands(web2py)

    url = '/shop_manage/brand_edit?sbID=1'
    client.get(url)
    assert client.status == 200

    data = {
        'id': '1',
        'Name': 'Grapefruit',
        'Description': 'Also great as juice'
    }

    client.post(url, data=data)
    assert client.status == 200

    brand = web2py.db.shop_brands(1)
    assert brand.Name == data['Name']


def test_brand_archive(client, web2py):
    """
        Can we archive a brand?
    """
    from populate_os_tables import populate_shop_brands
    populate_shop_brands(web2py)

    url = '/shop_manage/brand_archive?sbID=1'
    client.get(url)
    assert client.status == 200

    brand = web2py.db.shop_brands(1)
    assert brand.Archived == True


def test_categories(client, web2py):
    """
        Is the categories page listing categories?
    """
    from populate_os_tables import populate_shop_categories
    populate_shop_categories(web2py)

    assert web2py.db(web2py.db.shop_categories).count() == 1

    url = '/shop_manage/categories'
    client.get(url)
    assert client.status == 200

    category = web2py.db.shop_categories(1)
    assert category.Name in client.text


def test_category_add(client, web2py):
    """
        Can we add a category?
    """
    url = '/shop_manage/category_add'
    client.get(url)
    assert client.status == 200

    data = {
        'Name': 'Grapefruit',
        'Description': 'Also great as juice'
    }

    client.post(url, data=data)
    assert client.status == 200

    assert web2py.db(web2py.db.shop_categories).count() == 1


def test_category_edit(client, web2py):
    """
        Can we edit a category?
    """
    from populate_os_tables import populate_shop_categories
    populate_shop_categories(web2py)

    url = '/shop_manage/category_edit?scID=1'
    client.get(url)
    assert client.status == 200

    data = {
        'id': '1',
        'Name': 'Grapefruit',
        'Description': 'Also great as juice'
    }

    client.post(url, data=data)
    assert client.status == 200

    category = web2py.db.shop_categories(1)
    assert category.Name == data['Name']


def test_category_archive(client, web2py):
    """
        Can we archive a category?
    """
    from populate_os_tables import populate_shop_categories
    populate_shop_categories(web2py)

    url = '/shop_manage/category_archive?scID=1'
    client.get(url)
    assert client.status == 200

    category = web2py.db.shop_categories(1)
    assert category.Archived == True


def test_suppliers(client, web2py):
    """
        Is the suppliers page listing suppliers?
    """
    from populate_os_tables import populate_shop_suppliers
    populate_shop_suppliers(web2py)

    assert web2py.db(web2py.db.shop_suppliers).count() == 1

    url = '/shop_manage/suppliers'
    client.get(url)
    assert client.status == 200

    supplier = web2py.db.shop_suppliers(1)
    assert supplier.Name in client.text


def test_supplier_add(client, web2py):
    """
        Can we add a supplier?
    """
    url = '/shop_manage/supplier_add'
    client.get(url)
    assert client.status == 200

    data = {
        'Name': 'Grapefruit',
        'Description': 'Also great as juice'
    }

    client.post(url, data=data)
    assert client.status == 200

    assert web2py.db(web2py.db.shop_suppliers).count() == 1


def test_supplier_edit(client, web2py):
    """
        Can we edit a supplier?
    """
    from populate_os_tables import populate_shop_suppliers
    populate_shop_suppliers(web2py)

    url = '/shop_manage/supplier_edit?supID=1'
    client.get(url)
    assert client.status == 200

    data = {
        'id': '1',
        'Name': 'Grapefruit',
        'Description': 'Also great as juice'
    }

    client.post(url, data=data)
    assert client.status == 200

    supplier = web2py.db.shop_suppliers(1)
    assert supplier.Name == data['Name']


def test_supplier_archive(client, web2py):
    """
        Can we archive a supplier?
    """
    from populate_os_tables import populate_shop_suppliers
    populate_shop_suppliers(web2py)

    url = '/shop_manage/supplier_archive?supID=1'
    client.get(url)
    assert client.status == 200

    supplier = web2py.db.shop_suppliers(1)
    assert supplier.Archived == True
