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

<img width="1832" height="948" alt="Screenshot 2026-09-02 120403" src="https://github.com/user-attachments/assets/45f8f63c-6089-4046-ae60-3e7a0377aea3" />


### 2. Configure Data Quality Rules
Interactively select columns, apply regex matching, check for nulls, validate ranges, and enforce uniqueness.

<img width="1850" height="950" alt="Screenshot 2026-09-02 120512" src="https://github.com/user-attachments/assets/11cbe9cf-1475-4a39-95eb-7c602682ed09" />


### 3. Execution & Summary Dashboard
Run the checks and instantly view the Data Quality Score, passing metrics, and detailed failure percentage charts.

<img width="1852" height="1112" alt="Screenshot 2026-09-02 120448" src="https://github.com/user-attachments/assets/9f53e55e-8afe-4495-a7a2-14a23ebdae24" />


### 4. Databricks App Deployment
Fully integrated with Databricks Apps for secure, serverless hosting.

<img width="1897" height="883" alt="Screenshot 2026-09-02 120343" src="https://github.com/user-attachments/assets/eb99617f-3804-4e3f-a909-890325bd1bdb" />


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
