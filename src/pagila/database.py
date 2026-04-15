import psycopg2

def get_connection(db_url):
    return psycopg2.connect(db_url)

def execute_sql(conn, sql_content, description):
    if not sql_content.strip():
        return
    print(f"Executing {description}...")
    with conn.cursor() as cur:
        try:
            cur.execute(sql_content)
            conn.commit()
            print(f"Successfully executed {description}")
        except Exception as e:
            conn.rollback()
            print(f"Error executing {description}: {e}")
            raise

def reset_database(conn):
    print("Resetting database (dropping/creating schemas)...")
    with conn.cursor() as cur:
        cur.execute("DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;")
        cur.execute("DROP SCHEMA IF EXISTS legacy CASCADE;")
        conn.commit()
    print("Database reset complete.")
