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
    # Try to get native Databricks App environment variables
    server_hostname = os.environ.get("DATABRICKS_HOST") or os.environ.get("DATABRICKS_SERVER_HOSTNAME")
    access_token = os.environ.get("DATABRICKS_TOKEN")
    client_id = os.environ.get("DATABRICKS_CLIENT_ID")
    client_secret = os.environ.get("DATABRICKS_CLIENT_SECRET")
    
    warehouse_id = os.environ.get("DATABRICKS_WAREHOUSE_ID")
    if warehouse_id:
        http_path = f"/sql/1.0/warehouses/{warehouse_id}"
    else:
        http_path = os.environ.get("DATABRICKS_HTTP_PATH")
    
    if not server_hostname or not http_path:
        raise ValueError("Databricks connection environment variables (hostname or http_path) are missing.")

    if client_id and client_secret:
        # Use Databricks Apps Service Principal (OAuth)
        from databricks.sdk.core import Config
        config = Config(host=server_hostname, client_id=client_id, client_secret=client_secret)
        connection = sql.connect(
            server_hostname=server_hostname,
            http_path=http_path,
            credentials_provider=lambda: config.authenticate
        )
    elif access_token:
        # Use Personal Access Token (for local testing)
        connection = sql.connect(
            server_hostname=server_hostname,
            http_path=http_path,
            access_token=access_token
        )
    else:
        raise ValueError("Databricks credentials missing (no token or OAuth credentials found).")
    
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT * FROM {table_name}")
        result = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(result, columns=columns)
        
    return df
