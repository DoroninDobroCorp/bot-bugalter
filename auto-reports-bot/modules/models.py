from sqlalchemy import (Column, Integer, String, Float, ForeignKey, DateTime,
						Boolean, select)
from sqlalchemy.orm import relationship, selectinload
from sqlalchemy.ext.hybrid import hybrid_property
import datetime

from modules.init_db import async_session
from modules.base import Model


class Country(Model):
	__tablename__ = "country"
	id = Column(Integer, primary_key=True)
	name = Column(String)
	commission = Column(Float, default=0)
	flag = Column(String)
	is_deleted = Column(Boolean, default=False, index=True)

	transactions = relationship('Transaction', back_populates='country')
	bookmakers = relationship('Bookmaker', back_populates='country', lazy='selectin')
	wallets = relationship('Wallet', back_populates='country', lazy='selectin')
	reports = relationship('Report', back_populates='country')
	templates = relationship('Template', back_populates='country')

	def get_active_balance(self):
		bookmakers_balance = 0
		for bookmaker in self.bookmakers:
			if not bookmaker.is_deleted:
				bookmakers_balance += bookmaker.get_balance()
		wallets_balance = 0
		for wallet in self.wallets:
			if not wallet.is_deleted:
				wallets_balance += wallet.get_balance()
		return bookmakers_balance + wallets_balance

	def get_balance(self):
		"""Returns balance of active bookmakers (deposit + reports) + wallets for this country."""
		bookmakers_balance = 0
		for bookmaker in self.bookmakers:
			if bookmaker.is_active and not bookmaker.is_deleted:
				bookmakers_balance += bookmaker.get_balance()
		wallets_balance = 0
		for wallet in self.wallets:
			if not wallet.is_deleted:
				wallets_balance += wallet.get_balance()
		return bookmakers_balance + wallets_balance


class Bookmaker(Model):
	__tablename__ = "bookmaker"
	id = Column(Integer, primary_key=True)
	name = Column(String)
	bk_name = Column(String)
	salary_percentage = Column(Float)
	
	country_id = Column(Integer, ForeignKey('country.id'), index=True)
	template_id = Column(Integer, ForeignKey('template.id'), index=True)
	
	is_active = Column(Boolean, default=True, index=True)
	deactivated_at = Column(DateTime)
	is_deleted = Column(Boolean, default=False, index=True)

	country = relationship('Country', back_populates='bookmakers', lazy='selectin')
	template = relationship('Template', back_populates='bookmakers', lazy='selectin')

	transactions_sender = relationship('Transaction', back_populates='sender_bookmaker', foreign_keys='Transaction.sender_bookmaker_id', lazy='selectin')
	transactions_receiver = relationship('Transaction', back_populates='receiver_bookmaker', foreign_keys='Transaction.receiver_bookmaker_id', lazy='selectin')
	reports = relationship('Report', back_populates='bookmaker', lazy='selectin')

	def get_deposit(self):
		transactions_balance = 0
		for transaction in [t for t in self.transactions_sender if
							t.from_ == "deposit"]:
			transactions_balance -= transaction.amount
		for transaction in [t for t in self.transactions_receiver if
							t.where == "deposit"]:
			transactions_balance += transaction.real_amount
		return transactions_balance

	def get_balance(self):
		reports_balance = 0
		for report in self.reports:
			if not report.is_deleted and report.is_admin_checked:
				reports_balance += report.real_profit
		transactions_balance = 0
		for transaction in [t for t in self.transactions_sender if
							t.from_ == "balance"]:
			transactions_balance -= transaction.amount
		for transaction in [t for t in self.transactions_receiver if
							t.where == "balance"]:
			transactions_balance += transaction.real_amount
		return self.get_deposit() + reports_balance + transactions_balance


class Wallet(Model):
	__tablename__ = "wallet"
	id = Column(Integer, primary_key=True)
	name = Column(String)
	general_wallet_type = Column(String)
	wallet_type = Column(String)
	deposit = Column(Float)
	adjustment = Column(Float, default=0)
	
	country_id = Column(Integer, ForeignKey('country.id'), index=True)
	is_deleted = Column(Boolean, default=False, index=True)

	country = relationship('Country', back_populates='wallets', lazy='selectin')
	transactions_sender = relationship('Transaction', back_populates='sender_wallet', foreign_keys='Transaction.sender_wallet_id', lazy='selectin')
	transactions_receiver = relationship('Transaction', back_populates='receiver_wallet', foreign_keys='Transaction.receiver_wallet_id', lazy='selectin')

	def get_balance(self):
		sender_transactions = sum(transaction.amount for transaction in
								  self.transactions_sender)
		receiver_transactions = sum(transaction.real_amount for transaction in
									self.transactions_receiver)
		return self.deposit + receiver_transactions - sender_transactions + self.adjustment


class Transaction(Model):
	__tablename__ = "transaction"
	id = Column(Integer, primary_key=True)
	from_ = Column(String)
	where = Column(String)
	amount = Column(Float)
	commission = Column(Float, default=0)
	transaction_type = Column(String)
	timestamp = Column(DateTime)

	sender_wallet_id = Column(Integer, ForeignKey('wallet.id'), index=True)
	sender_bookmaker_id = Column(Integer, ForeignKey('bookmaker.id'), index=True)
	receiver_wallet_id = Column(Integer, ForeignKey('wallet.id'), index=True)
	receiver_bookmaker_id = Column(Integer, ForeignKey('bookmaker.id'), index=True)
	country_id = Column(Integer, ForeignKey('country.id'), index=True)
	
	is_deleted = Column(Boolean, default=False)

	sender_wallet = relationship('Wallet', foreign_keys=[sender_wallet_id], back_populates='transactions_sender')
	sender_bookmaker = relationship('Bookmaker', foreign_keys=[sender_bookmaker_id], back_populates='transactions_sender')
	receiver_wallet = relationship('Wallet', foreign_keys=[receiver_wallet_id], back_populates='transactions_receiver')
	receiver_bookmaker = relationship('Bookmaker', foreign_keys=[receiver_bookmaker_id], back_populates='transactions_receiver')
	country = relationship('Country', back_populates='transactions', lazy='joined')

	@property
	def real_amount(self):
		return self.amount - (self.commission or 0)


class Employee(Model):
	__tablename__ = "employee"
	id = Column(Integer, primary_key=True)
	name = Column(String)
	second_name = Column(String, index=True)
	username = Column(String)
	adjustment = Column(Float, default=0)
	token = Column(String, index=True)

	reports = relationship('Report', secondary='report_employee', back_populates='employees')

	async def salary(self, reports_employee=None):
		salary_sum = 0

		if not reports_employee:
			reports_employee = await ReportEmployee.filter_by(employee_id=self.id)

		for report_employee in reports_employee:
			report = await Report.get(id=report_employee.report_id, is_error=False, is_deleted=False)
			if report:
				emp_count = len(report.employees) if report.employees else 1
				salary_sum += (report.salary / emp_count)

		return salary_sum

	async def penalty(self, reports_employee=None):
		penalty_sum = 0

		if not reports_employee:
			reports_employee = await ReportEmployee.filter_by(employee_id=self.id)

		for report_employee in reports_employee:
			report = await Report.get(id=report_employee.report_id, is_deleted=False)
			if not report:
				continue
			# Штраф целиком первому сотруднику при ошибочном отчёте с убытком
			if report.is_error and report.profit < 0:
				if report.employees and report.employees[0].id == self.id:
					penalty_sum += report.penalty

		return penalty_sum

	async def get_balance(self):
		async with async_session() as session:
			stmt = (
				select(Report)
				.join(ReportEmployee, ReportEmployee.report_id == Report.id)
				.where(ReportEmployee.employee_id == self.id)
				.where(Report.is_deleted == False)
				.where(Report.is_admin_checked == True)
				.options(
					selectinload(Report.employees),
					selectinload(Report.bookmaker)
				)
			)
			result = await session.execute(stmt)
			reports = result.unique().scalars().all()

			# Зарплату делим поровну, штраф НЕ делим — целиком первому сотруднику
			salary_sum = 0.0
			penalty_sum = 0.0
			for report in reports:
				emp_count = len(report.employees) if report.employees else 1
				if not report.is_error:
					salary_sum += (report.salary / emp_count)
				if report.is_error and report.profit < 0:
					if report.employees and report.employees[0].id == self.id:
						penalty_sum += report.penalty

			return self.adjustment + salary_sum - penalty_sum


class Report(Model):
	__tablename__ = "report"
	id = Column(Integer, primary_key=True)
	date = Column(DateTime, index=True)
	date_str = Column(String)
	msg_id = Column(String)
	status = Column(String)
	source_id = Column(Integer, ForeignKey('source.id'), index=True)
	country_id = Column(Integer, ForeignKey('country.id'), index=True)
	bookmaker_id = Column(Integer, ForeignKey('bookmaker.id'), index=True)
	match_id = Column(String, ForeignKey('match.id'), index=True)

	nickname = Column(String)
	bet_amount = Column(Float)
	return_amount = Column(Float)
	coefficient = Column(Float)
	_salary_percentage = Column(Float)

	is_employee_checked = Column(Boolean, default=False, index=True)
	is_admin_checked = Column(Boolean, default=False, index=True)
	is_error = Column(Boolean, default=False, index=True)
	is_over = Column(Boolean, default=False)
	is_express = Column(Boolean, default=False)
	is_deleted = Column(Boolean, default=False, index=True)
	deleted_at = Column(DateTime, index=True)

	source = relationship('Source', back_populates='reports', lazy='selectin')
	country = relationship('Country', back_populates='reports', lazy='selectin')
	bookmaker = relationship('Bookmaker', back_populates='reports', lazy='selectin')
	match = relationship('Match', back_populates='reports', lazy='selectin')
	
	employees = relationship('Employee', secondary='report_employee', back_populates='reports', lazy='selectin')

	@property
	def canonical_match(self):
		return self.match.canonical_match if self.match and self.match.canonical_id else self.match

	@hybrid_property
	def salary_percentage(self):
		if self._salary_percentage is not None: return self._salary_percentage
		if self.bookmaker is not None: return self.bookmaker.salary_percentage
		return 0

	@salary_percentage.setter
	def salary_percentage(self, value):
		self._salary_percentage = value

	@property
	def profit(self):
		return (self.return_amount or 0) - (self.bet_amount or 0)

	@property
	def salary(self):
		return 0 if self.is_error else (self.bet_amount * self.salary_percentage / 100)

	@property
	def penalty(self):
		if self.is_error and self.profit < 0:
			return abs(self.profit) * 3 * self.salary_percentage / 100
		return 0

	@property
	def real_profit(self):
		return self.profit

	@property
	def real_salary(self):
		return self.salary - self.penalty


class Source(Model):
	__tablename__ = "source"
	id = Column(Integer, primary_key=True)
	chat_id = Column(Integer, default=0)
	name = Column(String)
	is_deleted = Column(Boolean, default=False, index=True)
	reports = relationship('Report', back_populates='source')


class Admin(Model):
	__tablename__ = "admin"
	id = Column(Integer, primary_key=True)
	employee_id = Column(Integer, ForeignKey('employee.id'), index=True, unique=True)
	employee = relationship('Employee', backref='admins_employee')


class Template(Model):
	__tablename__ = "template"
	id = Column(Integer, primary_key=True)
	name = Column(String)
	employee_percentage = Column(Float)
	country_id = Column(Integer, ForeignKey('country.id'), index=True)
	is_deleted = Column(Boolean, default=False, index=True)
	
	country = relationship('Country', back_populates='templates')
	bookmakers = relationship('Bookmaker', back_populates='template')


class Match(Model):
	__tablename__ = "match"
	id = Column(String, primary_key=True)
	name = Column(String)
	is_active = Column(Boolean, index=True)
	canonical_id = Column(String, ForeignKey('match.id'), index=True)

	canonical_match = relationship('Match', remote_side=[id], back_populates='children_matches')
	children_matches = relationship('Match', back_populates='canonical_match')
	reports = relationship('Report', back_populates='match')


class ReportEmployee(Model):
	__tablename__ = "report_employee"
	id = Column(Integer, primary_key=True)
	report_id = Column(Integer, ForeignKey('report.id'), index=True)
	employee_id = Column(Integer, ForeignKey('employee.id'), index=True)


class WaitingUser(Model):
	__tablename__ = "waiting_Users"
	id = Column(Integer, primary_key=True)
	name = Column(String)
	username = Column(String)

class OperationHistory(Model):
	__tablename__ = "operation_history"
	id = Column(Integer, primary_key=True)
	date = Column(DateTime, default=datetime.datetime.utcnow)
	user_name = Column(String)
	operation_type = Column(String)
	operation_description = Column(String)

class CommissionHistory(Model):
	__tablename__ = "commission_history"
	id = Column(Integer, primary_key=True)
	date = Column(DateTime, default=datetime.datetime.utcnow)
	user_name = Column(String)
	commission = Column(Float)
	commission_type = Column(String)
	commission_description = Column(String)
