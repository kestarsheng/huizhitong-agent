from app.server import analyze_inventory_risk, query_inventory


def test_query_inventory() -> None:
    result = query_inventory("P1001")
    assert result["found"] is True
    assert result["stock"] == 120


def test_inventory_risk() -> None:
    result = analyze_inventory_risk("P1002")
    assert result["risk"] == "HIGH"
    assert result["suggestion"] == "建议补货"

