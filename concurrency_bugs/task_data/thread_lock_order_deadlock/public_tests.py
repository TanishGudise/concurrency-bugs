import pytest
from bank import Account, Bank, InsufficientFunds


def test_transfer_moves_money():
    a, b = Account(1, 100), Account(2, 50)
    bank = Bank([a, b])
    bank.transfer(a, b, 30)
    assert (a.balance, b.balance) == (70, 80)
    assert bank.total() == 150


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
