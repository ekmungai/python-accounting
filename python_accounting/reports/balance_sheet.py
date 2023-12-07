from strenum import StrEnum
from python_accounting.models import Account


class BalanceSheet:
    """This class represents the Statement of Financial Position/Balance Sheet of a given Entity"""

    BalanceSheetAccounts = StrEnum(
        "BalanceSheetAccounts",
        {
            a.name: a.value
            for a in [
                Account.AccountType.NON_CURRENT_ASSET,
                Account.AccountType.CONTRA_ASSET,
                Account.AccountType.INVENTORY,
                Account.AccountType.BANK,
                Account.AccountType.CURRENT_ASSET,
                Account.AccountType.RECEIVABLE,
                Account.AccountType.NON_CURRENT_LIABILITY,
                Account.AccountType.CONTROL,
                Account.AccountType.CURRENT_LIABILITY,
                Account.AccountType.PAYABLE,
                Account.AccountType.EQUITY,
                Account.AccountType.RECONCILIATION,
            ]
        },
    )
