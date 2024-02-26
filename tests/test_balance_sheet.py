from datetime import datetime
from dateutil.relativedelta import relativedelta
from python_accounting.reports import BalanceSheet
from python_accounting.models import (
    Account,
    Tax,
    LineItem,
    Transaction,
    Balance,
)
from python_accounting.transactions import SupplierBill, CashSale, JournalEntry


def test_balance_sheet(session, entity, currency):
    """Tests the generation of an entity's balance sheet"""

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
    equity = Account(
        name="test account four",
        account_type=Account.AccountType.EQUITY,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    reconciliation = Account(
        name="test account five",
        account_type=Account.AccountType.RECONCILIATION,
        currency_id=currency.id,
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
    inventory = Account(
        name="test account nine",
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
    session.add_all(
        [
            bank,
            revenue,
            control,
            equity,
            reconciliation,
            income,
            supplier,
            cogs,
            inventory,
            liability,
            asset,
        ]
    )
    session.flush()

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

    supplier_bill = SupplierBill(
        narration="Supplier bill",
        transaction_date=datetime.now(),
        account_id=supplier.id,
        entity_id=entity.id,
    )
    session.add(supplier_bill)
    session.commit()

    tax = Tax(
        name="Input Vat",
        code="INPT",
        account_id=control.id,
        rate=5,
        entity_id=entity.id,
    )
    session.add(tax)
    session.flush()

    line_item1 = LineItem(
        narration="Test line item one",
        account_id=asset.id,
        amount=100,
        tax_id=tax.id,
        entity_id=entity.id,
    )
    session.add(line_item1)
    session.flush()

    supplier_bill.line_items.add(line_item1)
    session.add(supplier_bill)
    session.flush()

    supplier_bill.post(session)

    cash_sale = CashSale(
        narration="Cash sale",
        transaction_date=datetime.now(),
        account_id=bank.id,
        entity_id=entity.id,
    )
    session.add(cash_sale)
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

    line_item2 = LineItem(
        narration="Test line item two",
        account_id=revenue.id,
        amount=200,
        tax_id=tax.id,
        entity_id=entity.id,
    )
    session.add(line_item2)
    session.flush()

    cash_sale.line_items.add(line_item2)
    session.add(cash_sale)
    session.flush()

    cash_sale.post(session)

    journal_entry = JournalEntry(
        narration="Journal entry",
        transaction_date=datetime.now(),
        account_id=equity.id,
        entity_id=entity.id,
    )
    session.add(journal_entry)
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

    line_item3 = LineItem(
        narration="Test line item three",
        account_id=reconciliation.id,
        amount=70,
        tax_id=tax.id,
        entity_id=entity.id,
    )
    session.add(line_item3)
    session.flush()

    journal_entry.line_items.add(line_item3)
    session.add(journal_entry)
    session.flush()

    journal_entry.post(session)

    session.commit()

    statement = BalanceSheet(session)

    # totals
    assert statement.totals["ASSETS"] == 420
    assert statement.totals["LIABILITIES"] == -213
    assert statement.totals["EQUITY"] == -7

    # balances
    assert statement.balances["ASSETS"]["Non Current Asset"] == 100
    assert statement.balances["ASSETS"]["Inventory"] == 100
    assert statement.balances["ASSETS"]["Bank"] == 220
    assert statement.balances["LIABILITIES"]["Control"] == -8
    assert statement.balances["LIABILITIES"]["Current Liability"] == -100
    assert statement.balances["LIABILITIES"]["Payable"] == -105
    assert statement.balances["EQUITY"]["Equity"] == -77
    assert statement.balances["EQUITY"]["Reconciliation"] == 70

    assert statement.balances["debit"] == 490
    assert statement.balances["credit"] == -490

    # results
    assert statement.result_amounts["NET_ASSETS"] == 207
    assert statement.result_amounts["TOTAL_EQUITY"] == 207

    print(statement)
