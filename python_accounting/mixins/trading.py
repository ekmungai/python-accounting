from python_accounting.exceptions import (
    InvalidMainAccountError,
    InvalidLineItemAccountError,
)


class TradingMixin:
    """This class provides validation for transaction's that trade goods and services for an entity's"""

    def _validate_subclass_line_items(self, line_item):
        if line_item.account.account_type not in self.line_item_types:
            raise InvalidLineItemAccountError(
                self.__class__.__name__, self.line_item_types
            )
        return line_item

    def validate(self, session) -> None:
        """Validate the buying Transaction properties"""

        account = self._get_main_account(session, self.account_id)

        if account.account_type not in self.main_account_types:
            raise InvalidMainAccountError(
                self.__class__.__name__,
                self.account_type_map[self.__class__.__name__],
            )
        super().validate(session)
