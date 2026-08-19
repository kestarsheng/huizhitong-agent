from mcp.server.fastmcp import FastMCP

mcp = FastMCP("huizhitong-inventory")

_INVENTORY = {
    "P1001": {"product_id": "P1001", "product_name": "智能巡检终端", "stock": 120, "safe_stock": 50},
    "P1002": {"product_id": "P1002", "product_name": "工业温度传感器", "stock": 18, "safe_stock": 30},
}


@mcp.tool()
def query_inventory(product_id: str) -> dict:
    """查询商品库存、商品名称和安全库存。"""
    product = _INVENTORY.get(product_id)
    if product is None:
        return {"found": False, "product_id": product_id, "message": "未找到商品库存信息"}
    return {"found": True, **product}


@mcp.tool()
def analyze_inventory_risk(product_id: str) -> dict:
    """根据当前库存和安全库存判断库存风险。"""
    result = query_inventory(product_id)
    if not result["found"]:
        return result
    risk = "LOW" if result["stock"] >= result["safe_stock"] else "HIGH"
    return {**result, "risk": risk, "suggestion": "建议补货" if risk == "HIGH" else "库存正常"}


if __name__ == "__main__":
    mcp.run(transport="stdio")

