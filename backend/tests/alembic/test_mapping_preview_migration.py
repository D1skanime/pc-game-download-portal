from pathlib import Path


def test_mapping_preview_migration_follows_mapping_administration():
    source = Path("alembic/versions/0110_mapping_preview_results.py").read_text()
    assert 'down_revision = "0109_mapping_admin_contracts"' in source
    assert "mapping_previews" in source
    assert "def downgrade()" in source
