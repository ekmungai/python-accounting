import pytest
from datetime import datetime
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from python_accounting.models import (
    Account,
    Category,
    Entity,
    Balance,
    Transaction,
    ReportingPeriod,
    LineItem,
    Tax,
    Assignment,
)
from python_accounting.transactions import (
    ClientInvoice,
    CashSale,
    ContraEntry,
    ClientReceipt,
    CashPurchase,
    SupplierPayment,
    CreditNote,
    JournalEntry,
    SupplierBill,
    DebitNote,
)
from python_accounting.exceptions import (
    InvalidCategoryAccountTypeError,
    InvalidAccountTypeError,
    HangingTransactionsError,
)


def test_account_entity(session, entity, currency):
    """Tests the relationship between an account and its associated entity"""

    account = Account(
        name="test account",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add(account)
    session.commit()

    account = session.get(Account, account.id)
    assert account.entity.name == "Test Entity"
    assert account.name == "Test Account"


def test_account_validation(session, entity, currency):
    """Tests the validation of account objects"""

    account = Account(
        name="test account",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add(account)
    session.flush()

    with pytest.raises(InvalidAccountTypeError) as e:
        account.statement(session, None, None, True)

    assert (
        str(e.value)
        == "Only Receivable and Payable Accounts can have a statement/schedule."
    )

    account = session.get(Account, account.id)
    assert account.account_code == 3001

    account.name = "new test account"
    session.add(account)
    session.flush()

    account = session.get(Account, account.id)
    assert account.account_code == 3001
    assert (
        account.name == "New Test Account"
    )  # changes other than account type do not affect the account code

    account.account_type = Account.AccountType.RECEIVABLE
    session.add(account)
    session.flush()

    account = session.get(Account, account.id)
    assert account.account_code == 50001

    account = Account(
        name="test account three",
        account_type=Account.AccountType.RECEIVABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add(account)
    session.flush()

    account = session.get(Account, account.id)
    account.name == "Test Account Three"
    assert account.account_code == 50002

    category = Category(
        name="Test Category",
        category_account_type=Account.AccountType.BANK,
        entity_id=entity.id,
    )
    session.add(category)
    session.flush()

    account.category_id = category.id
    session.add(account)

    with pytest.raises(InvalidCategoryAccountTypeError) as e:
        session.commit()

    assert str(e.value) == "Cannot assign Receivable Account to Bank Category."

    session.expunge(account)
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

    with pytest.raises(HangingTransactionsError) as e:
        session.delete(account)
    assert (
        str(e.value)
        == """The Account cannot be deleted because it has Transactions in
         the current reporting period."""
    )


def test_account_isolation(session, entity, currency):
    """Tests the isolation of account objects by entity"""

    year = datetime.today().year
    entity2 = Entity(name="Test Entity Two")
    session.add(entity2)
    session.flush()
    entity2 = session.get(Entity, entity2.id)

    session.add_all(
        [
            Account(
                name="test account one",
                account_type=Account.AccountType.BANK,
                currency_id=currency.id,
                entity_id=entity.id,
            ),
            Account(
                name="test account two",
                account_type=Account.AccountType.RECEIVABLE,
                currency_id=currency.id,
                entity_id=entity2.id,
            ),
        ]
    )
    session.commit()

    accounts = session.scalars(select(Account)).all()

    assert len(accounts) == 1
    assert accounts[0].name == "Test Account One"
    assert accounts[0].account_type == Account.AccountType.BANK
    assert accounts[0].entity.name == "Test Entity"

    account2 = session.get(Account, 3)
    assert account2 == None

    session.entity = entity2
    accounts = session.scalars(select(Account)).all()

    assert len(accounts) == 1
    assert accounts[0].name == "Test Account Two"
    assert accounts[0].account_type == Account.AccountType.RECEIVABLE
    assert accounts[0].entity.name == "Test Entity Two"

    account1 = session.get(Account, 1)
    assert account1 == None


def test_account_recycling(session, entity, currency):
    """Tests the deleting, restoring and destroying functions of the account model"""

    account = Account(
        name="test account one",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add(account)
    session.flush()

    account_id = account.id

    session.delete(account)

    account = session.get(Account, account_id)
    assert account == None

    account = session.get(Account, account_id, include_deleted=True)
    assert account != None
    session.restore(account)

    account = session.get(Account, account_id)
    assert account != None

    session.destroy(account)

    account = session.get(Account, account_id)
    assert account == None

    account = session.get(Account, account_id, include_deleted=True)
    assert account != None
    session.restore(account)  # destroyed models canot be restored

    account = session.get(Account, account_id)
    assert account == None


def test_account_opening_balance(session, entity, currency):
    """Tests an account's opening balance"""

    account1 = Account(
        name="test account one",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account2 = Account(
        name="test account two",
        account_type=Account.AccountType.PAYABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add_all([account1, account2])
    session.flush()

    date = datetime.now() - relativedelta(days=365)
    session.add_all(
        [
            Balance(
                transaction_date=date,
                transaction_type=Transaction.TransactionType.CLIENT_INVOICE,
                amount=100,
                balance_type=Balance.BalanceType.DEBIT,
                account_id=account1.id,
                entity_id=entity.id,
            ),
            Balance(
                transaction_date=date,
                transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
                amount=25,
                balance_type=Balance.BalanceType.CREDIT,
                account_id=account1.id,
                entity_id=entity.id,
            ),
            Balance(
                transaction_date=date,
                transaction_type=Transaction.TransactionType.SUPPLIER_BILL,
                amount=50,
                balance_type=Balance.BalanceType.CREDIT,
                account_id=account2.id,
                entity_id=entity.id,
            ),
            Balance(
                transaction_date=date,
                transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
                amount=15,
                balance_type=Balance.BalanceType.DEBIT,
                account_id=account1.id,
                entity_id=entity.id,
            ),
        ]
    )
    assert account1.opening_balance(session) == 90
    assert account2.opening_balance(session) == -50

    date -= relativedelta(days=365)
    new_reporting_period = ReportingPeriod(
        calendar_year=date.year,
        period_count=2,
        entity_id=entity.id,
    )
    session.add(new_reporting_period)
    session.commit()
    assert account1.opening_balance(session, date.year) == 0
    assert account2.opening_balance(session, date.year) == 0


def test_account_closing_balance(session, entity, currency):
    """Tests an account's closing balance method"""
    account1 = Account(
        name="test account one",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account2 = Account(
        name="test account two",
        account_type=Account.AccountType.PAYABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add_all([account1, account2])
    session.flush()

    date = datetime.now() - relativedelta(days=365)
    session.add_all(
        [
            Balance(
                transaction_date=date,
                transaction_type=Transaction.TransactionType.CLIENT_INVOICE,
                amount=100,
                balance_type=Balance.BalanceType.DEBIT,
                account_id=account1.id,
                entity_id=entity.id,
            ),
            Balance(
                transaction_date=date,
                transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
                amount=25,
                balance_type=Balance.BalanceType.CREDIT,
                account_id=account1.id,
                entity_id=entity.id,
            ),
            Balance(
                transaction_date=date,
                transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
                amount=15,
                balance_type=Balance.BalanceType.DEBIT,
                account_id=account1.id,
                entity_id=entity.id,
            ),
        ]
    )
    transaction = Transaction(
        narration="Test transaction one",
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
        amount=25,
        entity_id=entity.id,
    )
    session.add(line_item1)
    session.flush()

    transaction.line_items.add(line_item1)
    session.add(transaction)
    session.flush()

    assert account1.closing_balance(session) == 90
    assert transaction.is_posted == False

    transaction.post(session)

    assert account1.closing_balance(session) == 65
    assert transaction.is_posted == True
    assert (
        account1.closing_balance(session, datetime.now() - relativedelta(days=1)) == 90
    )


def test_account_section_balances(session, entity, currency):
    """Tests accounts' balances aggregation by section"""

    category1 = Category(
        name="Test Category One",
        category_account_type=Account.AccountType.RECEIVABLE,
        entity_id=entity.id,
    )
    category2 = Category(
        name="Test Category Two",
        category_account_type=Account.AccountType.RECEIVABLE,
        entity_id=entity.id,
    )
    category3 = Category(
        name="Test Category Three",
        category_account_type=Account.AccountType.OPERATING_REVENUE,
        entity_id=entity.id,
    )
    category4 = Category(
        name="Test Category Four",
        category_account_type=Account.AccountType.CONTROL,
        entity_id=entity.id,
    )
    session.add_all([category1, category2, category3, category4])
    session.flush()

    account1 = Account(
        name="test account one",
        account_type=Account.AccountType.RECEIVABLE,
        currency_id=currency.id,
        category_id=category1.id,
        entity_id=entity.id,
    )
    account2 = Account(
        name="test account two",
        account_type=Account.AccountType.RECEIVABLE,
        currency_id=currency.id,
        category_id=category2.id,
        entity_id=entity.id,
    )
    account3 = Account(
        name="test account three",
        account_type=Account.AccountType.OPERATING_REVENUE,
        currency_id=currency.id,
        category_id=category3.id,
        entity_id=entity.id,
    )
    account4 = Account(
        name="test account four",
        account_type=Account.AccountType.CONTROL,
        currency_id=currency.id,
        category_id=category4.id,
        entity_id=entity.id,
    )
    session.add_all([account1, account2, account3, account4])
    session.flush()

    date = datetime.now() - relativedelta(days=365)
    session.add_all(
        [
            Balance(
                transaction_date=date,
                transaction_type=Transaction.TransactionType.CLIENT_INVOICE,
                amount=150,
                balance_type=Balance.BalanceType.DEBIT,
                account_id=account1.id,
                entity_id=entity.id,
            ),
            Balance(
                transaction_date=date,
                transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
                amount=80,
                balance_type=Balance.BalanceType.CREDIT,
                account_id=account1.id,
                entity_id=entity.id,
            ),
        ]
    )
    transaction = ClientInvoice(
        narration="Test transaction one",
        transaction_date=datetime.now(),
        account_id=account2.id,
        entity_id=entity.id,
    )
    session.add(transaction)
    session.commit()

    tax = Tax(
        name="Output Vat",
        code="OTPT",
        account_id=account4.id,
        rate=10,
        entity_id=entity.id,
    )
    session.add(tax)
    session.flush()

    line_item1 = LineItem(
        narration="Test line item one",
        account_id=account3.id,
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

    receivables_balances = Account.section_balances(
        session, [Account.AccountType.RECEIVABLE]
    )
    assert receivables_balances["opening"] == 70
    assert receivables_balances["movement"] == -110
    assert receivables_balances["closing"] == 180
    assert len(receivables_balances["categories"]) == 2
    assert receivables_balances["categories"][category1.name]["total"] == 70
    assert receivables_balances["categories"][category1.name]["accounts"] == [account1]

    revenues_balances = Account.section_balances(
        session, [Account.AccountType.OPERATING_REVENUE]
    )
    assert revenues_balances["opening"] == 0
    assert revenues_balances["movement"] == 100
    assert revenues_balances["closing"] == -100
    assert len(revenues_balances["categories"]) == 1
    assert revenues_balances["categories"][category3.name]["total"] == -100
    assert revenues_balances["categories"][category3.name]["accounts"] == [account3]

    control_balances = Account.section_balances(session, [Account.AccountType.CONTROL])
    assert control_balances["opening"] == 0
    assert control_balances["movement"] == 10
    assert control_balances["closing"] == -10
    assert len(control_balances["categories"]) == 1
    assert control_balances["categories"][category4.name]["total"] == -10
    assert control_balances["categories"][category4.name]["accounts"] == [account4]


def test_bank_account_statement(session, entity, currency):
    """Tests a bank account's statement"""

    bank_account = Account(
        name="test account one",
        account_type=Account.AccountType.BANK,
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
    bank_account2 = Account(
        name="test account four",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    client = Account(
        name="test account five",
        account_type=Account.AccountType.RECEIVABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    expense = Account(
        name="test account six",
        account_type=Account.AccountType.DIRECT_EXPENSE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    supplier = Account(
        name="test account seven",
        account_type=Account.AccountType.PAYABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add_all(
        [bank_account, revenue, control, bank_account2, client, expense, supplier]
    )
    session.commit()

    # opening balances
    date = datetime.now() - relativedelta(days=365)
    session.add_all(
        [
            Balance(
                transaction_date=date,
                transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
                amount=150,
                balance_type=Balance.BalanceType.DEBIT,
                account_id=bank_account.id,
                entity_id=entity.id,
            ),
            Balance(
                transaction_date=date,
                transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
                amount=80,
                balance_type=Balance.BalanceType.CREDIT,
                account_id=bank_account.id,
                entity_id=entity.id,
            ),
        ]
    )
    session.flush()

    # cash sale
    transaction1 = CashSale(
        narration="Test transaction one",
        transaction_date=datetime.now(),
        account_id=bank_account.id,
        entity_id=entity.id,
    )
    session.add(transaction1)
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

    transaction1.line_items.add(line_item1)
    session.add(transaction1)
    session.flush()

    transaction1.post(session)

    # credit contra entry
    transaction2 = ContraEntry(
        narration="Test transaction two",
        transaction_date=datetime.now(),
        account_id=bank_account2.id,
        entity_id=entity.id,
    )
    session.add(transaction2)
    session.commit()

    line_item2 = LineItem(
        narration="Test line item two",
        account_id=bank_account.id,
        amount=50,
        entity_id=entity.id,
    )
    session.add(line_item2)
    session.flush()

    transaction2.line_items.add(line_item2)
    session.add(transaction2)
    session.flush()

    transaction2.post(session)

    # debit contra entry
    transaction3 = ContraEntry(
        narration="Test transaction three",
        transaction_date=datetime.now(),
        account_id=bank_account.id,
        entity_id=entity.id,
    )
    session.add(transaction3)
    session.commit()

    line_item3 = LineItem(
        narration="Test line item three",
        account_id=bank_account2.id,
        amount=50,
        entity_id=entity.id,
    )
    session.add(line_item3)
    session.flush()

    transaction3.line_items.add(line_item3)
    session.add(transaction3)
    session.flush()

    transaction3.post(session)

    # client receipt
    transaction4 = ClientReceipt(
        narration="Test transaction four",
        transaction_date=datetime.now(),
        account_id=client.id,
        entity_id=entity.id,
    )
    session.add(transaction4)
    session.commit()

    line_item4 = LineItem(
        narration="Test line item four",
        account_id=bank_account.id,
        amount=25,
        entity_id=entity.id,
    )
    session.add(line_item4)
    session.flush()

    transaction4.line_items.add(line_item4)
    session.add(transaction4)
    session.flush()

    transaction4.post(session)

    # cash purchase
    transaction5 = CashPurchase(
        narration="Test transaction five",
        transaction_date=datetime.now(),
        account_id=bank_account.id,
        entity_id=entity.id,
    )
    session.add(transaction5)
    session.commit()

    tax2 = Tax(
        name="Input Vat",
        code="INPT",
        account_id=control.id,
        rate=5,
        entity_id=entity.id,
    )
    session.add(tax2)
    session.flush()

    line_item5 = LineItem(
        narration="Test line item five",
        account_id=expense.id,
        amount=60,
        tax_id=tax2.id,
        entity_id=entity.id,
    )
    session.add(line_item5)
    session.flush()

    transaction5.line_items.add(line_item5)
    session.add(transaction5)
    session.flush()

    transaction5.post(session)

    # supplier payment
    transaction6 = SupplierPayment(
        narration="Test transaction six",
        transaction_date=datetime.now(),
        account_id=supplier.id,
        entity_id=entity.id,
    )
    session.add(transaction6)
    session.commit()

    line_item6 = LineItem(
        narration="Test line item six",
        account_id=bank_account.id,
        amount=22,
        entity_id=entity.id,
    )
    session.add(line_item6)
    session.flush()

    transaction6.line_items.add(line_item6)
    session.add(transaction6)
    session.flush()

    transaction6.post(session)

    statement = bank_account.statement(session)

    assert statement["opening_balance"] == 70

    assert statement["transactions"][0].debit == 110
    assert statement["transactions"][0].credit == 0
    assert statement["transactions"][0].balance == 180

    assert statement["transactions"][1].debit == 0
    assert statement["transactions"][1].credit == 50
    assert statement["transactions"][1].balance == 130

    assert statement["transactions"][2].debit == 50
    assert statement["transactions"][2].credit == 0
    assert statement["transactions"][2].balance == 180

    assert statement["transactions"][3].debit == 25
    assert statement["transactions"][3].credit == 0
    assert statement["transactions"][3].balance == 205

    assert statement["transactions"][4].debit == 0
    assert statement["transactions"][4].credit == 63
    assert statement["transactions"][4].balance == 142

    assert statement["transactions"][5].debit == 0
    assert statement["transactions"][5].credit == 22
    assert statement["transactions"][5].balance == 120

    assert statement["closing_balance"] == 120

    statement = bank_account.statement(
        session,
        datetime.now() - relativedelta(days=2),
        datetime.now() - relativedelta(days=1),
    )

    assert statement["opening_balance"] == 70
    assert statement["transactions"] == []
    assert statement["closing_balance"] == 0


def test_receivable_account_statement(session, entity, currency):
    """Tests a receivable account's statement"""

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
    bank_account2 = Account(
        name="test account four",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add_all([client, revenue, control, bank_account2])
    session.commit()

    # opening balances
    date = datetime.now() - relativedelta(days=365)
    session.add_all(
        [
            Balance(
                transaction_date=date,
                transaction_type=Transaction.TransactionType.CLIENT_INVOICE,
                amount=45,
                balance_type=Balance.BalanceType.DEBIT,
                account_id=client.id,
                entity_id=entity.id,
            ),
            Balance(
                transaction_date=date,
                transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
                amount=70,
                balance_type=Balance.BalanceType.CREDIT,
                account_id=client.id,
                entity_id=entity.id,
            ),
        ]
    )
    session.flush()

    # client invoice
    transaction = ClientInvoice(
        narration="Test transaction one",
        transaction_date=datetime.now(),
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

    # client receipt
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
        account_id=bank_account2.id,
        amount=25,
        entity_id=entity.id,
    )
    session.add(line_item2)
    session.flush()

    transaction2.line_items.add(line_item2)
    session.add(transaction2)
    session.flush()

    transaction2.post(session)

    transaction3 = CreditNote(
        narration="Test transaction three",
        transaction_date=datetime.now(),
        account_id=client.id,
        entity_id=entity.id,
    )
    session.add(transaction3)
    session.commit()

    tax = Tax(
        name="Output Vat",
        code="OTPT",
        account_id=control.id,
        rate=7,
        entity_id=entity.id,
    )
    session.add(tax)
    session.flush()

    line_item3 = LineItem(
        narration="Test line item three",
        account_id=revenue.id,
        amount=100,
        tax_id=tax.id,
        entity_id=entity.id,
    )
    session.add(line_item3)
    session.flush()

    transaction3.line_items.add(line_item3)
    session.add(transaction3)
    session.flush()

    transaction3.post(session)

    # credit journal entry
    transaction4 = JournalEntry(
        narration="Test transaction four",
        transaction_date=datetime.now(),
        account_id=client.id,
        entity_id=entity.id,
    )
    session.add(transaction4)
    session.commit()

    line_item4 = LineItem(
        narration="Test line item four",
        account_id=revenue.id,
        amount=53,
        entity_id=entity.id,
    )
    session.add(line_item4)
    session.flush()

    transaction4.line_items.add(line_item4)
    session.add(transaction4)
    session.flush()

    transaction4.post(session)

    statement = client.statement(session)

    assert statement["opening_balance"] == -25

    assert statement["transactions"][0].debit == 110
    assert statement["transactions"][0].credit == 0
    assert statement["transactions"][0].balance == 85

    assert statement["transactions"][1].debit == 0
    assert statement["transactions"][1].credit == 25
    assert statement["transactions"][1].balance == 60

    assert statement["transactions"][2].debit == 0
    assert statement["transactions"][2].credit == 107
    assert statement["transactions"][2].balance == -47

    assert statement["transactions"][3].debit == 0
    assert statement["transactions"][3].credit == 53
    assert statement["transactions"][3].balance == -100

    assert statement["closing_balance"] == -100


def test_supplier_account_statement(session, entity, currency):
    """Tests a supplier account's statement"""

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
    expense = Account(
        name="test account six",
        account_type=Account.AccountType.DIRECT_EXPENSE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    supplier = Account(
        name="test account seven",
        account_type=Account.AccountType.PAYABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add_all([bank_account, control, expense, supplier])
    session.commit()

    # opening balances
    date = datetime.now() - relativedelta(days=365)
    session.add_all(
        [
            Balance(
                transaction_date=date,
                transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
                amount=68,
                balance_type=Balance.BalanceType.DEBIT,
                account_id=supplier.id,
                entity_id=entity.id,
            ),
            Balance(
                transaction_date=date,
                transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
                amount=73,
                balance_type=Balance.BalanceType.CREDIT,
                account_id=supplier.id,
                entity_id=entity.id,
            ),
        ]
    )
    session.flush()

    # supplier bill
    transaction = SupplierBill(
        narration="Test transaction one",
        transaction_date=datetime.now(),
        account_id=supplier.id,
        entity_id=entity.id,
    )
    session.add(transaction)
    session.commit()

    tax = Tax(
        name="Input Vat",
        code="INPT",
        account_id=control.id,
        rate=8,
        entity_id=entity.id,
    )
    session.add(tax)
    session.flush()

    line_item1 = LineItem(
        narration="Test line item one",
        account_id=expense.id,
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

    # debit note
    transaction2 = DebitNote(
        narration="Test transaction two",
        transaction_date=datetime.now(),
        account_id=supplier.id,
        entity_id=entity.id,
    )
    session.add(transaction2)
    session.commit()

    session.add(tax)
    session.flush()

    line_item2 = LineItem(
        narration="Test line item two",
        account_id=expense.id,
        amount=75,
        tax_id=tax.id,
        entity_id=entity.id,
    )
    session.add(line_item2)
    session.flush()

    transaction2.line_items.add(line_item2)
    session.add(transaction2)
    session.flush()

    transaction2.post(session)

    # supplier payment
    transaction3 = SupplierPayment(
        narration="Test transaction three",
        transaction_date=datetime.now(),
        account_id=supplier.id,
        entity_id=entity.id,
    )
    session.add(transaction3)
    session.commit()

    line_item3 = LineItem(
        narration="Test line item three",
        account_id=bank_account.id,
        amount=63,
        entity_id=entity.id,
    )
    session.add(line_item3)
    session.flush()

    transaction3.line_items.add(line_item3)
    session.add(transaction3)
    session.flush()

    transaction3.post(session)

    # debit journal entry
    transaction4 = JournalEntry(
        narration="Test transaction four",
        transaction_date=datetime.now(),
        account_id=supplier.id,
        entity_id=entity.id,
        credited=False,
    )
    session.add(transaction4)
    session.commit()

    line_item4 = LineItem(
        narration="Test line item four",
        account_id=expense.id,
        amount=53,
        entity_id=entity.id,
    )
    session.add(line_item4)
    session.flush()

    transaction4.line_items.add(line_item4)
    session.add(transaction4)
    session.flush()

    transaction4.post(session)

    statement = supplier.statement(session)

    assert statement["opening_balance"] == -5

    assert statement["transactions"][0].debit == 0
    assert statement["transactions"][0].credit == 108
    assert statement["transactions"][0].balance == -113

    assert statement["transactions"][1].debit == 81
    assert statement["transactions"][1].credit == 0
    assert statement["transactions"][1].balance == -32

    assert statement["transactions"][2].debit == 63
    assert statement["transactions"][2].credit == 0
    assert statement["transactions"][2].balance == 31

    assert statement["transactions"][3].debit == 53
    assert statement["transactions"][3].credit == 0
    assert statement["transactions"][3].balance == 84

    assert statement["closing_balance"] == 84


def test_receivable_account_schedule(session, entity, currency):
    """Tests a receivable account's schedule"""

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
    session.add_all([client, revenue, control, bank_account])
    session.commit()

    # opening balances
    date = datetime.now() - relativedelta(days=365)
    balance = Balance(
        transaction_date=date,
        transaction_type=Transaction.TransactionType.CLIENT_INVOICE,
        amount=45,
        balance_type=Balance.BalanceType.DEBIT,
        account_id=client.id,
        entity_id=entity.id,
    )
    session.add_all(
        [
            balance,
            Balance(
                transaction_date=date,
                transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
                amount=70,
                balance_type=Balance.BalanceType.CREDIT,
                account_id=client.id,
                entity_id=entity.id,
            ),
        ]
    )
    session.flush()

    # client invoice
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

    # client receipt
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
        assigned_id=balance.id,
        assigned_type=balance.__class__.__name__,
        entity_id=entity.id,
        amount=15,
    )
    session.add(assignment1)
    session.flush()

    # credit note
    transaction3 = CreditNote(
        narration="Test transaction three",
        transaction_date=datetime.now(),
        account_id=client.id,
        entity_id=entity.id,
    )
    session.add(transaction3)
    session.commit()

    tax = Tax(
        name="Output Vat",
        code="OTPT",
        account_id=control.id,
        rate=7,
        entity_id=entity.id,
    )
    session.add(tax)
    session.flush()

    line_item3 = LineItem(
        narration="Test line item three",
        account_id=revenue.id,
        amount=80,
        tax_id=tax.id,
        entity_id=entity.id,
    )
    session.add(line_item3)
    session.flush()

    transaction3.line_items.add(line_item3)
    session.add(transaction3)
    session.flush()

    transaction3.post(session)

    assignment2 = Assignment(
        assignment_date=datetime.now(),
        transaction_id=transaction3.id,
        assigned_id=transaction.id,
        assigned_type=transaction.__class__.__name__,
        entity_id=entity.id,
        amount=85.6,
    )
    session.add(assignment2)
    session.flush()

    # journal entry
    transaction4 = JournalEntry(
        narration="Test transaction four",
        transaction_date=datetime.now(),
        account_id=client.id,
        entity_id=entity.id,
        credited=False,
    )
    session.add(transaction4)
    session.commit()

    line_item4 = LineItem(
        narration="Test line item four",
        account_id=revenue.id,
        amount=50,
        entity_id=entity.id,
    )
    session.add(line_item4)
    session.flush()

    transaction4.line_items.add(line_item4)
    session.add(transaction4)
    session.flush()

    transaction4.post(session)

    statement = client.statement(session, None, None, True)

    assert statement["transactions"][0].amount == 45
    assert statement["transactions"][0].cleared_amount == 15
    assert statement["transactions"][0].uncleared_amount == 30
    assert statement["transactions"][0].age == 365

    assert statement["transactions"][1].amount == 110
    assert statement["transactions"][1].cleared_amount == Decimal("85.6")
    assert statement["transactions"][1].uncleared_amount == Decimal("24.4")
    assert statement["transactions"][1].age == 2

    assert statement["transactions"][2].amount == 50
    assert statement["transactions"][2].cleared_amount == 0
    assert statement["transactions"][2].uncleared_amount == 50
    assert statement["transactions"][2].age == 0

    assert statement["total_amount"] == 205
    assert statement["cleared_amount"] == Decimal("100.6")
    assert statement["uncleared_amount"] == Decimal("104.4")


def test_supplier_account_schedule(session, entity, currency):
    """Tests a supplier account's schedule"""

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
    expense = Account(
        name="test account six",
        account_type=Account.AccountType.DIRECT_EXPENSE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    supplier = Account(
        name="test account seven",
        account_type=Account.AccountType.PAYABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add_all([bank_account, control, expense, supplier])
    session.commit()

    # opening balances
    date = datetime.now() - relativedelta(days=365)
    balance = Balance(
        transaction_date=date,
        transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
        amount=73,
        balance_type=Balance.BalanceType.CREDIT,
        account_id=supplier.id,
        entity_id=entity.id,
    )
    session.add_all(
        [
            Balance(
                transaction_date=date,
                transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
                amount=68,
                balance_type=Balance.BalanceType.DEBIT,
                account_id=supplier.id,
                entity_id=entity.id,
            ),
            balance,
        ]
    )
    session.flush()

    # supplier bill
    transaction = SupplierBill(
        narration="Test transaction one",
        transaction_date=datetime.now() - relativedelta(days=4),
        account_id=supplier.id,
        entity_id=entity.id,
    )
    session.add(transaction)
    session.commit()

    tax = Tax(
        name="Input Vat",
        code="INPT",
        account_id=control.id,
        rate=8,
        entity_id=entity.id,
    )
    session.add(tax)
    session.flush()

    line_item1 = LineItem(
        narration="Test line item one",
        account_id=expense.id,
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

    # debit note
    transaction2 = DebitNote(
        narration="Test transaction two",
        transaction_date=datetime.now(),
        account_id=supplier.id,
        entity_id=entity.id,
    )
    session.add(transaction2)
    session.commit()

    session.add(tax)
    session.flush()

    line_item2 = LineItem(
        narration="Test line item two",
        account_id=expense.id,
        amount=75,
        tax_id=tax.id,
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
        assigned_id=balance.id,
        assigned_type=balance.__class__.__name__,
        entity_id=entity.id,
        amount=15,
    )
    session.add(assignment1)
    session.flush(assignment1)

    # supplier payment
    transaction3 = SupplierPayment(
        narration="Test transaction three",
        transaction_date=datetime.now(),
        account_id=supplier.id,
        entity_id=entity.id,
    )
    session.add(transaction3)
    session.commit()

    line_item3 = LineItem(
        narration="Test line item three",
        account_id=bank_account.id,
        amount=63,
        entity_id=entity.id,
    )
    session.add(line_item3)
    session.flush()

    transaction3.line_items.add(line_item3)
    session.add(transaction3)
    session.flush()

    transaction3.post(session)

    assignment2 = Assignment(
        assignment_date=datetime.now(),
        transaction_id=transaction3.id,
        assigned_id=transaction.id,
        assigned_type=transaction.__class__.__name__,
        entity_id=entity.id,
        amount=45,
    )
    session.add(assignment2)
    session.flush(assignment2)

    # journal entry
    transaction4 = JournalEntry(
        narration="Test transaction four",
        transaction_date=datetime.now(),
        account_id=supplier.id,
        entity_id=entity.id,
    )
    session.add(transaction4)
    session.commit()

    line_item4 = LineItem(
        narration="Test line item four",
        account_id=expense.id,
        amount=53,
        entity_id=entity.id,
    )
    session.add(line_item4)
    session.flush()

    transaction4.line_items.add(line_item4)
    session.add(transaction4)
    session.flush()

    transaction4.post(session)

    statement = supplier.statement(session, None, None, True)

    assert statement["transactions"][0].amount == 73
    assert statement["transactions"][0].cleared_amount == 15
    assert statement["transactions"][0].uncleared_amount == 58
    assert statement["transactions"][0].age == 365

    assert statement["transactions"][1].amount == 108
    assert statement["transactions"][1].cleared_amount == 45
    assert statement["transactions"][1].uncleared_amount == 63
    assert statement["transactions"][1].age == 4

    assert statement["transactions"][2].amount == 53
    assert statement["transactions"][2].cleared_amount == 0
    assert statement["transactions"][2].uncleared_amount == 53
    assert statement["transactions"][2].age == 0

    assert statement["total_amount"] == 234
    assert statement["cleared_amount"] == 60
    assert statement["uncleared_amount"] == 174
