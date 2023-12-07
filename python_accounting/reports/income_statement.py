from strenum import StrEnum
from python_accounting.models import Account


class IncomeStatement:
    """This class represents the Income Statement/Profit and Loss of a given Entity"""

    IncomeStatementAccounts = StrEnum(
        "IncomeStatementAccounts",
        {
            a.name: a.value
            for a in [
                Account.AccountType.OPERATING_REVENUE,
                Account.AccountType.NON_OPERATING_REVENUE,
                Account.AccountType.OPERATING_EXPENSE,
                Account.AccountType.DIRECT_EXPENSE,
                Account.AccountType.OVERHEAD_EXPENSE,
                Account.AccountType.OTHER_EXPENSE,
            ]
        },
    )
