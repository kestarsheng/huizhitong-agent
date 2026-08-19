from dataclasses import dataclass
from app.tools.mcp_inventory_gateway import McpInventoryGateway


@dataclass(frozen=True)
class InventoryToolGateway:
    """库存工具调用边界，后续可替换为 MCP Client 实现。"""

    _inventory: dict[str, dict] = None

    def __post_init__(self) -> None:
        if self._inventory is None:
            object.__setattr__(self, "_inventory", {
                "P1001": {"product_id": "P1001", "product_name": "智能巡检终端", "stock": 120, "safe_stock": 50},
                "P1002": {"product_id": "P1002", "product_name": "工业温度传感器", "stock": 18, "safe_stock": 30},
            })

    def analyze(self, product_id: str) -> dict:
        product = self._inventory.get(product_id)
        if product is None:
            return {"found": False, "product_id": product_id, "message": "未找到商品库存信息"}
        risk = "LOW" if product["stock"] >= product["safe_stock"] else "HIGH"
        return {**product, "found": True, "risk": risk,
                "suggestion": "建议补货" if risk == "HIGH" else "库存正常"}


inventory_gateway = InventoryToolGateway()
mcp_inventory_gateway = McpInventoryGateway()

