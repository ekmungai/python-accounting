from datetime import datetime
from sqlalchemy.orm.session import Session
from python_accounting.config import config
from python_accounting.models import Account


class FinancialStatement:
    """This class is an abstract representation of a Financial Statement as defined by IFRS and GAAP"""

    balances: dict
    accounts: dict
    totals: dict
    results: dict
    session: Session
    start_date: datetime
    end_date: datetime

    # printing
    printout: tuple
    width: str
    indent: str = " " * 4
    subtotal: str = "_" * 15
    grandtotal: str = "=" * 15

    def __init__(self, session: Session) -> None:
        self.session = session
        self.balances.update({"debit": 0, "credit": 0})

    def __str__(self) -> str:
        template = "{}\n" * len(self.sections)
        return template.format(*self.sections)

    def _get_sections(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
        full_balance: bool = True,
    ) -> None:
        """Get the balances of the accounts in the financial statement, aggregated by section"""

        for section, content in config.reports["income_statement"]["sections"].items():
            for account_type in content["account_types"]:
                balances = Account.section_balances(
                    self.session, [account_type], start_date, end_date, full_balance
                )
                account_type = Account.AccountType[account_type].value
                if balances["closing"] != 0:
                    self.accounts[section][account_type] = balances["categories"]
                    self.balances[section][account_type] = balances["closing"]
                    self.totals[section] += balances["closing"]
                    self.balances[
                        "debit" if balances["closing"] >= 0 else "credit"
                    ] += balances["closing"]

    def _print_title(self) -> str:
        """Print the title of the statement"""

        period = (
            f"For the period: {self.start_date.strftime(config.dates["long"])} to {self.end_date.strftime(config.dates["long"])}"
            if self.start_date
            else f"As at {self.end_date.strftime(config.dates["long"])}"
        )
        self.width = len(period)
        return f"\n{self.session.entity.name.center(self.width)}\n{self.title.center(self.width)}\n{period}"
    
    def _print_section(self, section, factor = 1) -> str:
        """Print the contents of a section of the statement"""
        content = f"\n{section.value}"
        
        for account_type, balance in self.balances[section.name].items():
            label = f"\n{self.indent}{account_type}" 
            content += f"{label}{balance * factor:>{self.width - len(label) + 1}}"
        return content

    def _print_result(self, result, grandtotal = False) -> str:
        """Print the results of a statement"""
        return "{}\n{}{}\n{}".format(
            f"{self.subtotal:>{self.width}}", 
            result, 
            f"{self.results[result.name]:>{self.width - len(result)}}", 
            f"{self.grandtotal:>{self.width}}" if grandtotal else ""
        )
