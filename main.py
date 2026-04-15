import os
from dotenv import load_dotenv
from src.pagila import get_connection, execute_sql, reset_database, clean_sql

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def run_migration():
    if not DATABASE_URL:
        print("DATABASE_URL not found in .env")
        return

    try:
        print("Connecting to Neon...")
        conn = get_connection(DATABASE_URL)
        conn.autocommit = False
        
        # 0. Reset Database
        reset_database(conn)
        
        # 1. Load and clean Schema
        schema_path = os.path.join("sql", "pagila-schema.sql")
        print(f"Reading {schema_path}...")
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_content = f.read()
        
        schema_base, schema_constraints = clean_sql(schema_content)
        
        # 2. Load and clean Data
        data_path = os.path.join("sql", "pagila-insert-data.sql")
        print(f"Reading {data_path}...")
        with open(data_path, "r", encoding="utf-8") as f:
            data_content = f.read()
        data_cleaned, _ = clean_sql(data_content)
        
        # 3. Execution Sequence: Base Schema -> Data -> Constraints
        execute_sql(conn, schema_base, "Base Schema")
        execute_sql(conn, data_cleaned, "Data Insertion")
        execute_sql(conn, schema_constraints, "FK Constraints")
        
        print("\nMigration completed successfully!")
        
    except Exception as e:
        print(f"\nMigration failed: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    run_migration()
