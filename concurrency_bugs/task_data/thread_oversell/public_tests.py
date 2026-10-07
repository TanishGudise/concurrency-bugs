import pytest
from inventory import Inventory


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
    assert inventory.reserve("gadget", 1) is False
    assert inventory.available("widget") == 1
    assert audit.records == [("widget", 2, False), ("gadget", 1, False)]


def test_quantity_must_be_positive():
    inventory = Inventory({"widget": 1}, ListAudit())
    with pytest.raises(ValueError):
        inventory.reserve("widget", 0)
