from fastapi import status


def _headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def test_transfer_history_requires_authentication(client, manifest):
    response = client.get(f"/api/download-transfer-sessions/{manifest.id}")
    assert response.status_code in (
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_404_NOT_FOUND,
    )


def test_transfer_payload_rejects_unknown_fields(client, access_token, manifest):
    response = client.post(
        "/api/download-transfer-sessions",
        headers=_headers(access_token),
        json={"manifest_id": manifest.id, "mode": "standard", "path": "/tmp/x"},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_standard_transfer_response_does_not_claim_local_storage(
    client, access_token, manifest
):
    created = client.post(
        "/api/download-transfer-sessions",
        headers=_headers(access_token),
        json={"manifest_id": manifest.id, "mode": "standard"},
    )
    assert created.status_code == status.HTTP_201_CREATED
    body = created.json()
    assert body["mode"] == "standard"
    assert all(item["status"] == "queued" for item in body["items"])
    assert all(
        forbidden not in created.text
        for forbidden in ("source_path", "fs_path", "file://", "token", "credential")
    )
