import pytest
from datetime import datetime
from dateutil.relativedelta import relativedelta
from python_accounting.transactions import ClientReceipt, ClientInvoice, JournalEntry
from python_accounting.models import Account, Assignment, Balance, LineItem, Transaction
from python_accounting.exceptions import (
    UnassignableTransactionError,
    UnclearableTransactionError,
    NegativeValueError,
    UnpostedAssignmentError,
    SelfClearanceError,
    InvalidAssignmentAccountError,
    InvalidClearanceEntryTypeError,
    CompoundTransactionAssignmentError,
    InsufficientBalanceError,
    OverclearanceError,
    MixedAssignmentError,
)


def test_assignment_entity(session, entity, currency):
    """Tests the relationship between a assignment and its associated entity"""

    account1 = Account(
        name="test account one",
        account_type=Account.AccountType.RECEIVABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account2 = Account(
        name="test account two",
        account_type=Account.AccountType.OPERATING_REVENUE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account3 = Account(
        name="test account three",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add_all([account1, account2, account3])
    session.flush()

    balance = Balance(
        transaction_date=datetime.now() - relativedelta(years=1),
        transaction_type=Transaction.TransactionType.CLIENT_INVOICE,
        amount=100,
        balance_type=Balance.BalanceType.DEBIT,
        account_id=account1.id,
        entity_id=entity.id,
    )
    session.add(balance)
    session.commit()

    transaction2 = ClientReceipt(
        narration="Test transaction one",
        transaction_date=datetime.now(),
        account_id=account1.id,
        entity_id=entity.id,
    )
    session.add(transaction2)
    session.commit()

    line_item2 = LineItem(
        narration="Test line item two",
        account_id=account3.id,
        amount=50,
        entity_id=entity.id,
    )
    session.add(line_item2)
    session.flush()

    transaction2.line_items.add(line_item2)
    session.add(transaction2)
    session.flush()

    transaction2.post(session)

    assignment = Assignment(
        assignment_date=datetime.now(),
        transaction_id=transaction2.id,
        assigned_id=balance.id,
        assigned_type=balance.__class__.__name__,
        entity_id=entity.id,
        amount=15,
    )
    session.add(assignment)
    session.commit()

    assignment = session.get(Assignment, assignment.id)
    assert assignment.entity.name == "Test Entity"

    assert assignment.assigned(session) == balance
    assert balance.cleared(session) == 15
    assert balance.clearances(session)[0] == assignment
    assert transaction2.balance(session) == 35
    assert transaction2.assignments(session)[0] == assignment

    balance.unclear(session)
    assert balance.clearances(session) == []
    assert transaction2.assignments(session) == []

    session.rollback()

    assert balance.clearances(session)[0] == assignment
    assert transaction2.assignments(session)[0] == assignment

    transaction2.unassign(session)
    assert balance.clearances(session) == []
    assert transaction2.assignments(session) == []


def test_assignment_validation(session, entity, currency):
    """Tests the validation of assignment objects"""

    account1 = Account(
        name="test account one",
        account_type=Account.AccountType.RECEIVABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account2 = Account(
        name="test account two",
        account_type=Account.AccountType.OPERATING_REVENUE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account3 = Account(
        name="test account three",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add_all([account1, account2, account3])
    session.flush()

    transaction1 = ClientInvoice(
        narration="Test transaction one",
        transaction_date=datetime.now(),
        account_id=account1.id,
        entity_id=entity.id,
    )
    session.add(transaction1)
    session.commit()

    line_item1 = LineItem(
        narration="Test line item one",
        account_id=account2.id,
        amount=50,
        entity_id=entity.id,
    )
    session.add(line_item1)
    session.flush()

    transaction1.line_items.add(line_item1)
    session.add(transaction1)
    session.flush()

    transaction1.post(session)

    transaction2 = ClientReceipt(
        narration="Test transaction one",
        transaction_date=datetime.now(),
        account_id=account1.id,
        entity_id=entity.id,
    )
    session.add(transaction2)
    session.commit()

    line_item2 = LineItem(
        narration="Test line item two",
        account_id=account3.id,
        amount=50,
        entity_id=entity.id,
    )
    session.add(line_item2)
    session.flush()

    transaction2.line_items.add(line_item2)
    session.add(transaction2)
    session.flush()

    transaction2.post(session)

    assignment = Assignment(
        assignment_date=datetime.now(),
        transaction_id=transaction1.id,
        assigned_id=transaction1.id,
        assigned_type=transaction1.__class__.__name__,
        entity_id=entity.id,
        amount=15,
    )

    with pytest.raises(UnassignableTransactionError) as e:
        session.add(assignment)
    assert (
        str(e.value)
        == """ClientInvoice Transaction cannot be assigned. Assignment
         Transaction type must be one of: Client Receipt, Supplier Payment, Credit Note, Debit Note, Journal Entry."""
    )
    session.expunge(assignment)

    assignment.transaction_id = transaction2.id
    assignment.assigned_id = transaction2.id

    with pytest.raises(UnclearableTransactionError) as e:
        session.add(assignment)
    assert (
        str(e.value)
        == """ClientReceipt Transaction cannot be cleared. Assignment
         assigned transaction type be must one of: Client Invoice, Supplier Bill, Journal Entry."""
    )
    session.expunge(assignment)

    assignment.assigned_id = transaction1.id
    assignment.amount = -1

    with pytest.raises(NegativeValueError) as e:
        session.add(assignment)
    assert str(e.value) == "Assignment amount cannot be negative."

    session.expunge(assignment)
    assignment.amount = 5000

    with pytest.raises(InsufficientBalanceError) as e:
        session.add(assignment)
    assert (
        str(e.value)
        == """ClientReceipt Transaction doesn't not have sufficient balance
         available to clear 5000 of the ClientInvoice Transaction."""
    )

    session.expunge(assignment)

    line_item3 = LineItem(
        narration="Test line item three",
        account_id=account3.id,
        amount=50,
        entity_id=entity.id,
    )
    session.add(line_item3)
    session.flush()

    transaction3 = JournalEntry(
        narration="Test transaction three",
        transaction_date=datetime.now(),
        account_id=account1.id,
        entity_id=entity.id,
    )
    transaction3.line_items.add(line_item3)
    session.add(transaction3)
    session.commit()

    assignment.assigned_id = transaction3.id
    assignment.amount = 15

    with pytest.raises(UnpostedAssignmentError) as e:
        session.add(assignment)
    assert str(e.value) == "An unposted Transaction cannot be cleared or assigned."

    session.expunge(assignment)
    transaction3.post(session)

    assignment.transaction_id = transaction3.id

    with pytest.raises(SelfClearanceError) as e:
        session.add(assignment)
    assert str(e.value) == "A Transaction cannot clear/be assigned to itself."

    session.expunge(assignment)
    account4 = Account(
        name="test account one",
        account_type=Account.AccountType.RECEIVABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add(account4)

    line_item4 = LineItem(
        narration="Test line item four",
        account_id=account3.id,
        amount=50,
        entity_id=entity.id,
    )
    session.add(line_item4)
    session.flush()

    transaction4 = JournalEntry(
        narration="Test transaction four",
        transaction_date=datetime.now(),
        account_id=account4.id,
        entity_id=entity.id,
    )
    transaction4.line_items.add(line_item4)
    session.add(transaction4)

    transaction4.post(session)

    assignment.assigned_id = transaction4.id

    with pytest.raises(InvalidAssignmentAccountError) as e:
        session.add(assignment)
    assert (
        str(e.value)
        == "The main account for the cleared and clearing Transaction must be the same."
    )

    session.expunge(assignment)

    line_item5 = LineItem(
        narration="Test line item five",
        account_id=account3.id,
        amount=50,
        entity_id=entity.id,
    )
    session.add(line_item5)
    session.flush()

    transaction5 = JournalEntry(
        narration="Test transaction five",
        transaction_date=datetime.now(),
        account_id=account1.id,
        entity_id=entity.id,
    )
    transaction5.line_items.add(line_item5)
    session.add(transaction5)
    transaction5.post(session)

    assignment.assigned_id = transaction5.id

    with pytest.raises(InvalidClearanceEntryTypeError) as e:
        session.add(assignment)
    assert (
        str(e.value)
        == """Transaction Credit entry increases the outstaning balance
         on the account instead of reducing it."""
    )

    session.expunge(assignment)
    transaction5.compound = True
    with pytest.raises(CompoundTransactionAssignmentError) as e:
        session.add(assignment)
    assert str(e.value) == "A compound Transaction cannot be cleared or assigned."

    session.expunge(assignment)
    session.expunge(transaction5)

    line_item6 = LineItem(
        narration="Test line item six",
        account_id=account3.id,
        amount=50,
        entity_id=entity.id,
    )
    session.add(line_item6)
    session.flush()

    transaction6 = JournalEntry(
        narration="Test transaction six",
        transaction_date=datetime.now(),
        account_id=account1.id,
        entity_id=entity.id,
    )
    transaction6.line_items.add(line_item6)
    session.add(transaction6)
    transaction6.post(session)

    assignment.assigned_id = transaction1.id
    assignment.amount = 40
    session.add(assignment)
    session.commit()

    assignment = Assignment(
        assignment_date=datetime.now(),
        transaction_id=transaction6.id,
        assigned_id=transaction1.id,
        assigned_type=transaction1.__class__.__name__,
        entity_id=entity.id,
        amount=15,
    )

    with pytest.raises(OverclearanceError) as e:
        session.add(assignment)
    assert (
        str(e.value)
        == "The ClientInvoice Transaction has already been completely cleared."
    )

    session.expunge(assignment)

    line_item7 = LineItem(
        narration="Test line item seven",
        account_id=account3.id,
        amount=50,
        entity_id=entity.id,
    )
    session.add(line_item7)
    session.flush()

    transaction7 = JournalEntry(
        narration="Test transaction seven",
        transaction_date=datetime.now(),
        account_id=account1.id,
        entity_id=entity.id,
        credited=False,
    )
    transaction7.line_items.add(line_item7)
    session.add(transaction7)
    transaction7.post(session)

    session.add(
        Assignment(
            assignment_date=datetime.now(),
            transaction_id=transaction3.id,
            assigned_id=transaction7.id,
            assigned_type=transaction7.__class__.__name__,
            entity_id=entity.id,
            amount=5,
        )
    )
    session.flush()

    assignment = Assignment(
        assignment_date=datetime.now(),
        transaction_id=transaction7.id,
        assigned_id=transaction3.id,
        assigned_type=transaction3.__class__.__name__,
        entity_id=entity.id,
        amount=5,
    )
    session.add(assignment)

    with pytest.raises(MixedAssignmentError) as e:
        session.flush()
    assert str(e.value) == "A Transaction that has been Cleared cannot be Assigned."

    session.expunge(assignment)

    line_item8 = LineItem(
        narration="Test line item eight",
        account_id=account3.id,
        amount=50,
        entity_id=entity.id,
    )
    session.add(line_item8)
    session.flush()

    transaction8 = JournalEntry(
        narration="Test transaction eight",
        transaction_date=datetime.now(),
        account_id=account1.id,
        entity_id=entity.id,
    )
    transaction8.line_items.add(line_item8)
    session.add(transaction8)
    transaction8.post(session)

    session.add(
        Assignment(
            assignment_date=datetime.now(),
            transaction_id=transaction8.id,
            assigned_id=transaction7.id,
            assigned_type=transaction5.__class__.__name__,
            entity_id=entity.id,
            amount=5,
        )
    )

    session.commit()

    line_item9 = LineItem(
        narration="Test line item nine",
        account_id=account3.id,
        amount=50,
        entity_id=entity.id,
    )
    session.add(line_item9)
    session.flush()

    transaction9 = JournalEntry(
        narration="Test transaction nine",
        transaction_date=datetime.now(),
        account_id=account1.id,
        entity_id=entity.id,
        credited=False,
    )
    transaction9.line_items.add(line_item9)
    session.add(transaction9)
    transaction9.post(session)

    assignment = Assignment(
        assignment_date=datetime.now(),
        transaction_id=transaction9.id,
        assigned_id=transaction8.id,
        assigned_type=transaction8.__class__.__name__,
        entity_id=entity.id,
        amount=5,
    )

    with pytest.raises(MixedAssignmentError) as e:
        session.add(assignment)
    assert str(e.value) == "A Transaction that has been Assigned cannot be Cleared."


def test_bulk_assignment(session, entity, currency):
    """Tests the bulk assignment of a clearing Transaction"""

    revenue = Account(
        name="revenue account",
        account_type=Account.AccountType.OPERATING_REVENUE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    client = Account(
        name="client account",
        account_type=Account.AccountType.RECEIVABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    bank = Account(
        name="Bank",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )

    session.add_all([revenue, client, bank])
    session.flush()

    balance = Balance(
        transaction_date=datetime.now() - relativedelta(years=1),
        transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
        amount=75,
        balance_type=Balance.BalanceType.DEBIT,
        account_id=client.id,
        entity_id=entity.id,
    )
    session.add(balance)

    invoice = ClientInvoice(
        narration="Test transaction one",
        transaction_date=datetime.now(),
        account_id=client.id,
        entity_id=entity.id,
    )
    session.add(invoice)
    session.commit()

    line_item1 = LineItem(
        narration="Test line item one",
        account_id=revenue.id,
        amount=100,
        entity_id=entity.id,
    )
    session.add(line_item1)
    session.flush()

    invoice.line_items.add(line_item1)
    session.add(invoice)
    session.flush()

    invoice.post(session)

    receipt = ClientReceipt(
        narration="Client Receipt",
        transaction_date=datetime.now(),
        account_id=client.id,
        entity_id=entity.id,
    )
    session.add(receipt)
    session.commit()

    line_item2 = LineItem(
        narration="Test line item two",
        account_id=bank.id,
        amount=100,
        entity_id=entity.id,
    )
    session.add(line_item2)
    session.flush()

    receipt.line_items.add(line_item2)
    session.add(receipt)
    session.flush()

    receipt.post(session)

    receipt.bulk_assign(session)

    assignments = receipt.assignments(session)
    assert len(assignments) == 2
    assert assignments[0].amount == 75
    assert assignments[1].amount == 25

    assert balance.cleared(session) == 75
    assert invoice.cleared(session) == 25
