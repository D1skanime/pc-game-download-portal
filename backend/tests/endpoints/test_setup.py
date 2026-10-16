def test_setup_discovery_has_bounded_relative_contract(client, monkeypatch):
    from endpoints import setup

    monkeypatch.setattr(setup.db_user_handler, "get_admin_users", lambda: [])
    monkeypatch.setattr(
        setup.setup_folder_handler,
        "discover_response",
        lambda: {
            "root_label": "Games",
            "folders": [
                {
                    "name": "Windows",
                    "relative_path": "Windows",
                    "association": "known",
                    "suggested_platform": "win",
                }
            ],
            "platform_options": [{"slug": "win", "display_name": "Windows"}],
        },
    )

    response = client.get("/api/setup/folders")

    assert response.status_code == 200
    body = response.json()
    assert body["root_label"] == "Games"
    assert body["folders"][0]["relative_path"] == "Windows"
    assert "/" not in body["folders"][0]["relative_path"]
    assert "container_path" not in body


def test_setup_assignment_requires_admin_write_scope(client, viewer_access_token):
    response = client.post(
        "/api/setup/folders/assign",
        headers={"Authorization": f"Bearer {viewer_access_token}"},
        json={"assignments": [{"folder_name": "Windows", "platform_slug": "win"}]},
    )
    assert response.status_code in {401, 403}


def test_setup_contract_does_not_reintroduce_legacy_structure_detection():
    source = open("endpoints/setup.py", encoding="utf-8").read()
    assert "detect_library_structure" not in source
    assert "roms/{platform}" not in source
