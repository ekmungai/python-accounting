from strenum import StrEnum
from datetime import datetime
from sqlalchemy.orm.session import Session
from python_accounting.config import config
from python_accounting.models import Account


class FinancialStatement:
    """This class is an abstract representation of a Financial Statement as defined by IFRS and GAAP"""
    
    # printing
    printout: tuple
    width: str
    indent: str = " " * config.reports["indent_length"]
    subtotal: str = "_" * config.reports["result_length"]
    grandtotal: str = "=" * config.reports["result_length"]

    def __init__(self, session: Session) -> None:
        self.session = session
        self.title = config.reports[self.config]["title"]

        # Financial Statement Sections
        self.sections = StrEnum(
            "Sections",
            {k: v["label"] for k, v in config.reports[self.config]["sections"].items()},
        )

        # Financial Statement Results
        self.results = StrEnum(
            "Results",
            {k: v for k, v in config.reports[self.config]["results"].items()},
        )

        self.section_names = [section.name for section in self.sections]
        self.accounts = {k: {} for k in self.section_names}
        self.balances = {k: {} for k in self.section_names}
        self.totals = {k: 0 for k in self.section_names}
        self.result_amounts = {}

        self.balances.update({"debit": 0, "credit": 0})
        

    def __str__(self) -> str:
        template = "{}\n" * len(self.printout)
        return template.format(*self.printout)

    def _get_sections(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
        full_balance: bool = True,
    ) -> None:
        """Get the balances of the accounts in the financial statement, aggregated by section"""

        for section, content in config.reports[self.config]["sections"].items():
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
            if hasattr(self, "start_date")
            else f"As at {self.end_date.strftime(config.dates["long"])}"
        )
        self.width = max(len(period), 45)
        return "\n{}\n{}\n{}".format(
            self.session.entity.name.center(self.width), 
            self.title.center(self.width), 
            period.center(self.width)
        )
    
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
            f"{self.result_amounts[result.name]:>{self.width - len(result)}}", 
            f"{self.grandtotal:>{self.width}}" if grandtotal else ""
        )
    

    def _print_total(self, section, factor = 1, grandtotal = False) -> str:
        """Print the total of a section of the statement"""
        label = f"Total {section.value}"
        return "{}\n{}{}\n{}".format(
            f"{self.subtotal:>{self.width}}", 
            label, 
            f"{self.totals[section.name] * factor:>{self.width - len(label)}}", 
            f"{self.grandtotal:>{self.width}}" if grandtotal else ""
        )
