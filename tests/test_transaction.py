import pytest
from datetime import datetime
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from sqlalchemy import select, func, update
from python_accounting.models import (
    Account,
    Transaction,
    Entity,
    ReportingPeriod,
    LineItem,
    Tax,
    Ledger,
    Balance,
)
from python_accounting.exceptions import (
    InvalidTransactionDateError,
    ClosedReportingPeriodError,
    AdjustingReportingPeriodError,
    RedundantTransactionError,
    MissingLineItemError,
    InvalidTransactionTypeError,
    PostedTransactionError,
)


def test_transaction_entity(session, entity, currency):
    """Tests the relationship between a transaction and its associated entity"""

    account = Account(
        name="test transaction account",
        account_type=Account.AccountType.CONTROL,
        currency_id=currency.id,
        entity_id=entity.id,
    )

    session.add(account)
    session.flush()

    transaction = Transaction(
        narration="Test transaction",
        transaction_date=datetime.now(),
        account_id=account.id,
        transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
        entity_id=entity.id,
    )
    session.add(transaction)
    session.commit()

    transaction = session.get(Transaction, transaction.id)

    assert transaction.entity.name == "Test Entity"
    assert transaction.account.name == "Test Transaction Account"
    assert transaction.transaction_no == "JN01/0001"
    assert transaction.currency_id == account.currency_id


def test_transaction_validation(session, entity, currency):
    """Tests the validation of transaction objects"""
    today = datetime.today()

    account = Account(
        name="test transaction account",
        account_type=Account.AccountType.CONTROL,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    previous_period = ReportingPeriod(
        calendar_year=today.year - 1,
        period_count=2,
        entity_id=entity.id,
        status=ReportingPeriod.Status.CLOSED,
    )
    session.add_all([previous_period, account])
    session.flush()

    transaction = Transaction(
        narration="Test transaction",
        transaction_date=entity.reporting_period.interval()["start"],
        account_id=account.id,
        transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
        entity_id=entity.id,
    )
    session.add(transaction)

    with pytest.raises(InvalidTransactionDateError) as e:
        session.commit()
    assert (
        str(e.value)
        == """The Transaction date cannot be at the exact start of the Reporting Period. Use a Balance object instead."""
    )

    transaction.transaction_date = today - relativedelta(years=1)
    session.add(transaction)
    last_year = datetime.today().year - 1
    with pytest.raises(ClosedReportingPeriodError) as e:
        session.commit()
    assert (
        str(e.value)
        == f"""Transaction cannot be recorded because Reporting
         Period: {last_year} <Period 2> is Closed."""
    )

    transaction.transaction_type = Transaction.TransactionType.CLIENT_INVOICE
    previous_period.status = ReportingPeriod.Status.ADJUSTING

    session.add_all([previous_period, transaction])

    with pytest.raises(AdjustingReportingPeriodError) as e:
        session.commit()
    assert (
        str(e.value)
        == f"""Only Journal Entry Transactions can be recorded for Reporting
         Period: {last_year} <Period 2> which has the Adjusting Status."""
    )

    previous_period.status = ReportingPeriod.Status.OPEN
    session.commit()

    transaction = session.get(Transaction, transaction.id)
    transaction.transaction_type = Transaction.TransactionType.CASH_SALE

    with pytest.raises(InvalidTransactionTypeError) as e:
        session.commit()
    assert (
        str(e.value)
        == "The Transaction type cannot be changed as this would bypass subclass validations."
    )

    session.expunge(transaction)

    transaction = Transaction(
        narration="Test transaction",
        transaction_date=datetime.now(),
        account_id=account.id,
        transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
        entity_id=entity.id,
    )
    session.add(transaction)
    session.flush()

    inventory = Account(
        name="test line item account",
        account_type=Account.AccountType.INVENTORY,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add(inventory)
    session.flush()

    line_item = LineItem(
        narration="Test line item",
        account_id=inventory.id,
        amount=50,
        entity_id=entity.id,
    )
    session.add(line_item)
    session.flush()

    transaction.line_items.add(line_item)
    session.add(transaction)
    transaction.post(session)

    with pytest.raises(PostedTransactionError) as e:
        session.delete(transaction)
    assert str(e.value) == "A Posted Transaction cannot be deleted."


def test_transaction_isolation(session, entity, currency):
    """Tests the isolation of transaction objects by entity"""

    account = Account(
        name="test transaction account",
        account_type=Account.AccountType.CONTROL,
        currency_id=currency.id,
        entity_id=entity.id,
    )

    session.add(account)

    entity2 = Entity(name="Test Entity Two")
    session.add(entity2)
    session.flush()
    entity2 = session.get(Entity, entity2.id)

    session.add_all(
        [
            Transaction(
                narration="Test transaction one",
                transaction_date=datetime.now(),
                account_id=account.id,
                transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
                entity_id=entity.id,
            ),
            Transaction(
                narration="Test transaction two",
                transaction_date=datetime.now(),
                account_id=account.id,
                transaction_type=Transaction.TransactionType.CLIENT_INVOICE,
                entity_id=entity2.id,
            ),
        ]
    )
    session.commit()

    transactions = session.scalars(select(Transaction)).all()

    assert len(transactions) == 1
    assert transactions[0].narration == "Test transaction one"
    assert transactions[0].transaction_type == Transaction.TransactionType.JOURNAL_ENTRY
    assert transactions[0].entity.name == "Test Entity"

    transaction2 = session.get(Transaction, 2)
    assert transaction2 == None

    session.entity = entity2
    transactions = session.scalars(select(Transaction)).all()

    assert len(transactions) == 1
    assert transactions[0].narration == "Test transaction two"
    assert (
        transactions[0].transaction_type == Transaction.TransactionType.CLIENT_INVOICE
    )
    assert transactions[0].entity.name == "Test Entity Two"

    transaction1 = session.get(Transaction, 1)
    assert transaction1 == None


def test_transaction_recycling(session, entity, currency):
    """Tests the deleting, restoring and destroying functions of the transaction model"""

    account = Account(
        name="test transaction account",
        account_type=Account.AccountType.CONTROL,
        currency_id=currency.id,
        entity_id=entity.id,
    )

    session.add(account)
    session.flush()

    transaction = Transaction(
        narration="Test transaction one",
        transaction_date=datetime.now(),
        account_id=account.id,
        transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
        entity_id=entity.id,
    )
    session.add(transaction)
    session.flush()

    transaction_id = transaction.id

    session.delete(transaction)

    transaction = session.get(Transaction, transaction_id)
    assert transaction is None

    transaction = session.get(Transaction, transaction_id, include_deleted=True)
    assert transaction is not None
    session.restore(transaction)

    transaction = session.get(Transaction, transaction_id)
    assert transaction is not None

    session.destroy(transaction)

    transaction = session.get(Transaction, transaction_id)
    assert transaction is None

    transaction = session.get(Transaction, transaction_id, include_deleted=True)
    assert transaction is not None
    session.restore(transaction)  # destroyed models canot be restored

    transaction = session.get(Transaction, transaction_id)
    assert transaction is None


def test_transaction_numbers(session, entity, currency):
    """Tests the auto genearted transaction numbers"""

    account = Account(
        name="test transaction account",
        account_type=Account.AccountType.CONTROL,
        currency_id=currency.id,
        entity_id=entity.id,
    )

    session.add(account)

    session.add_all(
        [
            Transaction(
                narration="Test transaction one",
                transaction_date=datetime.now(),
                account_id=account.id,
                transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
                entity_id=entity.id,
            ),
            Transaction(
                narration="Test transaction two",
                transaction_date=datetime.now(),
                account_id=account.id,
                transaction_type=Transaction.TransactionType.CLIENT_INVOICE,
                entity_id=entity.id,
            ),
            Transaction(
                narration="Test transaction three",
                transaction_date=datetime.now(),
                account_id=account.id,
                transaction_type=Transaction.TransactionType.CLIENT_INVOICE,
                entity_id=entity.id,
            ),
        ]
    )
    session.commit()

    transactions = session.scalars(select(Transaction)).all()

    assert transactions[0].narration == "Test transaction one"
    assert transactions[0].transaction_type == Transaction.TransactionType.JOURNAL_ENTRY
    assert transactions[0].transaction_no == "JN01/0001"

    assert transactions[1].narration == "Test transaction two"
    assert (
        transactions[1].transaction_type == Transaction.TransactionType.CLIENT_INVOICE
    )
    assert transactions[1].transaction_no == "IN01/0001"

    assert transactions[2].narration == "Test transaction three"
    assert (
        transactions[2].transaction_type == Transaction.TransactionType.CLIENT_INVOICE
    )
    assert transactions[2].transaction_no == "IN01/0002"


def test_transaction_line_items(session, entity, currency):
    """Tests the adding and removal of line items to the transaction"""
    account1 = Account(
        name="test transaction account",
        account_type=Account.AccountType.CONTROL,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account2 = Account(
        name="test line item account",
        account_type=Account.AccountType.CONTROL,
        currency_id=currency.id,
        entity_id=entity.id,
    )

    session.add_all([account1, account2])

    transaction = Transaction(
        narration="Test transaction one",
        transaction_date=datetime.now(),
        account_id=account1.id,
        transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
        entity_id=entity.id,
    )
    session.add(transaction)

    assert list(transaction.line_items) == []

    session.flush()

    assert list(transaction.line_items) == []

    line_item1 = LineItem(
        narration="Test line item one",
        account_id=account2.id,
        amount=10,
        entity_id=entity.id,
    )

    with pytest.raises(ValueError) as e:
        transaction.line_items.add(line_item1)
    assert str(e.value) == "Line Item must be persisted to be added to the Transaction."

    session.add(line_item1)
    session.flush()

    transaction.line_items.add(line_item1)
    transaction.line_items.add(line_item1)

    assert list(transaction.line_items) == [line_item1]

    line_item2 = LineItem(
        narration="Test line item two",
        account_id=account2.id,
        amount=20,
        entity_id=entity.id,
    )

    session.add(line_item2)
    session.flush()
    transaction.line_items.add(line_item2)
    transaction.line_items.remove(line_item1)

    assert list(transaction.line_items) == [line_item2]

    transaction.line_items.remove(line_item2)
    assert list(transaction.line_items) == []

    line_item1.account_id = account1.id
    transaction.line_items.add(line_item1)

    with pytest.raises(RedundantTransactionError) as e:
        session.commit()
    assert (
        str(e.value)
        == """Line Item <Test Transaction Account
         <Debit>: 10> Account is the same as the Transaction Account."""
    )

    line_item1.account_id = account2.id
    transaction.line_items.add(line_item1)
    session.add(transaction)
    session.flush()

    transaction.post(session)

    with pytest.raises(PostedTransactionError) as e:
        transaction.line_items.add(line_item2)
    assert str(e.value) == "Cannot Add Line Items from a Posted Transaction."

    with pytest.raises(PostedTransactionError) as e:
        transaction.line_items.remove(line_item1)
    assert str(e.value) == "Cannot Remove Line Items from a Posted Transaction."

    with pytest.raises(ValueError) as e:
        transaction.ledgers.remove(transaction.ledgers[0])
    assert str(e.value) == "Transaction ledgers cannot be Removed manually."

    with pytest.raises(ValueError) as e:
        transaction.ledgers.append(transaction.ledgers[0])
    assert str(e.value) == "Transaction ledgers cannot be Added manually."


def test_transaction_amount(session, entity, currency):
    """Tests a transactions tax property"""

    account1 = Account(
        name="test transaction account",
        account_type=Account.AccountType.OPERATING_REVENUE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account2 = Account(
        name="test line item account",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account3 = Account(
        name="test taxation account",
        account_type=Account.AccountType.CONTROL,
        currency_id=currency.id,
        entity_id=entity.id,
    )

    session.add_all([account1, account2, account3])
    session.flush()

    tax1 = Tax(
        name="Output Vat one",
        code="OTPT1",
        account_id=account3.id,
        rate=10,
        entity_id=entity.id,
    )
    session.add(tax1)
    session.flush()

    transaction = Transaction(
        narration="Test transaction one",
        transaction_date=datetime.now(),
        account_id=account1.id,
        transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
        entity_id=entity.id,
    )
    session.add(transaction)

    line_item1 = LineItem(
        narration="Test line item one",
        account_id=account2.id,
        amount=100,
        tax_id=tax1.id,
        entity_id=entity.id,
    )
    line_item2 = LineItem(
        narration="Test line item two",
        account_id=account2.id,
        amount=100,
        quantity=2,
        entity_id=entity.id,
    )

    session.add_all([line_item1, line_item2])
    session.flush()

    transaction.line_items.add(line_item1)
    transaction.line_items.add(line_item2)

    session.add(transaction)
    session.commit()

    assert transaction.amount == Decimal(310)


def test_transaction_tax(session, entity, currency):
    """Tests a transactions tax property"""

    account1 = Account(
        name="test transaction account",
        account_type=Account.AccountType.OPERATING_REVENUE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account2 = Account(
        name="test line item account",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account3 = Account(
        name="test taxation account",
        account_type=Account.AccountType.CONTROL,
        currency_id=currency.id,
        entity_id=entity.id,
    )

    session.add_all([account1, account2, account3])
    session.flush()

    tax1 = Tax(
        name="Output Vat one",
        code="OTPT1",
        account_id=account3.id,
        rate=10,
        entity_id=entity.id,
    )
    tax2 = Tax(
        name="Output Vat two",
        code="OTPT2",
        account_id=account3.id,
        rate=15,
        entity_id=entity.id,
    )
    session.add_all([tax1, tax2])
    session.flush()

    transaction = Transaction(
        narration="Test transaction one",
        transaction_date=datetime.now(),
        account_id=account1.id,
        transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
        entity_id=entity.id,
    )
    session.add(transaction)

    line_item1 = LineItem(
        narration="Test line item one",
        account_id=account2.id,
        amount=100,
        tax_id=tax1.id,
        entity_id=entity.id,
    )
    line_item2 = LineItem(
        narration="Test line item two",
        account_id=account2.id,
        amount=200,
        tax_id=tax2.id,
        entity_id=entity.id,
    )

    session.add_all([line_item1, line_item2])
    session.flush()

    transaction.line_items.add(line_item1)
    transaction.line_items.add(line_item2)

    session.add(transaction)
    session.commit()

    assert transaction.tax["total"] == Decimal(40)
    assert transaction.tax["taxes"] == {
        "OTPT1": dict(
            name="Output Vat one",
            rate="10.00%",
            amount=Decimal(10),
        ),
        "OTPT2": dict(
            name="Output Vat two",
            rate="15.00%",
            amount=Decimal(30),
        ),
    }


def test_transaction_posting(session, entity, currency):
    """Tests validation for changes allowed before and after posting a transaction"""
    account1 = Account(
        name="test transaction account",
        account_type=Account.AccountType.OPERATING_EXPENSE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account2 = Account(
        name="test line item one account",
        account_type=Account.AccountType.PAYABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )

    account3 = Account(
        name="test taxation account",
        account_type=Account.AccountType.CONTROL,
        currency_id=currency.id,
        entity_id=entity.id,
    )

    session.add_all([account1, account2, account3])
    session.flush()

    tax1 = Tax(
        name="Output Vat one",
        code="OTPT1",
        account_id=account3.id,
        rate=10,
        entity_id=entity.id,
    )
    session.add(tax1)
    session.flush()

    transaction = Transaction(
        narration="Test transaction",
        transaction_date=datetime.now(),
        account_id=account1.id,
        transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
        entity_id=entity.id,
    )
    session.add(transaction)
    session.flush()

    assert transaction.amount == Decimal(0)

    with pytest.raises(MissingLineItemError) as e:
        transaction.post(session)
    assert (
        str(e.value) == "A Transaction must have at least one Line Item to be posted."
    )

    line_item1 = LineItem(
        narration="Test line item one",
        account_id=account2.id,
        amount=75,
        tax_id=tax1.id,
        entity_id=entity.id,
    )

    session.add(line_item1)
    session.flush()

    transaction.line_items.add(line_item1)
    assert transaction.amount == Decimal(82.5)

    transaction.post(session)

    assert transaction.amount == Decimal(82.5)
    assert (
        session.query(func.sum(Ledger.amount).label("amount"))
        .filter(Ledger.entity_id == transaction.entity_id)
        .filter(Ledger.transaction_id == transaction.id)
        .filter(Ledger.currency_id == transaction.currency_id)
        .filter(
            Ledger.entry_type == Balance.BalanceType.CREDIT
            if transaction.credited
            else Balance.BalanceType.DEBIT
        )
        .scalar()
        == 82.5
    )
    transaction.narration = "new narration"
    session.add(transaction)

    with pytest.raises(PostedTransactionError) as e:
        session.commit()
    assert str(e.value) == "A Posted Transaction cannot be modified."


def test_transaction_account_contribution(session, entity, currency):
    """Tests the contribution of each line item account to the transaction total"""

    account1 = Account(
        name="test transaction account",
        account_type=Account.AccountType.OPERATING_EXPENSE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account2 = Account(
        name="test line item one account",
        account_type=Account.AccountType.PAYABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account3 = Account(
        name="test line item two account",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )

    session.add_all([account1, account2, account3])

    transaction = Transaction(
        narration="Test transaction",
        transaction_date=datetime.now(),
        account_id=account1.id,
        transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
        entity_id=entity.id,
    )
    session.add(transaction)
    session.flush()

    line_item1 = LineItem(
        narration="Test line item one",
        account_id=account2.id,
        amount=75,
        entity_id=entity.id,
    )

    line_item2 = LineItem(
        narration="Test line item two",
        account_id=account3.id,
        amount=120,
        entity_id=entity.id,
    )
    session.add_all([line_item1, line_item2])
    session.flush()

    transaction.line_items.add(line_item1)
    transaction.line_items.add(line_item2)
    session.add(transaction)
    session.flush()

    transaction.post(session)

    assert transaction.amount == Decimal(195)
    assert transaction.contribution(session, account1) == Decimal(-195)
    assert transaction.contribution(session, account2) == Decimal(75)
    assert transaction.contribution(session, account3) == Decimal(120)


def test_transaction_security(session, entity, currency):
    """Tests the security of Transactions against manipulation"""

    account1 = Account(
        name="test transaction account",
        account_type=Account.AccountType.OPERATING_EXPENSE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account2 = Account(
        name="test line item one account",
        account_type=Account.AccountType.PAYABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )

    session.add_all([account1, account2])

    transaction = Transaction(
        narration="Test transaction",
        transaction_date=datetime.now(),
        account_id=account1.id,
        transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
        entity_id=entity.id,
    )
    session.add(transaction)
    session.flush()

    line_item1 = LineItem(
        narration="Test line item one",
        account_id=account2.id,
        amount=75.36,
        entity_id=entity.id,
    )

    session.add_all([line_item1])
    session.flush()

    transaction.line_items.add(line_item1)
    session.add(transaction)
    session.flush()

    transaction.post(session)

    transaction.is_secure(session)
    # assert transaction.amount == Decimal("75.36")
    # assert transaction.is_secure(session) is True

    # connection = session.connection()
    # connection.execute(
    #     update(Ledger).where(Ledger.id == transaction.ledgers[0].id).values(amount=10)
    # )

    # session.refresh(transaction)
    # assert transaction.is_secure(session) is not True
