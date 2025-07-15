# Pharma France Insight Backend

This is a mock FastAPI backend for Pharma France Insight.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env.local` file in the `backend` directory with the following content:
   ```
   AZURE_SQL_SERVER=your_server_name
   AZURE_SQL_DATABASE=your_database_name
   AZURE_SQL_USERNAME=your_username
   AZURE_SQL_PASSWORD=your_password
   ```
   Replace the placeholders with your actual Azure SQL connection details.

3. Run the server:
   ```bash
   uvicorn main:app --reload
   ```

The API will be available at http://127.0.0.1:8000 