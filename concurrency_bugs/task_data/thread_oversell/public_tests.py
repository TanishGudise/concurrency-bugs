from decimal import Decimal

import pytest
from shop import Checkout, Inventory, LineItem, OrderRejected


class ListAudit:
    def __init__(self):
        self.records = []

    def record(self, item, quantity, ok):
        self.records.append((item, quantity, ok))


def test_reserve_within_stock():
    audit = ListAudit()
    inventory = Inventory({"widget": 3}, audit)
    assert inventory.reserve("widget", 2) is True
    assert inventory.available("widget") == 1
    assert audit.records == [("widget", 2, True)]


def test_reserve_more_than_stock_fails_without_changes():
    audit = ListAudit()
    inventory = Inventory({"widget": 1}, audit)
    assert inventory.reserve("widget", 2) is False
    assert inventory.available("widget") == 1
    assert audit.records == [("widget", 2, False)]


def test_failed_order_releases_earlier_lines():
    inventory = Inventory({"widget": 5, "gadget": 0}, ListAudit())
    checkout = Checkout(inventory, {"widget": Decimal("2.50"), "gadget": Decimal("10")})
    with pytest.raises(OrderRejected):
        checkout.place_order([LineItem("widget", 2), LineItem("gadget", 1)])
    assert inventory.available("widget") == 5
    order = checkout.place_order([LineItem("widget", 2)])
    assert order.total == Decimal("5.00")
