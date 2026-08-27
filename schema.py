DB_SCHEMA = """
Table: users
Columns: user_id, first_name, email, city, address

Table: orders
Columns: cart_id, user_id, total, total_products

Table: order_items
Columns: product_id, cart_id, user_id, quantity, price

Table: products
Columns: product_id, title, category, stock

Table: products_review
Columns: product_id, review_name, reviewer_email, rating, comment

Table: product_tags
Columns: product_id, tag
"""