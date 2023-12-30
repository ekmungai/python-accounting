from python_accounting.exceptions import (
    InvalidMainAccountError,
    InvalidLineItemAccountError,
)


class SellingMixin:
    """This class provides validation for transaction's that sell an entity's goods and services"""

    def _validate_subclass_line_items(self, line_item):
        from python_accounting.models import Account

        if line_item.account.account_type != Account.AccountType.OPERATING_REVENUE:
            raise InvalidLineItemAccountError(
                self.__class__.__name__, [Account.AccountType.OPERATING_REVENUE]
            )
        return line_item

    def validate(self, session) -> None:
        """Validate the selling Transaction properties"""
        from python_accounting.models import Account

        AccountTypeMap = {
            "ClientInvoice": Account.AccountType.RECEIVABLE,
            "CashSale": Account.AccountType.BANK,
        }

        account = self._get_main_account(session, self.account_id)

        if account.account_type not in [
            Account.AccountType.RECEIVABLE,
            Account.AccountType.BANK,
        ]:
            raise InvalidMainAccountError(
                self.__class__.__name__, AccountTypeMap[self.__class__.__name__]
            )
        super().validate(session)
