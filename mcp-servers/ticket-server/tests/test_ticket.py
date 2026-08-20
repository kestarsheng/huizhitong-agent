from app.server import create_ticket, query_ticket


def test_create_ticket() -> None:
    result = create_ticket("设备报修", "设备 E-1024 重启后仍报错", priority="HIGH", customer_id="C-001")
    assert result["created"] is True
    assert result["status"] == "OPEN"
    assert result["priority"] == "HIGH"
    assert result["ticket_id"].startswith("TK-")


def test_query_ticket_roundtrip() -> None:
    created = create_ticket("售后咨询", "查询保修期政策", priority="LOW")
    found = query_ticket(created["ticket_id"])
    assert found["found"] is True
    assert found["subject"] == "售后咨询"
    assert found["status"] == "OPEN"


def test_create_ticket_validation() -> None:
    empty = create_ticket("", "空主题")
    assert empty["created"] is False
    invalid_priority = create_ticket("主题", "描述", priority="URGENT")
    assert invalid_priority["created"] is False


def test_query_missing_ticket() -> None:
    result = query_ticket("TK-0000")
    assert result["found"] is False
