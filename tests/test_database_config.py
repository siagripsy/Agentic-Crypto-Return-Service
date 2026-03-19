from core.config.database_config import DatabaseConfig


def test_database_config_prefers_cloud_connection_string():
    cfg = DatabaseConfig(
        local_connection_string="LOCAL",
        cloud_connection_string="CLOUD",
    )
    conn = cfg.get_connection_string()
    assert conn.startswith("CLOUD")
    assert "Connection Timeout=15" in conn
    assert "Login Timeout=15" in conn


def test_database_config_builds_local_connection_string_from_parts():
    cfg = DatabaseConfig(
        local_connection_string=None,
        cloud_connection_string=None,
        local_server=".",
        local_instance="MSSQLSERVER",
        local_port="1433",
        local_database="APCRAS",
        local_user="sa",
        local_password="123",
    )
    conn = cfg.get_connection_string()
    assert "SERVER=.,1433" in conn
    assert "DATABASE=APCRAS" in conn
    assert "UID=sa" in conn
    assert "PWD=123" in conn
    assert "Connection Timeout=15" in conn
    assert "Login Timeout=15" in conn


def test_database_config_adds_timeouts_to_cloud_connection_string():
    cfg = DatabaseConfig(
        cloud_connection_string="DRIVER={ODBC Driver 18 for SQL Server};SERVER=db;DATABASE=APCRAS;UID=sa;PWD=123",
    )

    conn = cfg.get_connection_string()

    assert "Connection Timeout=15" in conn
    assert "Login Timeout=15" in conn


def test_database_config_keeps_existing_timeout_values():
    cfg = DatabaseConfig(
        cloud_connection_string=(
            "DRIVER={ODBC Driver 18 for SQL Server};SERVER=db;DATABASE=APCRAS;"
            "UID=sa;PWD=123;Connection Timeout=5;Login Timeout=7"
        ),
    )

    conn = cfg.get_connection_string()

    assert conn.count("Connection Timeout=") == 1
    assert conn.count("Login Timeout=") == 1
