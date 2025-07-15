from __future__ import annotations

import json
from decimal import Decimal
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

class AzureSQLConnection:
    def __init__(self, server, database, username, password, logger, driver='{ODBC Driver 18 for SQL Server}'):
        self.conn_str = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}'
        self.logger = logger

    def test_connection(self):
        try:
            conn = pyodbc.connect(self.conn_str)
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            row = cursor.fetchone()
            if row:
                self.logger.info('Connection successful')
            conn.close()
            return True
        except pyodbc.Error as e:
            self.logger.error(f'Connection test failed: {str(e)}')
            return False

    def execute_query(self, query, params=None):
        try:
            conn = pyodbc.connect(self.conn_str)
            cursor = conn.cursor()

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # For SELECT queries, return results
            if cursor.description:
                # Retrieve column names from the result
                columns = [column[0] for column in cursor.description]
                # Map each row to a dictionary using the column names
                results = [
                    dict(zip(columns, row))
                    for row in cursor.fetchall()
                ]
                conn.close()
                # Convert Decimals to float if needed
                data = json.dumps(
                    results, indent=4, default=lambda o: float(
                        o,
                    ) if isinstance(o, Decimal) else o,
                )
                return data
            else:
                # For non-SELECT queries (INSERT, UPDATE, etc.)
                conn.commit()
                conn.close()
                return True

        except pyodbc.Error as e:
            if self.logger:
                self.logger.error(f'Database error: {str(e)}')
            raise Exception(f'Database error: {str(e)}') 