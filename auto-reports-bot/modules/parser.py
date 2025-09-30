from aiogram.types import Message

from typing import List, Union, Optional
from datetime import datetime as dt

from modules.models import Bookmaker, Employee, Match, Source, Country
from modules.odt import ReportParsed


def find_date(array: List) -> Optional[str]:
	"""Ищет дату в массиве меток. Поддерживает форматы:
	- DD.MM.YY (например, 15.03.24)
	- DD.MM.YYYY (например, 15.03.2024)
	- DD.MM.YY_HH:MM:SS или DD.MM.YY HH:MM:SS (например, 15.03.24_14:30:00 или 15.03.24 14:30:00)
	- DD.MM.YYYY_HH:MM:SS или DD.MM.YYYY HH:MM:SS
	Если дата не найдена, возвращает текущее время.
	"""
	for el in array:
		if '.' in el:
			# Удаляем подчеркивания для совместимости (некоторые пишут 15.03.24_14:30:00)
			el_cleaned = el.replace('_', ' ')
			
			# Пробуем разные форматы
			formats_to_try = [
				"%d.%m.%Y %H:%M:%S",  # Полный формат с временем
				"%d.%m.%y %H:%M:%S",  # Короткий год с временем
				"%d.%m.%Y",           # Полный формат без времени
				"%d.%m.%y",           # Короткий год без времени
			]
			
			for fmt in formats_to_try:
				try:
					parsed_date = dt.strptime(el_cleaned, fmt)
					# Если формат без времени, добавляем текущее время
					if " " not in el_cleaned:
						# Берем текущее время
						now = dt.now()
						parsed_date = parsed_date.replace(hour=now.hour, minute=now.minute, second=now.second)
					return parsed_date.strftime("%d.%m.%Y %H:%M:%S")
				except ValueError:
					continue
	
	# Если ничего не найдено, возвращаем текущее время
	return dt.now().strftime("%d.%m.%Y %H:%M:%S")


def find_match(array: List) -> Optional[str]:
	for el in array:
		if el.startswith('#'):
			return el.replace('#', '')
	return None


async def parse(msg: Message) -> Union[ReportParsed, Exception]:
	try:
		lines = (msg.caption or '').split('\n')

		# line 1
		line1 = lines[0].split(maxsplit=1)
		if len(line1) == 1:
			raise Exception("В 1ой строчке недописано страну или профиль")

		# Case-insensitive country/profile
		country_list = await Country.filter(Country.name.ilike(line1[0].strip()), Country.is_deleted == False)
		country = country_list[0] if country_list else None
		profile = line1[1].strip()

		# line 2
		line2 = lines[1].replace(',', '.').split()

		# Case-insensitive bookmaker name and bk_name
		bookmaker_list = await Bookmaker.filter(
			Bookmaker.name.ilike(profile),
			Bookmaker.bk_name.ilike(line2[0].strip()),
			Bookmaker.is_deleted == False
		)
		bookmaker = bookmaker_list[0] if bookmaker_list else None
		stake = float(line2[1].strip())
		coefficient = float(line2[2].strip())
		# Опциональный возврат (line2[3]) согласно ТЗ - если не указан, рассчитывается автоматически
		return_amount = float(line2[3].strip()) if len(line2) > 3 and line2[3].strip().replace('.','').replace('-','').isdigit() else None

		# line 3
		line3 = lines[2]

		employees = []
		empls_names = [
			employee.strip()
			for employee in line3.split(',') if employee.strip() != ''
		]

		# line 4
		line4 = lines[3]

		match_id = line4.strip()
		match = await Match.get(id=match_id)
		if match:
			await match.update(is_active=True)

		# line 5 (marks)
		marks = []
		if len(lines) >= 5:
			line5 = lines[4]
			marks = [
				mark.strip()
				for mark in line5.split()
			]
			marks = [m.replace('х', 'x').lower() for m in marks]

		is_error = ('x3' in marks)
		is_over = ('x5' in marks)
		is_express = ('exp' in marks)
		delete = ('!' in marks)

		try:
			date = find_date(marks)
		except ValueError:
			raise Exception("Неверный формат времени (DD.MM.YY)")

		# check exist
		source = await Source.get(chat_id=msg.chat.id, is_deleted=False)

		if not country:
			raise Exception(f"Страна не существует")

		elif not bookmaker:
			raise Exception("БК профиль не существует")

		elif not source:
			raise Exception("Источник не существует")

		# Не валим отчёт, если match не найден: позволяем сохранить без match

		for name in empls_names:
			found = await Employee.filter(Employee.second_name.ilike(name))

			if not found:
				raise Exception(f"Сотрудника '{name}' не существует")

			employees.append(found[0])

	except IndexError:
		return Exception("Не правильный формат отчёта или это не отчёт¿")

	except Exception as e:
		return e

	# return result
	report = ReportParsed(
		msg_id=f"{msg.chat.id}:{msg.message_id}",
		date=date,
		status=("Обычный" if len(employees) == 1 else "Основной"),

		source=source,
		country=country,
		bookmaker=bookmaker,
		match_=match,

		count=len(employees),
		employees=employees,
		nickname=employees[0].username,

		stake=stake,
		coefficient=coefficient,
		# Если возврат не указан явно - рассчитываем автоматически для обратной совместимости
		return_amount=return_amount if return_amount is not None else (coefficient * stake),

		is_error=is_error,
		is_over=is_over,
		is_express=is_express,
		delete=delete
	)
	return report
