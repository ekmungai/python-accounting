from datetime import datetime
from decimal import Decimal

from python_accounting.models import Account, Currency, Entity, LineItem
from python_accounting.transactions import CashSale


def test_current_period_follows_the_year_start(session, monkeypatch):
    """Before the year start month, the current period is the one that began last year"""

    year = datetime.now().year

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(year, 3, 15, 12, tzinfo=tz)

        @classmethod
        def today(cls):
            return cls.now()

    for module in (
        "python_accounting.database.accounting_functions",
        "python_accounting.database.event_listeners",
    ):
        monkeypatch.setattr(f"{module}.datetime", FixedDateTime)

    entity = Entity(name="July Year Start", year_start=7)
    session.add(entity)
    session.commit()
    entity = session.get(Entity, entity.id)

    assert entity.reporting_period.calendar_year == year - 1
    assert entity.reporting_period.interval()["start"] == datetime(year - 1, 7, 1)

    currency = Currency(name="Australian Dollars", code="AUD", entity_id=entity.id)
    session.add(currency)
    session.flush()
    bank = Account(
        name="Bank",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    revenue = Account(
        name="Revenue",
        account_type=Account.AccountType.OPERATING_REVENUE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add_all([bank, revenue])
    session.flush()

    cash_sale = CashSale(
        narration="Sale in March",
        transaction_date=datetime(year, 3, 10),
        account_id=bank.id,
        entity_id=entity.id,
    )
    session.add(cash_sale)
    session.flush()
    line_item = LineItem(
        narration="Sale line",
        account_id=revenue.id,
        amount=Decimal(100),
        entity_id=entity.id,
    )
    session.add(line_item)
    session.flush()
    cash_sale.line_items.add(line_item)
    session.flush()
    cash_sale.post(session)

    assert cash_sale.is_posted
