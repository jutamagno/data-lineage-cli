from lineage.dbt import strip_jinja


def test_strip_jinja_ref():
    sql = "SELECT id FROM {{ ref('orders') }}"
    assert strip_jinja(sql) == "SELECT id FROM orders"


def test_strip_jinja_source():
    sql = "SELECT id FROM {{ source('raw', 'events') }}"
    assert strip_jinja(sql) == "SELECT id FROM events"


def test_strip_jinja_block_tag_removed():
    sql = "{% config(materialized='table') %} SELECT id FROM users"
    result = strip_jinja(sql)
    assert "config" not in result
    assert "SELECT id FROM users" in result


def test_strip_jinja_leaves_plain_sql_unchanged():
    sql = "SELECT id, name FROM users WHERE active = 1"
    assert strip_jinja(sql) == sql


def test_strip_jinja_combined():
    sql = (
        "{% config(materialized='view') %}\n"
        "SELECT o.id, c.name\n"
        "FROM {{ ref('orders') }} o\n"
        "JOIN {{ source('crm', 'customers') }} c ON o.customer_id = c.id"
    )
    result = strip_jinja(sql)
    assert "orders" in result
    assert "customers" in result
    assert "{{" not in result
    assert "{%" not in result


def test_strip_jinja_multiline_block_tag():
    sql = "{% if target.name == 'prod' %}\nSELECT id FROM prod_table\n{% endif %}"
    result = strip_jinja(sql)
    assert "{%" not in result
