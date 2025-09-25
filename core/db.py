import psycopg2
from core.config import AppConfig


def get_connection(config: AppConfig = None):
    """PostgreSQL 연결을 생성합니다. 설정된 스키마와 public을 search_path로 사용합니다."""
    cfg = config or AppConfig()
    schema = cfg.db_schema
    search_path = schema if isinstance(schema, str) else ",".join(schema)
    return psycopg2.connect(
        host=cfg.db_host,
        dbname=cfg.db_name,
        user=cfg.db_user,
        password=cfg.db_password,
        options=f"-c search_path={search_path},public"
    )


