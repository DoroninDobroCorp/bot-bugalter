import asyncio
from math import isnan
from types import NoneType

import pandas as pd
from pandas import Timestamp

from data.utils import *
import io
import openpyxl

fields_to_check = [
	'Дата', 'Источник', 'Страна', 'Букмекер',
	'Профиль', 'Сумма Проставленных', 'Возврат', 'nickName',
]
# Определение порядка полей
fields_order = [
	'№', 'Статус', 'Username', 'Дата', 'Сумма Проставленных',
	'Сумма возврата', 'Профит', 'Зарплата',
	'Источник', 'Страна', 'Букмекер',
	'Профиль', 'Название матча'
]


def check_type(obj, obj_types):
	types_isinstance = []
	for obj_type in obj_types:
		types_isinstance.append(isinstance(obj, obj_type))

	types_isinstance.append(obj is None)

	return any(types_isinstance)


async def process_excel_file(file_path: str):
	# Чтение файла Excel
	df = pd.read_excel(file_path)
	df_copy = df.copy()  # Создание копии DataFrame
	df_copy[
		'Error'] = None  # Добавление столбца 'Error' со значением по умолчанию None
	# переводим дату в datetime
	df['Дата'] = pd.to_datetime(df['Дата'], errors='coerce')
	employees = await get_employees()
	sources = await get_sources()
	countries = await get_countries()

	async def process_row(index, row):
		try:
			# Проверка, что все поля не равны None
			if not all(row.get(field) is not None for field in fields_to_check):
				# Если хотя бы одно поле равно None, находим эти поля и возвращаем
				missing_fields = [field for field in fields_to_check if
				                  row.get(field) is None or
				                  (isnan(row.get(field)) if isinstance(row.get(field), float) else False)]
				error_message = f"Не хватает полей: {', '.join(missing_fields)}"
				df_copy.at[
					index, 'Error'] = error_message  # Обновление столбца 'Error' в df_copy
				return

			# По умолчанию отчет не ошибочный (согласно ТЗ, ошибки определяются администратором позже)
			wrong_report_value = 0  # Всегда 0, так как ошибки определяются позже

			error_types_msg = "Не правильные типы для: "
			for field in fields_to_check:
				if field == 'Дата':
					if not check_type(row.get(field), [Timestamp]):
						error_types_msg += field + ", "

				elif field in ['Сумма Проставленных', 'Возврат']:
					if not check_type(row.get(field), [float, int]):
						error_types_msg += field + ", "


				else:
					if not check_type(row.get(field), [str]):
						error_types_msg += field + ", "

			if error_types_msg != "Не правильные типы для: ":
				df_copy.at[
					index, 'Error'] = error_types_msg
				return

			date = row.get('Дата')
			source = row.get('Источник')
			country = row.get('Страна')
			bk_name = row.get('Букмекер')
			bk_login = row.get('Профиль')
			placed = row.get('Сумма Проставленных')
			received = row.get('Возврат')
			nick_name = row.get('nickName')
			# Поля ниже — опциональны
			match_name = row.get('Название матча') if 'Название матча' in df.columns else None
			custom_salary_pct = row.get('Процент ЗП') if 'Процент ЗП' in df.columns else None
			
			# Определяем пользователя по никнейму
			employee = next((e for e in employees if e.second_name == nick_name), None)
			if not employee:
				df_copy.at[index, 'Error'] = f"Сотрудник с никнеймом {nick_name} не найден"
				return
			userid = employee.id

			# все приводим в str
			source = str(source)
			country = str(country)
			bk_name = str(bk_name)
			bk_login = str(bk_login)
			nick_name = str(nick_name)
			if match_name is not None:
				match_name = str(match_name)

			# Добавление строки в базу данных
			# Поддержка 'Процент ЗП' согласно ТЗ: если задан — используем, иначе берём с БК
			try:
				salary_percentage = float(custom_salary_pct) if custom_salary_pct not in (None, "",) else None
			except Exception:
				salary_percentage = None

			ans = await add_report_to_db(
				date, wrong_report_value, source,
				country, bk_name, bk_login, placed,
				received, userid, nick_name, match_name,
				employees, sources, countries, salary_percentage=salary_percentage
			)
			if ans != True:
				df_copy.at[
					index, 'Error'] = ans  # Обновление столбца 'Error' в df_copy

		except Exception as e:
			df_copy.at[index, 'Error'] = "Ошибка"

	# Создание списка задач для обработки строк
	tasks = [asyncio.create_task(process_row(index, row)) for index, row in
	         df.iterrows()]

	# Ожидание завершения всех задач
	await asyncio.gather(*tasks)

	# Фильтрация df_copy для включения только строк с ошибками
	df_errors = df_copy[df_copy['Error'].notna()]

	# Запись df_errors в файл 'errors.xlsx'
	df_errors.to_excel('errors.xlsx', index=False)

	# Возвращение True, если df_errors пуст
	return df_errors.empty


async def export_reports_to_excel(reports, start_date, end_date):
	# Создание Excel файла и заполнение данными
	workbook = openpyxl.Workbook()
	sheet = workbook.active

	# Добавление заголовков в соответствии с порядком полей
	sheet.append(fields_order)
	for report in reports:
		match_name = report.match.name if getattr(report, 'match', None) else '-'
		status_text = 'Отчет ошибочный' if report.is_error else 'Отчет не ошибочный'
		payout_value = report.penalty if (report.is_error and report.profit < 0) else report.salary
		usernames = ", ".join([e.username for e in report.employees if getattr(e, 'username', None)]) or '-'
		row_data = [
			report.id,
			status_text,
			usernames,
			report.date.strftime('%d.%m.%Y %H:%M'),
			report.bet_amount,
			report.return_amount,
			report.profit,
			payout_value,
			report.source.name,
			report.country.name,
			report.bookmaker.bk_name,
			report.bookmaker.name,
			match_name
		]
		sheet.append(row_data)

	# Сохранение файла в байт-код
	excel_file = io.BytesIO()
	workbook.save(excel_file)
	excel_file.seek(0)
	return excel_file
