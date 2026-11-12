"""Manage PostgreSQL database access."""
import os
import socket

import psycopg
from dotenv import load_dotenv
from psycopg.conninfo import conninfo_to_dict


def get_db_connection():
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL is missing. Add it to your .env file.")

    hostname = conninfo_to_dict(database_url).get("host")
    hostaddr = socket.gethostbyname(hostname) if hostname else None
    return psycopg.connect(database_url, hostaddr=hostaddr)


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
