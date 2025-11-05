import os
import asyncio
from typing import Optional
import psycopg
import boto3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Global variable for database connection
_db_context = None


class DbContext:
    def __init__(self):
        self.cluster_id = os.getenv('DSQL_CLUSTER_ID')
        self.region = os.getenv('DSQL_REGION')
        self.host = os.getenv('DSQL_HOST')
        self.port = int(os.getenv('DSQL_PORT', '5432'))
        self.database = os.getenv('DSQL_DATABASE', 'postgres')
        self.username = os.getenv('DSQL_USERNAME', 'admin')
        
        if not all([self.cluster_id, self.region, self.host]):
            raise ValueError("Missing required DSQL environment variables")
    
    def _generate_auth_token(self) -> str:
        """Generate IAM auth token for Aurora DSQL"""
        client = boto3.client('dsql', region_name=self.region)
        return client.generate_db_connect_admin_auth_token(
            Hostname=self.host,
            ExpiresIn=3600
        )
    
    async def execute_query(self, query: str) -> str:
        """Execute a query and return formatted results"""
        try:
            # Generate fresh token for each query
            password = self._generate_auth_token()
            
            conn_params = {
                'host': self.host,
                'port': self.port,
                'dbname': self.database,
                'user': self.username,
                'password': password,
                'sslmode': 'require'
            }
            
            async with await psycopg.AsyncConnection.connect(**conn_params) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query)
                    
                    if cur.description:
                        rows = await cur.fetchall()
                        if not rows:
                            return "No results found."
                        
                        headers = [desc[0] for desc in cur.description]
                        return self._format_table(headers, rows)
                    else:
                        return f"Query executed successfully. Rows affected: {cur.rowcount}"
                        
        except Exception as e:
            return f"SQL Error: {str(e)}"
    
    def _format_table(self, headers, rows):
        """Format as CSV"""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerows(rows)
        return output.getvalue()


def get_db_context() -> DbContext:
    """Get the current database context"""
    if _db_context is None:
        raise RuntimeError("Database context not set. Initialize with set_db_context() first.")
    return _db_context


def set_db_context(ctx: DbContext):
    """Set the database context"""
    global _db_context
    _db_context = ctx
