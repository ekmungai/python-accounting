# models/entity.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents the person, real or artifial engaging in financial Transactions.

"""
from typing import List
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, ForeignKey
from src.models import Recyclable, ReportingPeriod


class Entity(Recyclable):
    """
    Represents the Reporting Entity.

    Attributes:
        id (int): The primary key of the Entity database record.
        name (str): The Name of the Entity.
        multi_currency (:obj:`bool`, optional): Determines if the Entity can
            have Transactions in currencies other than its base Currency.
            Defaults to False.
        mid_year_balances (:obj:`bool`, optional): Determines if the Entity
            can have Opening Balances withing the current Reporting Period.
            Defaults to False.
        year_start (:obj:`int`, optional): The month at which the Entity's Reporting
            Periods begin, expressed as a number between 1 and 12. Defaults to 1
            (January).
        locale (str): The language format to be used to represent amounts. Defaults
            to en_GB.
        currency_id (:obj:`int`, optional): The id of the Reporting Currency of
            the Entity.
        reporting_period_id (:obj:`int`, optional): The current Reporting Period
            of the Entity.

    """

    __mapper_args__ = {"polymorphic_identity": "Entity"}

    id: Mapped[int] = mapped_column(ForeignKey("recyclable.id"), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    multi_currency: Mapped[bool] = mapped_column(Boolean, default=False)
    mid_year_balances: Mapped[bool] = mapped_column(Boolean, default=False)
    year_start: Mapped[int] = mapped_column(default=1)
    locale: Mapped[str] = mapped_column(String(5), default="en_GB")
    currency_id: Mapped[int] = mapped_column(ForeignKey("currency.id"), nullable=True)
    reporting_period_id: Mapped[int] = mapped_column(
        ForeignKey("reporting_period.id"), nullable=True
    )

    # relationships
    currency: Mapped["Currency"] = relationship(foreign_keys=[currency_id])
    reporting_period: Mapped["ReportingPeriod"] = relationship(
        foreign_keys=[reporting_period_id]
    )
    users: Mapped[List["User"]] = relationship(back_populates="entity")

    def __repr__(self) -> str:
        return self.name
