from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_phase18_backend_runner_uses_only_the_compose_network_database():
    runner = REPO_ROOT / "backend/tools/verify_phase18_backend_tests.sh"
    contents = runner.read_text()

    assert "set -Eeuo pipefail" in contents
    assert "docker compose exec -T romm-db-dev" in contents
    assert "docker compose exec -T romm-dev" in contents
    assert "DB_HOST=romm-db-dev" in contents
    assert "DB_PORT=3306" in contents
    assert "127.0.0.1" not in contents
    assert "DROP DATABASE IF EXISTS" in contents


def test_0115_creates_the_postgresql_enum_without_table_recreation():
    migration = (
        REPO_ROOT / "backend/alembic/versions/20260831_add_pc_rom_components.py"
    ).read_text()

    assert "from sqlalchemy.dialects.postgresql import ENUM" in migration
    assert "create_type=False" in migration
    assert "component_kind.create(connection, checkfirst=True)" in migration


def test_0116_creates_the_postgresql_enum_without_table_recreation():
    migration = (
        REPO_ROOT / "backend/alembic/versions/0116_pc_component_local_media.py"
    ).read_text()

    assert "from sqlalchemy.dialects.postgresql import ENUM" in migration
    assert "create_type=False" in migration
    assert "media_role.create(connection, checkfirst=True)" in migration
