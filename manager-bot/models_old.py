import datetime

import sqlalchemy as sa
from sqlalchemy.orm import mapped_column, Mapped

from base import Model


class Currency(Model):
    __tablename__ = "currency"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True,
                                    autoincrement=True)
    name: Mapped[str] = mapped_column(sa.String(20))
    symbol: Mapped[str] = mapped_column(sa.String(3))
    exchange_rate: Mapped[float] = mapped_column(
        sa.Float)  # this currency to euro

    def convert_from_eur(self, amount: float | int) -> float:
        return round(amount / self.exchange_rate, 2)

    def convert_to_eur(self, amount: float | int) -> float:
        return round(amount * self.exchange_rate, 2)


class User(Model):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(sa.String, nullable=True)
    balance: Mapped[float] = mapped_column(
        sa.Float, nullable=False, default=0
    )  # in euro
    misha_balance: Mapped[float] = mapped_column(
        sa.Float, nullable=False, default=0
    )  # in euro
    currency: Mapped[int] = mapped_column(sa.Integer,
                                          sa.ForeignKey("currency.id"))
    is_admin: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime, default=datetime.datetime.now
    )
    in_work: Mapped[bool] = mapped_column(sa.Boolean, default=True)
    active: Mapped[bool] = mapped_column(sa.Boolean, default=True)

    async def get_currency(self) -> Currency:
        return await Currency.get(id=self.currency)

    async def get_salary(self) -> "Salary":
        return await Salary.get(user=self.id)

    async def get_bet20_salary(self) -> "Bet20Salary":
        return await Bet20Salary.get(user=self.id)

    async def get_charity(self) -> "Charity":
        return await Charity.get(user=self.id)

    async def currency_balance(self) -> float | int:
        currency = await self.get_currency()
        return currency.convert_to_eur(self.balance)

    async def currency_misha_balance(self) -> float | int:
        currency = await self.get_currency()
        return currency.convert_to_eur(self.misha_balance)


class Report(Model):
    __tablename__ = "report"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True,
                                    autoincrement=True)
    user: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey("user.id"))
    partner: Mapped[int] = mapped_column(sa.Integer,
                                         sa.ForeignKey("partner.id"))
    photo: Mapped[str] = mapped_column(sa.String, nullable=True, default=None)
    amount: Mapped[float] = mapped_column(sa.Float, default=0)
    refund_amount: Mapped[float] = mapped_column(sa.Float, default=0)
    salary_percent: Mapped[int] = mapped_column(sa.Integer)
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime, default=datetime.datetime.now
    )
    erroneous: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    active: Mapped[bool] = mapped_column(sa.Boolean, default=True)

    async def get_partner(self) -> "Partner":
        return await Partner.get(id=self.partner)

    async def get_user(self) -> "User":
        return await User.get(id=self.user)

    def profit(self) -> float | int:
        return self.refund_amount - self.amount


class Partner(Model):
    __tablename__ = "partner"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True,
                                    autoincrement=True)
    name: Mapped[str] = mapped_column(sa.String)
    active: Mapped[bool] = mapped_column(sa.Boolean, default=True)


class Salary(Model):
    __tablename__ = "salary"

    user: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("user.id"), primary_key=True
    )
    amount: Mapped[float] = mapped_column(sa.Float, default=0)
    total_amount: Mapped[float] = mapped_column(sa.Float, default=0)
    last_debiting_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime, nullable=True, default=None
    )


class Bet20Salary(Model):
    __tablename__ = "bet20_salary"

    user: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("user.id"), primary_key=True
    )
    amount: Mapped[float] = mapped_column(sa.Float, default=0)
    total_amount: Mapped[float] = mapped_column(sa.Float, default=0)
    last_debiting_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime, nullable=True, default=None
    )


class Operation(Model):
    __tablename__ = "operation"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True,
                                    autoincrement=True)
    user: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey("user.id"))
    amount: Mapped[float] = mapped_column(sa.Float)
    reason: Mapped[str] = mapped_column(sa.Text)
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime, default=datetime.datetime.now()
    )


class Charity(Model):
    __tablename__ = "charity"

    user: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("user.id"), primary_key=True
    )
    amount: Mapped[float] = mapped_column(sa.Float, default=0)
    total_amount: Mapped[float] = mapped_column(sa.Float, default=0)
    last_debiting_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime, nullable=True, default=None
    )


class WorkInterval(Model):
    __tablename__ = "work_interval"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True,
                                    autoincrement=True)
    start_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime, default=datetime.datetime.now()
    )
    end_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime, default=None, nullable=True
    )
    user: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("user.id"), primary_key=True
    )
