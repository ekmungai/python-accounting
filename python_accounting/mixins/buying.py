from python_accounting.exceptions import (
    InvalidMainAccountError,
    InvalidLineItemAccountError,
)


class BuyingMixin:
    """This class provides validation for transaction's that buy goods and services for an entity's"""

    def _validate_subclass_line_items(self, line_item):
        from python_accounting.models import Account

        if line_item.account.account_type not in Account.purchasables:
            raise InvalidLineItemAccountError(
                self.__class__.__name__, Account.purchasables
            )
        return line_item

    def validate(self, session) -> None:
        """Validate the buying Transaction properties"""
        from python_accounting.models import Account

        AccountTypeMap = {
            "SupplierBill": Account.AccountType.PAYABLE,
            "CashPurchase": Account.AccountType.BANK,
        }

        account = self._get_main_account(session, self.account_id)

        if account.account_type not in [
            Account.AccountType.PAYABLE,
            Account.AccountType.BANK,
        ]:
            raise InvalidMainAccountError(
                self.__class__.__name__, AccountTypeMap[self.__class__.__name__]
            )
        super().validate(session)
