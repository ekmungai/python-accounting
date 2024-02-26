from datetime import datetime
from dateutil.relativedelta import relativedelta
from python_accounting.models import (
    Account,
    Tax,
    LineItem,
    Category,
    Balance,
    Transaction,
)
from python_accounting.transactions import (
    CashSale,
    ClientInvoice,
    CreditNote,
    JournalEntry,
    SupplierBill,
    CashPurchase,
)
from python_accounting.reports import TrialBalance


def test_trial_balance(session, entity, currency):
    """Tests the generation of an entity's trial balance"""

    # INCOME STATEMENT
    category = Category(
        name="Test Category",
        category_account_type=Account.AccountType.OPERATING_REVENUE,
        entity_id=entity.id,
    )
    session.add(category)
    session.commit()

    bank = Account(
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
    client = Account(
        name="test account four",
        account_type=Account.AccountType.RECEIVABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    revenue2 = Account(
        name="test account five",
        account_type=Account.AccountType.OPERATING_REVENUE,
        currency_id=currency.id,
        category_id=category.id,
        entity_id=entity.id,
    )
    income = Account(
        name="test account six",
        account_type=Account.AccountType.NON_OPERATING_REVENUE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    supplier = Account(
        name="test account seven",
        account_type=Account.AccountType.PAYABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    cogs = Account(
        name="test account eight",
        account_type=Account.AccountType.OPERATING_EXPENSE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    expense = Account(
        name="test account nine",
        account_type=Account.AccountType.DIRECT_EXPENSE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    overhead = Account(
        name="test account ten",
        account_type=Account.AccountType.OVERHEAD_EXPENSE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    inventory = Account(
        name="test account eleven",
        account_type=Account.AccountType.INVENTORY,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    liability = Account(
        name="test account ten",
        account_type=Account.AccountType.CURRENT_LIABILITY,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    asset = Account(
        name="test account eleven",
        account_type=Account.AccountType.NON_CURRENT_ASSET,
        currency_id=currency.id,
        entity_id=entity.id,
    )

    equity = Account(
        name="test account twelve",
        account_type=Account.AccountType.EQUITY,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    reconciliation = Account(
        name="test account thirteen",
        account_type=Account.AccountType.RECONCILIATION,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add_all(
        [
            bank,
            revenue,
            control,
            client,
            revenue2,
            income,
            supplier,
            cogs,
            expense,
            overhead,
            inventory,
            asset,
            liability,
            equity,
            reconciliation,
        ]
    )
    session.flush()

    tax = Tax(
        name="Output Vat",
        code="OTPT",
        account_id=control.id,
        rate=10,
        entity_id=entity.id,
    )
    tax2 = Tax(
        name="Input Vat",
        code="INPT",
        account_id=control.id,
        rate=10,
        entity_id=entity.id,
    )
    session.add_all([tax, tax2])
    session.flush()

    # -------------------
    # Operating Revenues
    # -------------------

    # cash sale
    cash_sale = CashSale(
        narration="Test cash sale",
        transaction_date=datetime.now(),
        account_id=bank.id,
        entity_id=entity.id,
    )
    session.add(cash_sale)
    session.commit()

    line_item1 = LineItem(
        narration="Test line item one",
        account_id=revenue.id,
        amount=200,
        tax_id=tax.id,
        entity_id=entity.id,
    )
    session.add(line_item1)
    session.flush()

    cash_sale.line_items.add(line_item1)
    session.add(cash_sale)
    session.flush()

    cash_sale.post(session)

    # client invoice
    client_invoice = ClientInvoice(
        narration="Test client invoice",
        transaction_date=datetime.now(),
        account_id=client.id,
        entity_id=entity.id,
    )
    session.add(client_invoice)
    session.commit()

    line_item2 = LineItem(
        narration="Test line item two",
        account_id=revenue2.id,
        amount=100,
        tax_id=tax.id,
        entity_id=entity.id,
    )
    session.add(line_item2)
    session.flush()

    client_invoice.line_items.add(line_item2)
    session.add(client_invoice)
    session.flush()

    client_invoice.post(session)

    # credit note
    credit_note = CreditNote(
        narration="Test credit note",
        transaction_date=datetime.now(),
        account_id=client.id,
        entity_id=entity.id,
    )
    session.add(credit_note)
    session.commit()

    line_item3 = LineItem(
        narration="Test line item three",
        account_id=revenue.id,
        amount=80,
        tax_id=tax.id,
        entity_id=entity.id,
    )
    session.add(line_item3)
    session.flush()

    credit_note.line_items.add(line_item3)
    session.add(credit_note)
    session.flush()

    credit_note.post(session)

    # -----------------------
    # Non Operating Revenues
    # -----------------------

    line_item4 = LineItem(
        narration="Test line item four",
        account_id=bank.id,
        amount=50,
        entity_id=entity.id,
    )
    session.add(line_item4)
    session.flush()

    other_income = JournalEntry(
        narration="Test supplier_bill six",
        transaction_date=datetime.now(),
        account_id=income.id,
        entity_id=entity.id,
    )
    other_income.line_items.add(line_item4)
    session.add(other_income)
    other_income.post(session)

    # -------------------
    # Operating Expenses
    # -------------------

    # supplier bill
    supplier_bill = SupplierBill(
        narration="Test supplier bill",
        transaction_date=datetime.now(),
        account_id=supplier.id,
        entity_id=entity.id,
    )
    session.add(supplier_bill)
    session.commit()

    line_item5 = LineItem(
        narration="Test line item five",
        account_id=cogs.id,
        amount=100,
        tax_id=tax.id,
        entity_id=entity.id,
    )
    session.add(line_item5)
    session.flush()

    supplier_bill.line_items.add(line_item5)
    session.add(supplier_bill)
    session.flush()

    supplier_bill.post(session)

    # -------------------
    # Non Operating Expenses
    # -------------------

    cash_purchase = CashPurchase(
        narration="Test cash purchase",
        transaction_date=datetime.now(),
        account_id=bank.id,
        entity_id=entity.id,
    )
    session.add(cash_purchase)
    session.commit()

    line_item6 = LineItem(
        narration="Test line item six",
        account_id=expense.id,
        amount=65,
        tax_id=tax2.id,
        entity_id=entity.id,
    )
    session.add(line_item6)
    session.flush()

    cash_purchase.line_items.add(line_item6)
    session.add(cash_purchase)
    session.flush()

    cash_purchase.post(session)

    overhead_expense = CashPurchase(
        narration="Test cash purchase 2",
        transaction_date=datetime.now(),
        account_id=bank.id,
        entity_id=entity.id,
    )
    session.add(overhead_expense)
    session.commit()

    line_item7 = LineItem(
        narration="Test line item seven",
        account_id=overhead.id,
        amount=40,
        tax_id=tax2.id,
        entity_id=entity.id,
    )
    session.add(line_item7)
    session.flush()

    overhead_expense.line_items.add(line_item7)
    session.add(overhead_expense)
    session.flush()

    overhead_expense.post(session)

    # BALANCE SHEET
    session.add_all(
        [
            Balance(
                transaction_date=datetime.now() - relativedelta(years=1),
                transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
                amount=100,
                balance_type=Balance.BalanceType.DEBIT,
                account_id=inventory.id,
                entity_id=entity.id,
            ),
            Balance(
                transaction_date=datetime.now() - relativedelta(years=1),
                transaction_type=Transaction.TransactionType.SUPPLIER_BILL,
                amount=100,
                balance_type=Balance.BalanceType.CREDIT,
                account_id=liability.id,
                entity_id=entity.id,
            ),
        ]
    )

    supplier_bill2 = SupplierBill(
        narration="Supplier bill",
        transaction_date=datetime.now(),
        account_id=supplier.id,
        entity_id=entity.id,
    )
    session.add(supplier_bill2)
    session.commit()

    line_item9 = LineItem(
        narration="Test line item nine",
        account_id=asset.id,
        amount=100,
        tax_id=tax2.id,
        entity_id=entity.id,
    )
    session.add(line_item9)
    session.flush()

    supplier_bill2.line_items.add(line_item9)
    session.add(supplier_bill2)
    session.flush()

    supplier_bill2.post(session)

    cash_sale2 = CashSale(
        narration="Cash sale",
        transaction_date=datetime.now(),
        account_id=bank.id,
        entity_id=entity.id,
    )
    session.add(cash_sale2)
    session.commit()

    line_item10 = LineItem(
        narration="Test line item ten",
        account_id=revenue.id,
        amount=200,
        tax_id=tax.id,
        entity_id=entity.id,
    )
    session.add(line_item10)
    session.flush()

    cash_sale2.line_items.add(line_item10)
    session.add(cash_sale2)
    session.flush()

    cash_sale2.post(session)

    journal_entry2 = JournalEntry(
        narration="Journal entry",
        transaction_date=datetime.now(),
        account_id=equity.id,
        entity_id=entity.id,
    )
    session.add(journal_entry2)
    session.commit()

    line_item11 = LineItem(
        narration="Test line item eleven",
        account_id=reconciliation.id,
        amount=70,
        tax_id=tax.id,
        entity_id=entity.id,
    )
    session.add(line_item11)
    session.flush()

    journal_entry2.line_items.add(line_item11)
    session.add(journal_entry2)
    session.flush()

    journal_entry2.post(session)

    statement = TrialBalance(session)

    # totals
    assert statement.totals["INCOME_STATEMENT"] == -265
    assert statement.totals["BALANCE_SHEET"] == 265

    # # balances
    assert statement.balances["INCOME_STATEMENT"]["Operating Revenue"] == -420
    assert statement.balances["INCOME_STATEMENT"]["Non Operating Revenue"] == -50
    assert statement.balances["INCOME_STATEMENT"]["Operating Expense"] == 100
    assert statement.balances["INCOME_STATEMENT"]["Direct Expense"] == 65
    assert statement.balances["INCOME_STATEMENT"]["Overhead Expense"] == 40

    assert statement.balances["BALANCE_SHEET"]["Non Current Asset"] == 100
    assert statement.balances["BALANCE_SHEET"]["Inventory"] == 100
    assert statement.balances["BALANCE_SHEET"]["Bank"] == 374.5
    assert statement.balances["BALANCE_SHEET"]["Receivable"] == 22
    assert statement.balances["BALANCE_SHEET"]["Control"] == -4.5
    assert statement.balances["BALANCE_SHEET"]["Current Liability"] == -100
    assert statement.balances["BALANCE_SHEET"]["Payable"] == -220
    assert statement.balances["BALANCE_SHEET"]["Equity"] == -77
    assert statement.balances["BALANCE_SHEET"]["Reconciliation"] == 70

    # # results
    assert statement.result_amounts["DEBIT"] == 871.5
    assert statement.result_amounts["CREDIT"] == 871.5

    print(statement)
