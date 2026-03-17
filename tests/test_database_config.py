from core.config.database_config import DatabaseConfig


def test_database_config_prefers_cloud_connection_string():
    cfg = DatabaseConfig(
        local_connection_string="LOCAL",
        cloud_connection_string="CLOUD",
    )
    assert cfg.get_connection_string() == "CLOUD"


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

