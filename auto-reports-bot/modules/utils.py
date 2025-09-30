import openpyxl as xl
import shutil
import os
from datetime import datetime as dt
from sqlalchemy import and_

from modules.parser import ReportParsed
from modules.models import Report, ReportEmployee, Source
from modules.logs import error
from config import execute


def esc_md(text: str):
	escape_chars = r'_*[]()~`>#+-=|{}.!'
	return ''.join(f'\\{char}' if char in escape_chars else char for char in str(text))


async def add_report_to_db(parsed: ReportParsed):
	date = dt.strptime(parsed.date, "%d.%m.%Y %H:%M:%S")

	report = await Report.create(
		date=date,
		date_str=date.strftime("%d.%m.%Y"),
		status=parsed.status,
		is_error=parsed.is_error,
		is_over=parsed.is_over,
		is_express=parsed.is_express,
		nickname=parsed.nickname,
		source_id=parsed.source.id,
		country_id=parsed.country.id,
		bookmaker_id=parsed.bookmaker.id,
		match_id=parsed.match_.id if parsed.match_ else '',
		bet_amount=parsed.stake,
		return_amount=parsed.return_amount,  # Используем реальный возврат согласно ТЗ
		coefficient=parsed.coefficient,
		_salary_percentage=(5 if parsed.is_express else None)
	)

	for employee in parsed.employees:
		await ReportEmployee.create(
			report_id=report.id,
			employee_id=employee.id
		)

	execute(f"INSERT INTO reports VALUES('{parsed.msg_id}', {report.id})")


async def edit_report(parsed: ReportParsed):
	report_id = execute(f"SELECT report_id FROM reports WHERE msg_id='{parsed.msg_id}'")
	report = await Report.get(id=report_id)
	date = dt.strptime(parsed.date, "%d.%m.%Y %H:%M:%S")

	if report.is_employee_checked:
		return

	await report.update(
		date=date,
		date_str=date.strftime("%d.%m.%Y"),
		status=parsed.status,
		is_error=parsed.is_error,
		is_over=parsed.is_over,
		is_express=parsed.is_express,
		nickname=parsed.nickname,
		source_id=parsed.source.id,
		country_id=parsed.country.id,
		bookmaker_id=parsed.bookmaker.id,
		match_id=parsed.match_.id if parsed.match_ else report.match_id,
		bet_amount=parsed.stake,
		return_amount=parsed.return_amount,  # Используем реальный возврат согласно Тз
		coefficient=parsed.coefficient,
		_salary_percentage=(5 if parsed.is_express else None)
	)

	for employee in report.employees:
		rep_empl = await ReportEmployee.get(
			report_id=report.id,
			employee_id=employee.id
		)
		await rep_empl.delete()

	for employee in parsed.employees:
		await ReportEmployee.create(
			report_id=report.id,
			employee_id=employee.id
		)


async def delete_report(parsed: ReportParsed):
	report_id = execute(f"SELECT report_id FROM reports WHERE msg_id='{parsed.msg_id}'")
	if not report_id:
		return
	
	report = await Report.get(id=report_id)
	if not report:
		return

	# Позволяем удаление только если отчет еще не подтвержден сотрудником
	if report.is_employee_checked:
		return

	# Помечаем отчет как удаленный в основной БД
	await report.update(is_deleted=True, deleted_at=dt.utcnow())
	# Удаляем связь msg_id -> report_id из локальной таблицы
	execute(f"DELETE FROM reports WHERE msg_id='{parsed.msg_id}'")


async def exist_source(chat_id: int) -> bool:
	return await Source.get(chat_id=chat_id) is not None


async def exist_report(msg_id: str) -> bool:
	report_id = execute(f"SELECT report_id FROM reports WHERE msg_id='{msg_id}'")
	return await Report.get(id=report_id) is not None


async def gather_tables(filters_list):
	shutil.copyfile(
		os.path.realpath("tables/clean/main_table.xlsx"), "tables/main_table.xlsx"
	)
	shutil.copyfile(
		os.path.realpath("tables/clean/bot_table.xlsx"), "tables/bot_table.xlsx"
	)

	main_table = xl.load_workbook("tables/main_table.xlsx")
	bot_table = xl.load_workbook("tables/bot_table.xlsx")

	mpage = main_table.active
	bpage = bot_table.active

	filters = {
		f.split('=')[0]: f.split('=')[1]
		for f in filters_list
		if '=' in f
	}

	# gather main table
	mrow, brow = 2, 2

	filtered_reports = []
	if filters_list[0] == 'all':
		filtered_reports = await Report.all()

	else:
		if filters.get('from') and filters.get('to'):
			from_date = dt.strptime(filters['from'], "%d.%m.%Y")
			to_date = dt.strptime(filters['to'], "%d.%m.%Y")
			filtered_reports = await Report.filter(and_(
				Report.date >= from_date,
				Report.date <= to_date
			))
		elif filters.get("date"):
			filtered_reports = await Report.filter(Report.date_str == filters['date'])
		else:
			filtered_reports = await Report.filter_by(**filters)

	for report in filtered_reports:
		temp_rows = [mrow, brow]
		try:
			mpage[f'A{mrow}'].value = report.date.strftime("%d.%m.%Y %H:%M:%S")
			mpage[f'B{mrow}'].value = report.status
			mpage[f'C{mrow}'].value = report.source.name
			mpage[f'D{mrow}'].value = report.country.name
			mpage[f'E{mrow}'].value = report.bookmaker.bk_name
			mpage[f'F{mrow}'].value = report.bookmaker.name
			mpage[f'G{mrow}'].value = report.match.name if report.match else ''
			mpage[f'H{mrow}'].value = len(report.employees)
			mpage[f'I{mrow}'].value = report.coefficient
			mpage[f'J{mrow}'].value = report.employees[0].second_name
			mpage[f'K{mrow}'].value = "{:.2f}".format(report.bet_amount)
			mpage[f'L{mrow}'].value = "{:.2f}".format(float(report.profit))
			mpage[f'M{mrow}'].value = "{:.2f}".format(report.return_amount)
			mpage[f'N{mrow}'].value = ('Да' if report.is_error else 'Нет')
			mpage[f'O{mrow}'].value = ('Да' if report.is_over else 'Нет')
			mpage[f'P{mrow}'].value = ('Да' if report.is_express else 'Нет')

			mrow += 1

			if report.status == 'Обычный':
				bpage[f'A{brow}'].value = report.date.strftime("%d.%m.%Y %H:%M:%S")
				bpage[f'B{brow}'].value = report.source.name
				bpage[f'C{brow}'].value = report.country.name
				bpage[f'D{brow}'].value = report.bookmaker.bk_name
				bpage[f'E{brow}'].value = report.bookmaker.name
				bpage[f'F{brow}'].value = report.match.name if report.match else ''
				bpage[f'G{brow}'].value = report.employees[0].username
				bpage[f'H{brow}'].value = report.bet_amount
				bpage[f'I{brow}'].value = report.return_amount
				bpage[f'J{brow}'].value = ('Да' if report.is_error else 'Нет')
				bpage[f'K{brow}'].value = report.employees[0].id
				bpage[f'L{brow}'].value = ('Да' if report.is_express else 'Нет')

				brow += 1

			if report.status == "Основной":
				for employee in report.employees:
					mpage[f'A{mrow}'].value = report.date.strftime("%d.%m.%Y %H:%M:%S")
					mpage[f'B{mrow}'].value = "Подотчет"
					mpage[f'C{mrow}'].value = report.source.name
					mpage[f'D{mrow}'].value = report.country.name
					mpage[f'E{mrow}'].value = report.bookmaker.bk_name
					mpage[f'F{mrow}'].value = report.bookmaker.name
					mpage[f'G{mrow}'].value = report.match.name if report.match else ''
					mpage[f'H{mrow}'].value = 1
					mpage[f'I{mrow}'].value = report.coefficient
					mpage[f'J{mrow}'].value = employee.second_name
					mpage[f'K{mrow}'].value = "{:.2f}".format(report.bet_amount / len(report.employees))
					mpage[f'L{mrow}'].value = "{:.2f}".format(report.profit / len(report.employees))
					mpage[f'M{mrow}'].value = "{:.2f}".format(report.return_amount / len(report.employees))
					mpage[f'N{mrow}'].value = ('Да' if report.is_error else 'Нет')
					mpage[f'O{mrow}'].value = ('Да' if report.is_over else 'Нет')
					mpage[f'P{mrow}'].value = ('Да' if report.is_express else 'Нет')

					bpage[f'A{brow}'].value = report.date.strftime("%d.%m.%Y %H:%M:%S")
					bpage[f'B{brow}'].value = report.source.name
					bpage[f'C{brow}'].value = report.country.name
					bpage[f'D{brow}'].value = report.bookmaker.bk_name
					bpage[f'E{brow}'].value = report.bookmaker.name
					bpage[f'F{brow}'].value = report.match.name if report.match else ''
					bpage[f'G{brow}'].value = employee.username
					bpage[f'H{brow}'].value = "{:.2f}".format(report.bet_amount / len(report.employees))
					bpage[f'I{brow}'].value = "{:.2f}".format(report.return_amount / len(report.employees))
					bpage[f'J{brow}'].value = ('Да' if report.is_error else 'Нет')
					bpage[f'K{brow}'].value = employee.id
					bpage[f'L{brow}'].value = ('Да' if report.is_express else 'Нет')

					mrow += 1
					brow += 1

		except Exception as e:
			mrow, brow = temp_rows
			await error(report, e)
			continue

	main_table.save("tables/main_table.xlsx")
	bot_table.save("tables/bot_table.xlsx")
