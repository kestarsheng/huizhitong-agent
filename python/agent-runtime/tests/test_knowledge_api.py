from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_add_document() -> None:
    response = client.post(
        "/internal/knowledge/documents",
        json={
            "document_id": "return-policy",
            "content": "退货规则：签收后七天内支持无理由退货，退回商品需保持完好。",
            "tenant_id": "t-1",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["document_id"] == "return-policy"
    assert body["tenant_id"] == "t-1"
    assert body["chunk_count"] >= 1


def test_list_documents() -> None:
    response = client.get("/internal/knowledge/documents")
    assert response.status_code == 200
    ids = [doc["document_id"] for doc in response.json()]
    assert "equipment-manual" in ids
    assert "after-sales-policy" in ids


def test_duplicate_document_conflict() -> None:
    first = client.post(
        "/internal/knowledge/documents",
        json={"document_id": "dup-doc", "content": "重复文档内容，用于冲突校验。"},
    )
    assert first.status_code == 201
    second = client.post(
        "/internal/knowledge/documents",
        json={"document_id": "dup-doc", "content": "再次提交相同文档 ID。"},
    )
    assert second.status_code == 409


def test_document_validation() -> None:
    response = client.post(
        "/internal/knowledge/documents",
        json={"document_id": "非法 ID", "content": "文档内容。"},
    )
    assert response.status_code == 422
