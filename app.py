import os
import re
import streamlit as st
from groq import Groq
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from schema import DB_SCHEMA


load_dotenv()

def get_config(key: str) -> str:
    
    try:
        if key in st.secrets:
            return st.secrets[key]
    except FileNotFoundError:
        pass
    value = os.getenv(key)
    if not value:
        st.error(f"Missing required config value: {key}")
        st.stop()
    return value

GROQ_API_KEY = get_config("GROQ_API_KEY")
DB_HOST = get_config("DB_HOST")
DB_PORT = get_config("DB_PORT")
DB_NAME = get_config("DB_NAME")
DB_USER = get_config("DB_USER")
DB_PASSWORD = get_config("DB_PASSWORD")

client = Groq(api_key=GROQ_API_KEY)



@st.cache_resource
def connect_to_live_database():
    """Establishes a connection to the PostgreSQL instance (e.g. Neon)."""
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
        sslmode="require",
    )

def get_db_connection():
    """Returns a live DB connection, transparently reconnecting if the
    cached one has died (e.g. Neon auto-suspended it after inactivity)."""
    conn = connect_to_live_database()
    try:
       
        if conn.closed != 0:
            raise psycopg2.OperationalError("cached connection is closed")
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
    except (psycopg2.OperationalError, psycopg2.InterfaceError):
        connect_to_live_database.clear()  
        conn = connect_to_live_database()  
    return conn



FORBIDDEN_KEYWORDS = [
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE",
    "CREATE", "GRANT", "REVOKE", "EXEC", "EXECUTE", "MERGE",
    "REPLACE", "ATTACH", "DETACH", "COPY", "CALL", "DO",
]

def is_safe_select(sql: str) -> bool:
    """Returns True only if the query is a single, read-only SELECT statement."""
    cleaned = sql.strip().rstrip(";")

   
    if not re.match(r"^\s*(WITH\b.*?\bSELECT|SELECT)\b", cleaned, re.IGNORECASE | re.DOTALL):
        return False

   
    if ";" in cleaned:
        return False

   
    upper_sql = cleaned.upper()
    for word in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{word}\b", upper_sql):
            return False

    return True



st.title("Database Chatbot")
st.write(
    "Type a question about your data below. The app will translate it to SQL, "
    "query the database, and display the results."
)

user_question = st.text_input(
    "What would you like to know?",
    placeholder="e.g., Show me all products in the Electronics category with stock less than 20",
)

if user_question:
    system_instruction = f"""
    You are a strict natural language to SQL translation system.
    Analyze the user request and convert it into a completely standard, valid SQL query.

    Use this precise database schema:
    {DB_SCHEMA}

    Rules:
    1. Respond ONLY with the clean, executable SQL code.
    2. Do not include markdown formatting, backticks (```sql), explanation blocks, or polite phrases.
    3. Ensure table and column names precisely match the provided schema.
    4. Only ever generate a single read-only SELECT query. Never generate INSERT, UPDATE,
       DELETE, DROP, ALTER, or any other statement that modifies data or schema.
    """

    with st.spinner("Translating question to database code..."):
        try:
            ai_response = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_question},
                ],
                temperature=0.0,
            )

            generated_sql = ai_response.choices[0].message.content.strip()
           
            generated_sql = re.sub(r"^```sql|```$", "", generated_sql, flags=re.IGNORECASE).strip()

            st.markdown("Generated Query")
            st.code(generated_sql, language="sql")

            if not is_safe_select(generated_sql):
                st.error(
                    "This query was blocked because it isn't a safe, read-only SELECT statement. "
                    "Try rephrasing your question."
                )
            else:
                df_results = pd.read_sql_query(generated_sql, get_db_connection())

                st.markdown("Query Results")
                if not df_results.empty:
                    st.dataframe(df_results, use_container_width=True)

                    numeric_cols = df_results.select_dtypes(include=["number"]).columns.tolist()
                    if len(numeric_cols) > 0 and len(df_results) > 1:
                        st.markdown("#### Visual Summary")
                        st.bar_chart(df_results[numeric_cols[0]])
                else:
                    st.info("The query executed successfully, but returned zero rows matching your criteria.")

        except Exception as error:
            st.error(f"An error occurred during execution: {error}")