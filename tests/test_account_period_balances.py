from datetime import datetime

import pytest
from dateutil.relativedelta import relativedelta
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from python_accounting.exceptions import MissingReportingPeriodError
from python_accounting.models import Account, Balance, Ledger, ReportingPeriod, Transaction
from python_accounting.reports import IncomeStatement
from python_accounting.transactions import CashSale


@pytest.fixture
def accounts(session, entity, currency):
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
    return bank, revenue


def test_section_balances_do_not_count_the_start_date_twice(
    session, entity, accounts, post_document
):
    """A Transaction on the start date is in the movement, not the opening balance"""

    bank, revenue = accounts
    period_start = entity.reporting_period.interval()["start"]
    post_document(CashSale, bank, revenue, period_start + relativedelta(hours=9), 100)

    balances = Account.section_balances(
        session, [Account.AccountType.BANK], None, period_start + relativedelta(days=1)
    )
    assert balances["opening"] == 0
    assert balances["closing"] == 100

    later = period_start + relativedelta(days=2, hours=9)
    post_document(CashSale, bank, revenue, later, 30)
    balances = Account.section_balances(
        session,
        [Account.AccountType.BANK],
        later,
        period_start + relativedelta(days=3),
    )
    assert balances["opening"] == 100
    assert balances["closing"] == 130


def test_statement_opening_balance_includes_movement_before_the_start_date(
    session, entity, accounts, post_document
):
    """The statement agrees with the closing balance of the Account"""

    bank, revenue = accounts
    period_start = entity.reporting_period.interval()["start"]
    post_document(CashSale, bank, revenue, period_start + relativedelta(days=9), 100)
    post_document(CashSale, bank, revenue, period_start + relativedelta(days=20), 30)
    end_date = period_start + relativedelta(days=25)

    statement = bank.statement(session, period_start + relativedelta(days=15), end_date)

    assert statement["opening_balance"] == 100
    assert statement["closing_balance"] == 130
    assert statement["closing_balance"] == bank.closing_balance(session, end_date)


def test_statement_without_transactions_closes_at_its_opening_balance(
    session, entity, accounts
):
    """The closing balance of an inactive Account is its opening balance"""

    bank, _ = accounts
    session.add(
        Balance(
            transaction_date=entity.reporting_period.interval()["start"]
            - relativedelta(days=1),
            transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
            amount=50,
            balance_type=Balance.BalanceType.DEBIT,
            account_id=bank.id,
            entity_id=entity.id,
        )
    )
    session.flush()

    statement = bank.statement(session)

    assert statement["opening_balance"] == 50
    assert statement["transactions"] == []
    assert statement["closing_balance"] == 50


def test_report_can_start_before_the_first_period(
    session, entity, accounts, post_document, freeze_today
):
    """Only the end date has to be within a Reporting Period"""

    year = datetime.now().year
    freeze_today(year, 8, 15)
    entity.year_start = 7
    session.commit()
    bank, revenue = accounts
    post_document(CashSale, bank, revenue, datetime(year, 7, 15, 9), 100)

    income_statement = IncomeStatement(
        session, datetime(year, 6, 1), datetime(year, 8, 1)
    )
    assert income_statement.result_amounts["NET_PROFIT"] == 100

    with pytest.raises(MissingReportingPeriodError):
        bank.closing_balance(session, datetime(year, 6, 30))


def test_date_year_without_an_entity_is_the_year_of_the_date():
    """The date is not ignored when there is no Entity"""

    assert ReportingPeriod.date_year(datetime(2020, 5, 1)) == 2020
    assert ReportingPeriod.date_year() == datetime.today().year


def test_mysql_dates_keep_microseconds():
    """Ledger hashes are verified against the dates as they were stored"""

    ddl = str(CreateTable(Ledger.__table__).compile(dialect=mysql.dialect()))

    assert "transaction_date DATETIME(6)" in ddl
