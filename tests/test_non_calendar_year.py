from datetime import datetime
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from python_accounting.models import Account, Balance, LineItem, Transaction
from python_accounting.reports import BalanceSheet, IncomeStatement, TrialBalance
from python_accounting.transactions import CashSale


def test_reports_in_second_half_of_a_non_calendar_year(session, entity, currency):
    """Reports dated before the year start month use the period that contains them"""

    entity.year_start = 7
    session.commit()
    period_start = entity.reporting_period.interval()["start"]
    # March of the same reporting period, in the calendar year after it starts.
    transaction_date = period_start + relativedelta(months=8, days=14)
    end_date = period_start + relativedelta(months=9) - relativedelta(days=1)
    assert end_date.year == period_start.year + 1

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
    equity = Account(
        name="Equity",
        account_type=Account.AccountType.EQUITY,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add_all([bank, revenue, equity])
    session.flush()

    session.add_all(
        [
            Balance(
                transaction_date=period_start - relativedelta(days=1),
                transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
                amount=50,
                balance_type=Balance.BalanceType.DEBIT,
                account_id=bank.id,
                entity_id=entity.id,
            ),
            Balance(
                transaction_date=period_start - relativedelta(days=1),
                transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
                amount=50,
                balance_type=Balance.BalanceType.CREDIT,
                account_id=equity.id,
                entity_id=entity.id,
            ),
        ]
    )
    session.flush()

    cash_sale = CashSale(
        narration="Sale in March",
        transaction_date=transaction_date,
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

    assert bank.opening_balance(session, period_start.year) == 50
    assert bank.balance_movement(session, None, end_date) == 100
    assert bank.closing_balance(session, end_date) == 150

    statement = bank.statement(session, None, end_date)
    assert statement["opening_balance"] == 50
    assert statement["closing_balance"] == 150

    income_statement = IncomeStatement(session, None, end_date)
    assert income_statement.result_amounts["NET_PROFIT"] == 100

    balance_sheet = BalanceSheet(session, end_date)
    assert balance_sheet.totals["ASSETS"] == 150

    trial_balance = TrialBalance(session, end_date)
    assert trial_balance.totals["INCOME_STATEMENT"] == -100
    assert trial_balance.totals["BALANCE_SHEET"] == 100
