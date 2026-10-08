"""Order placement: reserve every line item, price the order, roll back on failure."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from shop.inventory import Inventory


class OrderRejected(Exception):
    pass


@dataclass(frozen=True)
class LineItem:
    sku: str
    quantity: int


@dataclass(frozen=True)
class Order:
    lines: tuple[LineItem, ...]
    total: Decimal


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class Checkout:
    def __init__(
        self, inventory: Inventory, prices: dict[str, Decimal], *, bulk_discount: Decimal = Decimal("0.1")
    ):
        self._inventory = inventory
        self._prices = prices
        self._bulk_discount = bulk_discount

    def price(self, lines: list[LineItem]) -> Decimal:
        total = Decimal(0)
        for line in lines:
            unit = self._prices[line.sku]
            subtotal = unit * line.quantity
            if line.quantity >= 10:
                subtotal -= subtotal * self._bulk_discount
            total += subtotal
        return _money(total)

    def place_order(self, lines: list[LineItem]) -> Order:
        """Reserve all line items or none of them."""
        reserved: list[LineItem] = []
        try:
            for line in lines:
                if line.sku not in self._prices:
                    raise OrderRejected(f"unknown item {line.sku!r}")
                if not self._inventory.reserve(line.sku, line.quantity):
                    raise OrderRejected(f"not enough {line.sku!r} in stock")
                reserved.append(line)
        except Exception:
            for line in reserved:
                self._inventory.release(line.sku, line.quantity)
            raise
        return Order(lines=tuple(lines), total=self.price(lines))
