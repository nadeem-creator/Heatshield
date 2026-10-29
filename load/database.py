"""Manage PostgreSQL database access."""
import os
import psycopg
from dotenv import load_dotenv

def get_db_connection():
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL is missing. Add it to your .env file.")

    return psycopg.connect(database_url)

if __name__ == "__main__":
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_database(), NOW();")
                database_name, connected_at = cursor.fetchone()

                print(f"Connected to database: {database_name}")
                print(f"Connection time: {connected_at}")

    except Exception as error:
        print(f"Database connection failed: {error}")
