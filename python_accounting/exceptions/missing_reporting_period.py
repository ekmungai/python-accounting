from .base import AccountingExeption


class MissingReportingPeriodError(AccountingExeption):
    """The Entity does not have a reporting period for the given date"""

    def __init__(self, entity, year) -> None:
        self.message = f"Entity <{entity}> has no reporting period for the year {year}"
        super().__init__()
