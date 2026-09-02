# Data Quality Dashboard - Databricks Unity Catalog Integration

An interactive, self-service Streamlit application that empowers data teams to build, configure, and execute Great Expectations data quality rules directly against Databricks Unity Catalog tables.

## 🚀 Features
- **Direct Unity Catalog Integration:** Streams data securely from Databricks SQL Warehouses using OAuth M2M (Service Principals).
- **Dynamic Rule Configuration:** Build data quality checks on the fly from any Great Expectations rule.
- **Interactive UI:** Select columns, browse categories, and configure complex rule parameters without writing code.
- **Comprehensive Reporting:** Get instant visualizations on pass/fail rates, DQ scores, and granular rule results.
- **Databricks Apps Native:** Designed to be deployed effortlessly as a Databricks App, leveraging native environment variables and automatic authentication.

## 📸 Dashboard Walkthrough

### 1. Data Preview (Unity Catalog)
The app successfully connects to Databricks and fetches live data.
![Data Preview](images/data_preview.png)

### 2. Configure Data Quality Rules
Interactively select columns, apply regex matching, check for nulls, validate ranges, and enforce uniqueness.
![Configure Rules](images/rules_config.png)

### 3. Execution & Summary Dashboard
Run the checks and instantly view the Data Quality Score, passing metrics, and detailed failure percentage charts.
![DQ Summary](images/dashboard.png)

### 4. Databricks App Deployment
Fully integrated with Databricks Apps for secure, serverless hosting.
![Databricks App](images/databricks_app.png)

## 🛠️ Tech Stack
- **Frontend:** Streamlit
- **Data Processing:** Pandas, Databricks SQL Connector
- **Data Quality Engine:** Great Expectations
- **Hosting:** Databricks Apps

## 💻 Local Setup
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Add your credentials to `.streamlit/secrets.toml`:
```toml
DATABRICKS_SERVER_HOSTNAME = "your-hostname"
DATABRICKS_HTTP_PATH = "your-http-path"
DATABRICKS_TOKEN = "your-pat"
```
4. Run locally: `streamlit run app.py`
