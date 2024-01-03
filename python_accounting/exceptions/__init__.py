class AccountingExeption(Exception):
    """Base accounting exception"""

    message: str

    def __str__(self) -> str:
        return f"{self.message}"


class AdjustingReportingPeriodError(AccountingExeption):
    """Only Journal Entry Transactions can be recorded for adjusting status reporting periods"""

    def __init__(self, reporting_period) -> None:
        self.message = f"Only Journal Entry Transactions can be recorded for Reporting Period: {reporting_period} which has the Adjusting Status"
        super().__init__()


class ClosedReportingPeriodError(AccountingExeption):
    """Transactions cannot be recorded for closed reporting periods"""

    def __init__(self, reporting_period) -> None:
        self.message = f"Transaction cannot be recorded because Reporting Period: {reporting_period} is Closed"
        super().__init__()


class DuplicateReportingPeriodError(AccountingExeption):
    """An Entity can only have one reporting period per calendar year"""

    message = "A reporting Period already exists for that calendar year"


class InvalidAccountTypeError(AccountingExeption):
    """The account type must be one of those given in the list"""

    def __init__(self, property, account_types: list) -> None:
        self.message = f"Property {property} must be one of: {', '.join(account_types)}"
        super().__init__()


class InvalidBalanceAccountError(AccountingExeption):
    """Income Statement Accounts cannot have an opening balance"""

    message = "Income Statement Accounts cannot have an opening balance"


class InvalidBalanceDateError(AccountingExeption):
    """Unless the Entity allows for mid year balances, the balance date must be earlier than its reporting period's start"""

    message = "Transaction date must be earlier than the first day of the Balance's Reporting Period"


class InvalidBalanceTransactionError(AccountingExeption):
    """Balance Transaction must be one of Client Invoice, Supplier Bill or Journal Entry"""

    message = "Balance Transaction must be one of Client Invoice, Supplier Bill or Journal Entry"


class InvalidCategoryAccountTypeError(AccountingExeption):
    """The account type must the same as the category account type"""

    def __init__(self, account_type, category_account_type) -> None:
        self.message = (
            f"Cannot assign {account_type} Account to {category_account_type} Category"
        )
        super().__init__()


class InvalidLineItemAccountError(AccountingExeption):
    """The Line Item main Account type must be one of those given in the list"""

    def __init__(self, classname, account_types: list) -> None:
        self.message = f"{classname} Transaction Line Item Account type be one of: {', '.join(account_types)}"
        super().__init__()


class InvalidMainAccountError(AccountingExeption):
    """The account type of the transaction must be of the type given"""

    def __init__(self, classname, account_type: str) -> None:
        self.message = f"{classname} Transaction main Account be of type {account_type}"
        super().__init__()


class InvalidTaxAccountError(AccountingExeption):
    """A Tax account must be of type Control"""

    message = "A Tax account must be of type Control"


class InvalidTaxChargeError(AccountingExeption):
    """A Contra Entry Transaction cannot be charged Tax"""

    def __init__(self, classname) -> None:
        self.message = f"{classname} Transactions cannot be charged Tax"
        super().__init__()


class InvalidTransactionDateError(AccountingExeption):
    """The Transaction date cannot be the exact beginning of the reporting period"""

    message = "The Transaction date cannot be at the exact beginning of the Reporting Period. Use a Balance object instead"


class MissingEntityError(AccountingExeption):
    """Accounting objects must all be associated with an Entity"""

    message = "Accounting objects must have an Entity"


class MissingLineItemError(AccountingExeption):
    """A Transaction must have at least one Line Item to be posted"""

    message = "A Transaction must have at least one Line Item to be posted"


class MissingMainAccountAmountError(AccountingExeption):
    """A Compound Journal Entry Transaction must have a main account amount"""

    message = "A Compound Journal Entry Transaction must have a main account amount"


class MissingReportingPeriodError(AccountingExeption):
    """The Entity does not have a reporting period for the given date"""

    def __init__(self, entity, year) -> None:
        self.message = f"Entity <{entity}> has no reporting period for the year {year}"
        super().__init__()


class MissingTaxAccountError(AccountingExeption):
    """A non Zero Rate Tax must have an associated control account"""

    message = "A non Zero Rate Tax must have an associated Control Account"


class MultipleOpenPeriodsError(AccountingExeption):
    """An Entity can only have one reporting period open at a time"""

    message = "There can only be one Open Reporting Period per Entity at a time"


class NegativeAmountError(AccountingExeption):
    """Accounting amounts should not be negative"""

    def __init__(self, amount_class, property="amount") -> None:
        self.message = f"{amount_class} {property} cannot be negative"
        super().__init__()


class PostedTransactionError(AccountingExeption):
    """Changes are not allowed for a posted Transaction"""

    def __init__(self, message) -> None:
        self.message = message
        super().__init__()


class RedundantTransactionError(AccountingExeption):
    """A Transaction main account cannot be used as the account for any of its Line Items"""

    def __init__(self, line_item) -> None:
        self.message = (
            f"Line Item <{line_item}> Account is the same as the Transaction Account"
        )
        super().__init__()


class SessionEntityError(AccountingExeption):
    """The Session Entity should not be deleted"""

    message = "Cannot delete the session Entity"


class UnbalancedTransactionError(AccountingExeption):
    """Total Debit amounts do not match total Credit amounts"""

    message = "Total Debit amounts do not match total Credit amounts"


class UnassignableTransactionError(AccountingExeption):
    """The Transaction type must be one of those given in the list"""

    def __init__(self, classname, transaction_types: list) -> None:
        self.message = f"{classname} Transaction cannot be assigned. Assignment Transaction type must be one of: {', '.join(transaction_types)}"
        super().__init__()


class UnclearableTransactionError(AccountingExeption):
    """The Transaction type must be one of those given in the list"""

    def __init__(self, classname, transaction_types: list) -> None:
        self.message = f"{classname} Transaction cannot be cleared. Assignment assigned transaction type be must one of: {', '.join(transaction_types)}"
        super().__init__()


class UnpostedAssignmentError(AccountingExeption):
    """An unposted Transaction cannot be cleared or assigned"""

    message = "An unposted Transaction cannot be cleared or assigned"


class SelfClearanceError(AccountingExeption):
    """A Transaction cannot clear/be assigned to itself"""

    message = "A Transaction cannot clear/be assigned to itself"


class InvalidAssignmentAccountError(AccountingExeption):
    """The main account for the cleared and clearing Transaction must be the same"""

    message = (
        "The main account for the cleared and clearing Transaction must be the same"
    )


class InvalidClearanceEntryTypeError(AccountingExeption):
    """Transaction Entry increases the Main Account outstanding balance instead of reducing it"""

    def __init__(self, entry_type: str) -> None:
        self.message = f"Transaction {entry_type} entry increases the outstaning balance on the account instead of reducing it"
        super().__init__()


class CompoundTransactionAssignmentError(AccountingExeption):
    """A compound Transaction cannot be cleared or assigned"""

    message = "A compound Transaction cannot be cleared or assigned"


class InsufficientBalanceError(AccountingExeption):
    """Assigning Transaction does not have suffecient balance to clear the amount specified of the assigned"""

    def __init__(self, assigning: str, amount: float, assigned: str) -> None:
        self.message = f"{assigning} Transaction doesn't not have sufficient balance available to clear {amount} of the {assigned} Transaction"
        super().__init__()


class OverclearanceError(AccountingExeption):
    """The assigned Transaction has already been completely cleared"""

    def __init__(self, assigned: str) -> None:
        self.message = f"The {assigned} Transaction has already been completely cleared"
        super().__init__()


class MixedAssignmentError(AccountingExeption):
    """An assigned/cleared cannot be cleared/assigned"""

    def __init__(self, previous: str, current: str) -> None:
        self.message = f"A Transaction that has been {previous} cannot be {current}"
        super().__init__()
