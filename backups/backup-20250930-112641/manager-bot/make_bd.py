from sqlalchemy import create_engine
from data.models import *
from sqlalchemy.orm import sessionmaker
import sqlite3 as sql

import random as rd
from string import ascii_letters, digits
from datetime import datetime as dt

to_engine = create_engine("sqlite:///../main.db")
Model.metadata.create_all(to_engine)
to_session = sessionmaker(bind=to_engine)()

from_db = sql.connect("test_transfer.db").cursor().execute

countries_transfer = [
	"Бельгия", "Бразилия", "Испания", "Россия", "Словакия", "Турция", "Украина"
]

wallets_transfer = [
	("Егор", "Страна", 1), ("Эзель", "Страна", 1),
	("Соня", "Страна", 13),
	("Энди", "Страна", 5),
	("Основной", "Общий", None), ("Андрей", "Общий", None), ("Аня", "Общий", None),
	("Богдан", "Страна", 4), ("Лискас", "Страна", 4), ("Дима Дима", "Страна", 4), ("Витя", "Страна", 4),
	("Вова", "Страна", 2), ("Валера", "Страна", 17)
]

bookmakers_transfer = [
	("Starcasino", "Ez5", 1), ("Unibet", "Be26", 1), ("Bingoal", "Lz5", 1), ("Starcasino", "Lz5", 1), ("Scooore", "Ez5", 1), ("Unibet", "Ve9", 1),
	("Betnacional", "Br7", 13), ("Rivalo", "Br8", 13),
	("Apuestademurcia", "Es2", 5), ("Kirolbet", "Es7", 5), ("Retabet", "Es8", 5), ("Speedybet", "Es10", 5), ("888sport", "Es9", 5),
	("Codere", "Es11", 5), ("Interwetten", "Es14", 5), ("Goldenbull", "Es13", 5), ("Luckia", "Es12", 5), ("Williamhill", "Es16", 5),
	("Fonbet", "Ru15", 4),
	("Nike", "Sl34", 2), ("Nike", "Sl35", 2),
	("1xbet", "Tk42", 23), ("Hepsibahis", "Tk45", 23), ("Iddaa", "Tk44", 23), ("Sekabet", "Tk49", 23), ("Artemisbet", "Tk48", 23),
	("Artemisbet", "Tk55", 23), ("Betboo", "Tk52", 23),  ("Superbahis", "Tk51", 23), ("Bets10", "Tk54", 23), ("Hepsibahis", "Tk50", 23),
	("Betfair", "Ua1", 17),
]

# ADMINS
for admin in from_db("SELECT * FROM admin").fetchall():
	new_admin = Admin(
		id=admin[0],
		employee_id=admin[1]
	)
	to_session.add(new_admin)

to_session.commit()

# BOOKMAKERS
for bookmaker in from_db("SELECT * FROM bookmaker").fetchall():
		if (bookmaker[7], bookmaker[1], bookmaker[2]) in bookmakers_transfer and bookmaker[4]:
			new_bookmaker = Bookmaker(
				id=bookmaker[0],
				name=bookmaker[1],
				country_id=bookmaker[2],
				salary_percentage=bookmaker[3],
				is_active=bookmaker[4],
				deactivated_at=dt.strptime(bookmaker[5], "%Y-%m-%d %H:%M:%S.%f") if bookmaker[5] else None,
				template_id=bookmaker[6],
				bk_name=bookmaker[7],
				is_deleted=bookmaker[8]
		)
			to_session.add(new_bookmaker)

to_session.commit()

# COMMISSIONS HISTORY
for commission_history in from_db("SELECT * FROM commission_history").fetchall():
	new_commission_history = CommissionHistory(
		id=commission_history[0],
		date=dt.strptime(commission_history[1], "%Y-%m-%d %H:%M:%S.%f"),
		user_name=commission_history[2],
		commission=commission_history[3],
		commission_type=commission_history[4],
		commission_description=commission_history[5]
	)
	to_session.add(new_commission_history)

to_session.commit()

# COUNTRIES
for country in from_db("SELECT * FROM country").fetchall():
	if country[1] in countries_transfer:
		new_country = Country(
			id=country[0],
			name=country[1],
			commission=country[2],
			flag=country[3],
			is_deleted=country[4]
		)
		to_session.add(new_country)

to_session.commit()

# EMPLOYEES
empls = {}
for employee in from_db("SELECT * FROM employee").fetchall():
	empls[employee[0]] = employee[3]

	new_employee = Employee(
		id=employee[0],
		name=employee[1],
		adjustment=employee[2], # employee[2]
		username=employee[3]
	)
	to_session.add(new_employee)

to_session.commit()

# OPERATIONS HISTORY
for operation_history in from_db("SELECT * FROM operation_history").fetchall():
	new_operation_history = OperationHistory(
		id=operation_history[0],
		date=dt.strptime(operation_history[1], "%Y-%m-%d %H:%M:%S.%f"),
		user_name=operation_history[2],
		operation_type=operation_history[3],
		operation_description=operation_history[4]
	)
	to_session.add(new_operation_history)

to_session.commit()

# SOURCES
for source in from_db("SELECT * FROM source").fetchall():
	new_source = Source(
		id=source[0],
		chat_id=0,
		name=source[1],
		is_deleted=source[2]
	)
	to_session.add(new_source)

to_session.commit()

# TEMPLATES
for template in from_db("SELECT * FROM template").fetchall():
	new_template = Template(
		id=template[0],
		name=template[1],
		country_id=template[2],
		employee_percentage=template[3],
		is_deleted=template[4]
	)
	to_session.add(new_template)

to_session.commit()

# TRANSACTIONS
for transaction in from_db("SELECT * FROM 'transaction'").fetchall():
	new_transaction = Transaction(
		id=transaction[0],
		from_=transaction[1],
		where=transaction[2],
		amount=transaction[3],
		commission=transaction[4],
		sender_wallet_id=transaction[5],
		sender_bookmaker_id=transaction[6],
		receiver_wallet_id=transaction[7],
		receiver_bookmaker_id=transaction[8],
		country_id=transaction[9],
		transaction_type=transaction[10],
		timestamp=transaction[11],
		is_deleted=transaction[12]
	)
	to_session.add(new_transaction)

to_session.commit()

# WAITING USERS
for waiting_user in from_db("SELECT * FROM waiting_Users").fetchall():
	new_waiting_user = WaitingUser(
		id=waiting_user[0],
		name=waiting_user[1],
		username=waiting_user[2]
	)
	to_session.add(new_waiting_user)

to_session.commit()

# WALLETS
for wallet in from_db("SELECT * FROM wallet").fetchall():
	if (wallet[1], wallet[3], wallet[4]) in wallets_transfer:
		new_wallet = Wallet(
			id=wallet[0],
			name=wallet[1],
			general_wallet_type=wallet[2],
			wallet_type=wallet[3],
			country_id=wallet[4],
			deposit=wallet[5],
			adjustment=wallet[6],
			is_deleted=wallet[7]
		)
		to_session.add(new_wallet)

to_session.commit()

# MATCHES
matches = {}
for report in from_db("SELECT * FROM report").fetchall():
	match_name = report[5]
	if match_name not in list(matches.keys()):
		match_id = ''.join([
			rd.choice(ascii_letters + digits)
			for _ in range(10)
		])
		matches[match_name] = match_id

	else:
		continue

	new_match = Match(
		id=match_id,
		name=match_name,
		is_active=True
	)

	to_session.add(new_match)

to_session.commit()

# REPORTS
for report in from_db("SELECT * FROM report").fetchall():
	date = dt.strptime(report[1], "%Y-%m-%d %H:%M:%S.%f")
	new_report = Report(
		id=report[0],
		date=date,
		date_str=date.strftime("%d.%m.%Y"),
		status='Обычный',
		source_id=report[2],
		country_id=report[3],
		bookmaker_id=report[4],
		match_id=matches[report[5]],
		nickname=(empls.get(report[10]) if empls.get(report[10]) else ""),
		bet_amount=report[7],
		return_amount=report[8],
		coefficient=round(report[8]/report[7], 2),
		is_employee_checked=True,
		is_admin_checked=True,
		is_error=report[11],
		is_over=False,
		is_express=False,
		is_deleted=report[12]
	)
	to_session.add(new_report)

to_session.commit()

# REPORT EMPLOYEES
for report in from_db("SELECT * FROM report").fetchall():
	report_id = report[0]
	employee_id = report[10]

	report_empl = ReportEmployee(
		report_id=report_id,
		employee_id=employee_id
	)
	to_session.add(report_empl)

to_session.commit()
