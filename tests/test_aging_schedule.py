from dateutil.relativedelta import relativedelta
from datetime import datetime
from python_accounting.models import (
    Account,
    Balance,
    Transaction,
    LineItem,
    Tax,
    Assignment,
    ReportingPeriod,
)
from python_accounting.transactions import (
    ClientInvoice,
    ClientReceipt,
    JournalEntry,
    SupplierBill,
    SupplierPayment,
)
from python_accounting.reports import AgingSchedule


def test_receivables_aging_schedule(session, entity, currency):
    """Tests the allocation of receivable account balances into buckets based on the age of their outstanding transactions"""

    client = Account(
        name="test account one",
        account_type=Account.AccountType.RECEIVABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    revenue = Account(
        name="test account two",
        account_type=Account.AccountType.OPERATING_REVENUE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    control = Account(
        name="test account three",
        account_type=Account.AccountType.CONTROL,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    bank_account = Account(
        name="test account four",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    client2 = Account(
        name="test account five",
        account_type=Account.AccountType.RECEIVABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add_all(
        [
            client,
            revenue,
            control,
            bank_account,
            ReportingPeriod(
                calendar_year=datetime.now().year - 1,
                period_count=2,
                entity_id=entity.id,
            ),
            client2,
        ]
    )
    session.commit()

    session.add_all(
        [
            Balance(
                transaction_date=datetime.now()
                - relativedelta(years=2),  # 365+ transaction
                transaction_type=Transaction.TransactionType.CLIENT_INVOICE,
                amount=45,
                balance_type=Balance.BalanceType.DEBIT,
                account_id=client.id,
                entity_id=entity.id,
            ),
            Balance(
                transaction_date=datetime.now()
                - relativedelta(days=365),  # 271 - 365 days transaction
                transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
                amount=70,
                balance_type=Balance.BalanceType.DEBIT,
                account_id=client2.id,
                entity_id=entity.id,
            ),
        ]
    )
    session.flush()

    # current transaction
    transaction = ClientInvoice(
        narration="Test transaction one",
        transaction_date=datetime.now() - relativedelta(days=2),
        account_id=client.id,
        entity_id=entity.id,
    )
    session.add(transaction)
    session.commit()

    tax = Tax(
        name="Output Vat",
        code="OTPT",
        account_id=control.id,
        rate=10,
        entity_id=entity.id,
    )
    session.add(tax)
    session.flush()

    line_item1 = LineItem(
        narration="Test line item one",
        account_id=revenue.id,
        amount=100,
        tax_id=tax.id,
        entity_id=entity.id,
    )
    session.add(line_item1)
    session.flush()

    transaction.line_items.add(line_item1)
    session.add(transaction)
    session.flush()

    transaction.post(session)

    # partially clear current transaction
    transaction2 = ClientReceipt(
        narration="Test transaction two",
        transaction_date=datetime.now(),
        account_id=client.id,
        entity_id=entity.id,
    )
    session.add(transaction2)
    session.commit()

    line_item2 = LineItem(
        narration="Test line item two",
        account_id=bank_account.id,
        amount=25,
        entity_id=entity.id,
    )
    session.add(line_item2)
    session.flush()

    transaction2.line_items.add(line_item2)
    session.add(transaction2)
    session.flush()

    transaction2.post(session)

    assignment1 = Assignment(
        assignment_date=datetime.now(),
        transaction_id=transaction2.id,
        assigned_id=transaction.id,
        assigned_type=transaction.__class__.__name__,
        entity_id=entity.id,
        amount=15,
    )
    session.add(assignment1)
    session.flush()

    # 31 - 90 days transaction
    transaction3 = JournalEntry(
        narration="Test transaction three",
        transaction_date=datetime.now() - relativedelta(months=2),
        account_id=client.id,
        entity_id=entity.id,
        credited=False,
    )
    session.add(transaction3)
    session.flush()

    line_item3 = LineItem(
        narration="Test line item three",
        account_id=revenue.id,
        amount=50,
        entity_id=entity.id,
    )
    session.add(line_item3)
    session.flush()

    transaction3.line_items.add(line_item3)
    session.add(transaction3)
    session.flush()

    transaction3.post(session)

    # 91 - 180 days transaction
    transaction4 = JournalEntry(
        narration="Test transaction four",
        transaction_date=datetime.now() - relativedelta(months=5),
        account_id=client2.id,
        entity_id=entity.id,
        credited=False,
    )
    session.add(transaction4)
    session.flush()

    line_item4 = LineItem(
        narration="Test line item four",
        account_id=revenue.id,
        amount=25,
        entity_id=entity.id,
    )
    session.add(line_item4)
    session.flush()

    transaction4.line_items.add(line_item4)
    session.add(transaction4)
    session.flush()

    transaction4.post(session)

    # 181 - 270 days transaction
    transaction5 = JournalEntry(
        narration="Test transaction five",
        transaction_date=datetime.now() - relativedelta(months=8),
        account_id=client.id,
        entity_id=entity.id,
        credited=False,
    )
    session.add(transaction5)
    session.flush()

    line_item5 = LineItem(
        narration="Test line item five",
        account_id=revenue.id,
        amount=65,
        entity_id=entity.id,
    )
    session.add(line_item5)
    session.flush()

    transaction5.line_items.add(line_item5)
    session.add(transaction5)
    session.flush()

    transaction5.post(session)

    # 181 - 270 days transaction
    transaction6 = JournalEntry(
        narration="Test transaction six",
        transaction_date=datetime.now() - relativedelta(months=10),
        account_id=client.id,
        entity_id=entity.id,
        credited=False,
    )
    session.add(transaction6)
    session.flush()

    line_item6 = LineItem(
        narration="Test line item six",
        account_id=revenue.id,
        amount=85,
        entity_id=entity.id,
    )
    session.add(line_item6)
    session.flush()

    transaction6.line_items.add(line_item6)
    session.add(transaction6)
    session.flush()

    transaction6.post(session)

    schedule = AgingSchedule(session, Account.AccountType.RECEIVABLE)

    assert schedule.balances["current"] == 95
    assert schedule.balances["31 - 90 days"] == 50
    assert schedule.balances["91 - 180 days"] == 25
    assert schedule.balances["181 - 270 days"] == 65
    assert schedule.balances["271 - 365 days"] == 155
    assert schedule.balances["365+ (bad debts)"] == 45

    assert schedule.accounts[0].balances["current"] == 95
    assert schedule.accounts[0].balances["31 - 90 days"] == 50
    assert schedule.accounts[0].balances["91 - 180 days"] == 0
    assert schedule.accounts[0].balances["181 - 270 days"] == 65
    assert schedule.accounts[0].balances["271 - 365 days"] == 85
    assert schedule.accounts[0].balances["365+ (bad debts)"] == 45

    assert schedule.accounts[1].balances["current"] == 0
    assert schedule.accounts[1].balances["31 - 90 days"] == 0
    assert schedule.accounts[1].balances["91 - 180 days"] == 25
    assert schedule.accounts[1].balances["181 - 270 days"] == 0
    assert schedule.accounts[1].balances["271 - 365 days"] == 70
    assert schedule.accounts[1].balances["365+ (bad debts)"] == 0


def test_payables_aging_schedule(session, entity, currency):
    """Tests the allocation of payables account balances into buckets based on the age of their outstanding transactions"""

    supplier = Account(
        name="test account one",
        account_type=Account.AccountType.PAYABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    cogs = Account(
        name="test account two",
        account_type=Account.AccountType.OPERATING_EXPENSE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    control = Account(
        name="test account three",
        account_type=Account.AccountType.CONTROL,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    bank_account = Account(
        name="test account four",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    supplier2 = Account(
        name="test account five",
        account_type=Account.AccountType.PAYABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add_all(
        [
            supplier,
            cogs,
            control,
            bank_account,
            ReportingPeriod(
                calendar_year=datetime.now().year - 1,
                period_count=2,
                entity_id=entity.id,
            ),
            supplier2,
        ]
    )
    session.commit()

    session.add_all(
        [
            Balance(
                transaction_date=datetime.now()
                - relativedelta(years=2),  # 365+ transaction
                transaction_type=Transaction.TransactionType.SUPPLIER_BILL,
                amount=68,
                balance_type=Balance.BalanceType.CREDIT,
                account_id=supplier.id,
                entity_id=entity.id,
            ),
            Balance(
                transaction_date=datetime.now()
                - relativedelta(days=365),  # 271 - 365 days transaction
                transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
                amount=83,
                balance_type=Balance.BalanceType.CREDIT,
                account_id=supplier2.id,
                entity_id=entity.id,
            ),
        ]
    )
    session.flush()

    # current transaction
    transaction = SupplierBill(
        narration="Test transaction one",
        transaction_date=datetime.now() - relativedelta(days=2),
        account_id=supplier.id,
        entity_id=entity.id,
    )
    session.add(transaction)
    session.commit()

    tax = Tax(
        name="Inpu Vat",
        code="INPT",
        account_id=control.id,
        rate=8,
        entity_id=entity.id,
    )
    session.add(tax)
    session.flush()

    line_item1 = LineItem(
        narration="Test line item one",
        account_id=cogs.id,
        amount=100,
        tax_id=tax.id,
        entity_id=entity.id,
    )
    session.add(line_item1)
    session.flush()

    transaction.line_items.add(line_item1)
    session.add(transaction)
    session.flush()

    transaction.post(session)

    # partially clear current transaction
    transaction2 = SupplierPayment(
        narration="Test transaction two",
        transaction_date=datetime.now(),
        account_id=supplier.id,
        entity_id=entity.id,
    )
    session.add(transaction2)
    session.commit()

    line_item2 = LineItem(
        narration="Test line item two",
        account_id=bank_account.id,
        amount=35,
        entity_id=entity.id,
    )
    session.add(line_item2)
    session.flush()

    transaction2.line_items.add(line_item2)
    session.add(transaction2)
    session.flush()

    transaction2.post(session)

    assignment1 = Assignment(
        assignment_date=datetime.now(),
        transaction_id=transaction2.id,
        assigned_id=transaction.id,
        assigned_type=transaction.__class__.__name__,
        entity_id=entity.id,
        amount=35,
    )
    session.add(assignment1)
    session.flush()

    # 31 - 90 days transaction
    transaction3 = JournalEntry(
        narration="Test transaction three",
        transaction_date=datetime.now() - relativedelta(months=2),
        account_id=supplier.id,
        entity_id=entity.id,
    )
    session.add(transaction3)
    session.flush()

    line_item3 = LineItem(
        narration="Test line item three",
        account_id=cogs.id,
        amount=63,
        entity_id=entity.id,
    )
    session.add(line_item3)
    session.flush()

    transaction3.line_items.add(line_item3)
    session.add(transaction3)
    session.flush()

    transaction3.post(session)

    # 91 - 180 days transaction
    transaction4 = JournalEntry(
        narration="Test transaction four",
        transaction_date=datetime.now() - relativedelta(months=5),
        account_id=supplier2.id,
        entity_id=entity.id,
    )
    session.add(transaction4)
    session.flush()

    line_item4 = LineItem(
        narration="Test line item four",
        account_id=cogs.id,
        amount=76,
        entity_id=entity.id,
    )
    session.add(line_item4)
    session.flush()

    transaction4.line_items.add(line_item4)
    session.add(transaction4)
    session.flush()

    transaction4.post(session)

    # 181 - 270 days transaction
    transaction5 = JournalEntry(
        narration="Test transaction five",
        transaction_date=datetime.now() - relativedelta(months=8),
        account_id=supplier.id,
        entity_id=entity.id,
    )
    session.add(transaction5)
    session.flush()

    line_item5 = LineItem(
        narration="Test line item five",
        account_id=cogs.id,
        amount=37,
        entity_id=entity.id,
    )
    session.add(line_item5)
    session.flush()

    transaction5.line_items.add(line_item5)
    session.add(transaction5)
    session.flush()

    transaction5.post(session)

    # 271 - 365 days transaction
    transaction6 = JournalEntry(
        narration="Test transaction six",
        transaction_date=datetime.now() - relativedelta(months=10),
        account_id=supplier.id,
        entity_id=entity.id,
    )
    session.add(transaction6)
    session.flush()

    line_item6 = LineItem(
        narration="Test line item six",
        account_id=cogs.id,
        amount=31,
        entity_id=entity.id,
    )
    session.add(line_item6)
    session.flush()

    transaction6.line_items.add(line_item6)
    session.add(transaction6)
    session.flush()

    transaction6.post(session)

    schedule = AgingSchedule(session, Account.AccountType.PAYABLE)

    assert schedule.balances["current"] == 73
    assert schedule.balances["31 - 90 days"] == 63
    assert schedule.balances["91 - 180 days"] == 76
    assert schedule.balances["181 - 270 days"] == 37
    assert schedule.balances["271 - 365 days"] == 114
    assert schedule.balances["365+ (bad debts)"] == 68

    assert schedule.accounts[0].balances["current"] == 73
    assert schedule.accounts[0].balances["31 - 90 days"] == 63
    assert schedule.accounts[0].balances["91 - 180 days"] == 0
    assert schedule.accounts[0].balances["181 - 270 days"] == 37
    assert schedule.accounts[0].balances["271 - 365 days"] == 31
    assert schedule.accounts[0].balances["365+ (bad debts)"] == 68

    assert schedule.accounts[1].balances["current"] == 0
    assert schedule.accounts[1].balances["31 - 90 days"] == 0
    assert schedule.accounts[1].balances["91 - 180 days"] == 76
    assert schedule.accounts[1].balances["181 - 270 days"] == 0
    assert schedule.accounts[1].balances["271 - 365 days"] == 83
    assert schedule.accounts[1].balances["365+ (bad debts)"] == 0
