import os
import pandas as pd
import streamlit as st
from databricks import sql

@st.cache_data(show_spinner=False)
def load_databricks_table(table_name="customer_dq") -> pd.DataFrame:
    """
    Connects to Databricks SQL Warehouse and queries a Unity Catalog table,
    returning the results as a Pandas DataFrame.
    """
    server_hostname = os.environ.get("DATABRICKS_SERVER_HOSTNAME")
    http_path = os.environ.get("DATABRICKS_HTTP_PATH")
    access_token = os.environ.get("DATABRICKS_TOKEN")
    
    if not all([server_hostname, http_path, access_token]):
        raise ValueError("Databricks connection environment variables are missing.")

    connection = sql.connect(
        server_hostname=server_hostname,
        http_path=http_path,
        access_token=access_token
    )
    
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT * FROM {table_name}")
        result = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(result, columns=columns)
        
    return df
