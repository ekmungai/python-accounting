from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Enum
from python_accounting.mixins import IsolatingMixin
from strenum import StrEnum
from .recyclable import Recyclable


class Account(IsolatingMixin, Recyclable):
    """Represents an account which groups related Transactions"""

    class AccountType(StrEnum):
        """Account types"""

        # Balance Sheet: Asset Accounts
        NON_CURRENT_ASSET = "Non Current Asset"
        CONTRA_ASSET = "Contra Asset"
        INVENTORY = "Inventory"
        BANK = "Bank"
        CURRENT_ASSET = "Current Asset"
        RECEIVABLE = "Receivable"

        # Balance Sheet: Liabilities Accounts
        NON_CURRENT_LIABILITY = "Non Current Liability"
        CONTROL = "Control"
        CURRENT_LIABILITY = "Current Liability"
        PAYABLE = "Payable"
        RECONCILIATION = "Reconciliation"

        # Balance Sheet: Equity Accounts
        EQUITY = "Equity"

        # Income Statement: Operations Accounts
        OPERATING_REVENUE = "Operating Revenue"
        OPERATING_EXPENSE = "Operating Expense"

        # Income Statement: Non Operations Accounts
        NON_OPERATING_REVENUE = "Non Operating Revenue"
        DIRECT_EXPENSE = "Direct Expense"
        OVERHEAD_EXPENSE = "Overhead Expense"
        OTHER_EXPENSE = "Other Expense"

    __mapper_args__ = {"polymorphic_identity": "Account"}

    id: Mapped[int] = mapped_column(ForeignKey("recyclable.id"), primary_key=True)
    name: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(String(1000))
    code: Mapped[str] = mapped_column(String(10))
    account_type: Mapped[StrEnum] = mapped_column(Enum(AccountType))
    currency_id: Mapped[int] = mapped_column(ForeignKey("currency.id"), nullable=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("category.id"), nullable=True)

    # relationships
    currency: Mapped["Currency"] = relationship(foreign_keys=[currency_id])
    category: Mapped["Category"] = relationship(foreign_keys=[category_id])

    def __repr__(self) -> str:
        return f"{self.name} <{self.code}>"
