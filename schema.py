schema = """
Table: users
Columns: 
- user_id
-first_name
-email
-city
-address

tables:orders
columns:
-cart_id
-user_id
-total
-total_products

tables:order_items
columns:
-product_id
-cart_id
-user_id
-quantity
-price

tables:products
columns :
-product_id
-title
-category
-stock

tables:products_review
columns:
-product_id
-review-name
-reviewer_email
-rating
-comment

tables:product_tags
cilumns:
-product_id
-tag

"""
