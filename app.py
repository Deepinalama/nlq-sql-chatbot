import streamlit as st
from groq import Groq
import sqlite3
import pandas as pd
import psycopg2


# INITIALIZATION & CONFIGURATION


# API key from console.groq.com
GROQ_API_KEY = "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"

# Initialize AI client
client = Groq(api_key=GROQ_API_KEY)

# Exact schema definitions provided for tables
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

#DATABASE SETUP (SAMPLE DATA)



def connect_to_live_database():
    """Establishes a connection to your real PostgreSQL instance."""
    return psycopg2.connect(
        host="localhost",          
        database="ecommerce",  
        user="postgres",  
        password="db_password",  
        port="5432"               
    )

# Establish live connection
db_conn = connect_to_live_database()




#STREAMLIT INTERFACE


st.title("Database Chatbot")
st.write("Type a question about your data below. The app will translate it to SQL, query the database, and display the results.")

# Text input 
user_question = st.text_input(
    "What would you like to know?", 
    placeholder="e.g., Show me all products in the Electronics category with stock less than 20"
)

if user_question:
    # instruction set for the AI engine
    system_instruction = f"""
    You are a strict natural language to SQL translation system. 
    Analyze the user request and convert it into a completely standard, valid SQL query.
    
    Use this precise database schema:
    {DB_SCHEMA}
    
    Rules:
    1. Respond ONLY with the clean, executable SQL code. 
    2. Do not include markdown formatting, backticks (```sql), explanation blocks, or polite phrases.
    3. Ensure table and column names precisely match the provided schema.
    """
    
    with st.spinner("Translating question to database code..."):
        try:
            # Request translation from the model 
            ai_response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_question}
                ],
                temperature=0.0
            )
            
            generated_sql = ai_response.choices[0].message.content.strip()
            
           
            st.markdown("Generated Query")
            st.code(generated_sql, language="sql")
            
            # Execute the generated string on the database engine
            df_results = pd.read_sql_query(generated_sql, db_conn)
            
           
            st.markdown("Query Results")
            if not df_results.empty:
                st.dataframe(df_results, use_container_width=True)
                
                # offer visual graphs if numeric columns are available
                numeric_cols = df_results.select_dtypes(include=['number']).columns.tolist()
                if len(numeric_cols) > 0 and len(df_results) > 1:
                    st.markdown("#### Visual Summary")
                    st.bar_chart(df_results[numeric_cols[0]])
            else:
                st.info("The query executed successfully, but returned zero rows matching your criteria.")
                
        except Exception as error:
            st.error(f"An error occurred during execution: {error}")