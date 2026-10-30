from datetime import datetime

import pytest
from sqlalchemy import select, update

from python_accounting.exceptions import AdjustingReportingPeriodError
from python_accounting.models import (
    Account,
    Balance,
    Entity,
    Recyclable,
    ReportingPeriod,
    Transaction,
)
from python_accounting.transactions import CashSale
from python_accounting.utils import reporting_period_repair as repair_module
from python_accounting.utils.reporting_period_repair import (
    CLOSED_PERIOD,
    MISSING_PERIOD,
    find,
    repair,
)

YEAR = datetime.now().year


def _account(session, entity, currency, account_type, name):
    account = Account(
        name=name,
        account_type=account_type,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add(account)
    session.flush()
    return account


def _balance(session, entity, account, **attributes):
    balance = Balance(
        transaction_date=datetime(YEAR - 2, 12, 1),
        transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
        amount=50,
        balance_type=Balance.BalanceType.DEBIT,
        account_id=account.id,
        entity_id=entity.id,
        **attributes,
    )
    session.add(balance)
    session.commit()
    return balance


def _set_created_at(session, balance, created_at):
    session.connection().execute(
        update(Recyclable.__table__)
        .where(Recyclable.__table__.c.id == balance.id)
        .values(created_at=created_at)
    )
    session.commit()


def _periods(session):
    return {
        p.calendar_year: p
        for p in session.scalars(select(ReportingPeriod)).all()
    }


@pytest.fixture
def old_rollover(session, entity, freeze_today):
    """A July Entity in its year, and a function to roll it over as earlier versions did."""

    freeze_today(YEAR - 1, 8, 15)
    session.connection().execute(
        update(ReportingPeriod.__table__)
        .where(ReportingPeriod.__table__.c.id == entity.reporting_period_id)
        .values(calendar_year=YEAR - 1)
    )
    entity.year_start = 7
    session.commit()

    def rollover():
        running = entity.reporting_period
        running.status = ReportingPeriod.Status.ADJUSTING
        session.commit()
        early = ReportingPeriod(
            calendar_year=YEAR,
            period_count=running.period_count + 1,
            entity_id=entity.id,
        )
        session.add(early)
        session.commit()
        entity.reporting_period_id = early.id
        session.commit()
        # New code would not attach Balances to the early period before it begins
        freeze_today(YEAR, 8, 15)
        return running, early

    return rollover


def test_upgrade_does_not_back_date_a_second_open_period(session, entity, freeze_today):
    """An Entity that only has the early period gets no second open period"""

    freeze_today(YEAR, 3, 15)
    entity.year_start = 7
    session.commit()
    period = entity.reporting_period
    assert period.calendar_year == YEAR

    session.add(Entity(name="Unrelated"))
    session.commit()

    assert entity.reporting_period_id == period.id
    assert list(_periods(session)) == [YEAR]


def test_repair_relabels_the_only_period(session, entity, currency, freeze_today):
    """Without a running period to return to, the early period takes its place"""

    freeze_today(YEAR, 3, 15)
    entity.year_start = 7
    session.commit()
    bank = _account(session, entity, currency, Account.AccountType.BANK, "Bank")
    balance = _balance(session, entity, bank)
    assert balance.transaction_no.endswith(str(YEAR))

    findings = find(session)
    assert len(findings.periods) == 1
    assert findings.periods[0].previous is None
    assert findings.balances == []
    assert repair(session, findings) == 1

    assert list(_periods(session)) == [YEAR - 1]
    assert entity.reporting_period.status == ReportingPeriod.Status.OPEN
    assert entity.reporting_period.interval()["start"] == datetime(YEAR - 1, 7, 1)
    assert balance.reporting_period_id == entity.reporting_period_id
    assert balance.transaction_no.endswith(str(YEAR - 1))
    assert bank.closing_balance(session) == 50

    assert find(session).periods == []


def test_repair_restores_a_rolled_over_entity(
    session, entity, currency, old_rollover, freeze_today
):
    """The running period reopens and takes the Balances back from the early one"""

    bank = _account(session, entity, currency, Account.AccountType.BANK, "Bank")
    revenue = _account(
        session, entity, currency, Account.AccountType.OPERATING_REVENUE, "Revenue"
    )
    running, early = old_rollover()
    early_id = early.id
    balance = _balance(session, entity, bank)
    assert balance.reporting_period_id == early_id
    freeze_today(YEAR, 3, 15)

    session.add(Entity(name="Unrelated"))
    session.commit()
    assert entity.reporting_period_id == running.id
    assert bank.closing_balance(session) == 0

    sale = CashSale(
        narration="Sale in March",
        transaction_date=datetime(YEAR, 3, 10),
        account_id=bank.id,
        entity_id=entity.id,
    )
    with pytest.raises(AdjustingReportingPeriodError):
        session.add(sale)
        session.flush()
    session.rollback()

    findings = find(session)
    assert len(findings.periods) == 1
    assert len(findings.balances) == 1
    assert bank.closing_balance(session) == 0  # nothing changes until repaired
    assert repair(session, findings) == 2

    assert list(_periods(session)) == [YEAR - 1]
    assert running.status == ReportingPeriod.Status.OPEN
    assert entity.reporting_period_id == running.id
    assert balance.reporting_period_id == running.id
    assert balance.transaction_no.endswith(str(YEAR - 1))
    assert bank.closing_balance(session) == 50
    assert revenue.closing_balance(session) == 0

    session.add(
        CashSale(
            narration="Sale in March",
            transaction_date=datetime(YEAR, 3, 10),
            account_id=bank.id,
            entity_id=entity.id,
        )
    )
    session.flush()

    assert find(session).periods == []
    assert find(session).balances == []


def test_period_count_is_reused_after_repair(session, entity, currency, old_rollover, freeze_today):
    """The next period can be created after the early one has been removed"""

    running, _ = old_rollover()
    freeze_today(YEAR, 3, 15)
    session.add(Entity(name="Unrelated"))
    session.commit()
    count = running.period_count
    repair(session, find(session))

    freeze_today(YEAR, 8, 15)
    _account(session, entity, currency, Account.AccountType.BANK, "Bank")
    session.commit()

    assert entity.reporting_period.calendar_year == YEAR
    assert entity.reporting_period.period_count == count + 1
    assert entity.reporting_period.status == ReportingPeriod.Status.OPEN
    assert running.status == ReportingPeriod.Status.ADJUSTING


def test_balance_of_a_begun_period_is_found_by_when_it_was_created(
    session, entity, currency, old_rollover, freeze_today
):
    """After the year start the period is right, but the Balance is still a year late"""

    bank = _account(session, entity, currency, Account.AccountType.BANK, "Bank")
    running, early = old_rollover()
    balance = _balance(session, entity, bank)
    correct = _balance(session, entity, bank)
    freeze_today(YEAR, 8, 15)
    _set_created_at(session, balance, datetime(YEAR, 3, 10))
    _set_created_at(session, correct, datetime(YEAR, 8, 10))

    findings = find(session)
    assert findings.periods == []
    assert [f.balance.id for f in findings.balances] == [balance.id]
    assert findings.balances[0].target.id == running.id
    assert bank.closing_balance(session) == 100
    assert repair(session, findings) == 1

    assert balance.reporting_period_id == running.id
    assert correct.reporting_period_id == early.id
    assert bank.closing_balance(session) == 50


def test_closed_period_blocks_repair(
    session, entity, currency, old_rollover, freeze_today
):
    """Nothing is moved into or out of a closed Reporting Period"""

    bank = _account(session, entity, currency, Account.AccountType.BANK, "Bank")
    running, early = old_rollover()
    balance = _balance(session, entity, bank)
    freeze_today(YEAR, 3, 15)
    running.status = ReportingPeriod.Status.CLOSED
    session.commit()

    findings = find(session)
    assert findings.periods[0].blocked == CLOSED_PERIOD
    assert findings.balances[0].blocked == CLOSED_PERIOD
    assert repair(session, findings) == 0

    assert sorted(_periods(session)) == [YEAR - 1, YEAR]
    assert balance.reporting_period_id == early.id


def test_missing_period_blocks_the_move(session, entity, currency, freeze_today):
    """A Balance with no earlier period to move to is listed, and left where it is"""

    freeze_today(YEAR, 8, 15)
    entity.year_start = 7
    session.commit()
    bank = _account(session, entity, currency, Account.AccountType.BANK, "Bank")
    balance = _balance(session, entity, bank)
    _set_created_at(session, balance, datetime(YEAR, 3, 10))

    findings = find(session)
    assert [f.blocked for f in findings.balances] == [MISSING_PERIOD]
    assert repair(session, findings) == 0
    assert balance.reporting_period.calendar_year == YEAR


def test_january_year_is_not_checked(session, entity, currency, freeze_today):
    """A year starting in January cannot have been affected"""

    freeze_today(YEAR, 3, 15)
    bank = _account(session, entity, currency, Account.AccountType.BANK, "Bank")
    _balance(session, entity, bank)

    findings = find(session)
    assert findings.periods == []
    assert findings.balances == []


def test_repair_rolls_back_on_failure(
    session, entity, currency, old_rollover, freeze_today, monkeypatch
):
    """A failure partway through leaves everything as it was"""

    bank = _account(session, entity, currency, Account.AccountType.BANK, "Bank")
    _, early = old_rollover()
    balance = _balance(session, entity, bank)
    freeze_today(YEAR, 3, 15)

    def fail(*_):
        raise RuntimeError

    monkeypatch.setattr(repair_module, "_replace", fail)
    with pytest.raises(RuntimeError):
        repair(session, find(session))

    assert balance.reporting_period_id == early.id
