import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def verify():
    if not DATABASE_URL:
        print("DATABASE_URL not found in .env")
        return

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Check tables
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'")
        tables = [t[0] for t in cur.fetchall()]
        print(f"Total Tables: {len(tables)}")
        
        # Check actor count (using public prefix just in case)
        cur.execute("SELECT count(*) FROM public.actor")
        actor_count = cur.fetchone()[0]
        print(f"Actor Count: {actor_count}")
        
        # Check film count
        cur.execute("SELECT count(*) FROM public.film")
        film_count = cur.fetchone()[0]
        print(f"Film Count: {film_count}")
        
        if actor_count == 200:
            print("\nVerification PASSED: Data successfully migrated.")
        else:
            print(f"\nVerification FAILED: Expected 200 actors, found {actor_count}")

        conn.close()
    except Exception as e:
        print(f"Verification Error: {e}")

if __name__ == "__main__":
    verify()
