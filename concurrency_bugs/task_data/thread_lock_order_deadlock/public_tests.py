import pytest
from bank import Account, Bank, InsufficientFunds, statement


def test_transfer_moves_money_and_is_audited():
    a, b = Account(1, 10_000, "ada"), Account(2, 5_000, "bob")
    bank = Bank([a, b])
    bank.transfer(a, b, 3_000)
    assert (a.balance, b.balance) == (7_000, 8_000)
    assert bank.total() == 15_000
    assert [(e.src, e.dst, e.amount) for e in bank.audit.entries()] == [(1, 2, 3_000)]
    assert bank.audit.volume(2) == 3_000


def test_insufficient_funds_changes_nothing():
    a, b = Account(1, 10), Account(2, 0)
    bank = Bank([a, b])
    with pytest.raises(InsufficientFunds):
        bank.transfer(a, b, 11)
    assert (a.balance, b.balance) == (10, 0)


def test_invalid_transfers_are_rejected():
    a, b = Account(1, 10), Account(2, 0)
    bank = Bank([a, b])
    with pytest.raises(ValueError):
        bank.transfer(a, b, 0)
    with pytest.raises(ValueError):
        bank.transfer(a, a, 5)


def test_statement_formats_cents():
    assert statement(Account(7, 12_345, "ada")) == "#7 ada: 123.45 USD"
