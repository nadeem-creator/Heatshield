"""Test database connection configuration without external services."""

import os
import unittest
from unittest.mock import patch

from load.database import get_db_connection


class DatabaseConnectionTests(unittest.TestCase):
    @patch("load.database.psycopg.connect")
    @patch("load.database.socket.gethostbyname", return_value="192.0.2.1")
    @patch("load.database.load_dotenv")
    def test_connects_with_resolved_ipv4_address(
        self,
        _load_dotenv,
        gethostbyname,
        connect,
    ):
        database_url = "postgresql://user:password@db.example.test/database"

        with patch.dict(os.environ, {"DATABASE_URL": database_url}, clear=True):
            get_db_connection()

        gethostbyname.assert_called_once_with("db.example.test")
        connect.assert_called_once_with(database_url, hostaddr="192.0.2.1")

    @patch("load.database.load_dotenv")
    def test_rejects_missing_database_url(self, _load_dotenv):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "DATABASE_URL is missing"):
                get_db_connection()


if __name__ == "__main__":
    unittest.main()
