from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote_plus

from dotenv import load_dotenv


load_dotenv()


DEFAULT_ODBC_DRIVER = "ODBC Driver 18 for SQL Server"


@dataclass(frozen=True)
class DatabaseConfig:
    odbc_driver: str = os.getenv("DB_ODBC_DRIVER", DEFAULT_ODBC_DRIVER)
    connect_timeout_seconds: int = int(os.getenv("DB_CONNECT_TIMEOUT", "15"))
    login_timeout_seconds: int = int(os.getenv("DB_LOGIN_TIMEOUT", "15"))
    local_connection_string: str | None = os.getenv("LOCAL_DB_CONNECTION_STRING")
    cloud_connection_string: str | None = os.getenv("CLOUD_DB_CONNECTION_STRING")
    local_server: str = os.getenv("LOCAL_DB_SERVER", ".")
    local_instance: str = os.getenv("LOCAL_DB_INSTANCE", "MSSQLSERVER")
    local_port: str = os.getenv("LOCAL_DB_PORT", "1433")
    local_database: str = os.getenv("LOCAL_DB_NAME", "APCRAS")
    local_user: str = os.getenv("LOCAL_DB_USER", "sa")
    local_password: str = os.getenv("LOCAL_DB_PASSWORD", "")

    def get_connection_string(self) -> str:
        if self.cloud_connection_string:
            return self._ensure_timeouts(self.cloud_connection_string)
        if self.local_connection_string:
            return self._ensure_timeouts(self.local_connection_string)
        return self._ensure_timeouts(self._build_local_connection_string())

    def get_sqlalchemy_url(self) -> str:
        odbc_connect = quote_plus(self.get_connection_string())
        return f"mssql+pyodbc:///?odbc_connect={odbc_connect}"

    def _build_local_connection_string(self) -> str:
        server = self.local_server
        if self.local_instance and self.local_instance.upper() != "MSSQLSERVER":
            server = f"{server}\\{self.local_instance}"
        elif self.local_port:
            server = f"{server},{self.local_port}"

        parts = [
            f"DRIVER={{{self.odbc_driver}}}",
            f"SERVER={server}",
            f"DATABASE={self.local_database}",
            f"UID={self.local_user}",
            f"PWD={self.local_password}",
            "TrustServerCertificate=yes",
            "Encrypt=no",
        ]
        return ";".join(parts)

    def _ensure_timeouts(self, connection_string: str) -> str:
        lower = connection_string.lower()
        parts = [connection_string.rstrip(";")]

        if "connection timeout=" not in lower and "connect timeout=" not in lower:
            parts.append(f"Connection Timeout={self.connect_timeout_seconds}")
        if "login timeout=" not in lower:
            parts.append(f"Login Timeout={self.login_timeout_seconds}")

        return ";".join(part for part in parts if part)
