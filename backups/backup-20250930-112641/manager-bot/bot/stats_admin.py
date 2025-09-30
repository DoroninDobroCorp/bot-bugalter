from aiogram import types
from hisory_excel_logic.make_excel import *
from aiogram.dispatcher import FSMContext
from data.statistic import *
from bot.utils import *
from data.utils import *
from bot.states import StatisticsStates
from bot.keyboards import *
from datetime import datetime, timedelta
from report_logic.excel_reports import export_reports_to_excel


@admin_required
async def cancel_period_process(call: types.CallbackQuery,
								state: FSMContext):
	await call.answer()
	await call.message.answer("Введение периода отменено",
							  reply_markup=general_stats_keyboard)
	await state.finish()


@admin_required
async def show_history(message: types.Message):
	last_10_operations = await get_last_10_operations()
	if not last_10_operations:
		await message.answer("No operations")
		return
	await message.answer("\n".join(
		[
			f"{operation.operation_description} - {operation.date.strftime('%d.%m.%Y %H:%M:%S')}"
			for operation
			in last_10_operations]), reply_markup=export_history_keyboard)


@admin_required
async def show_commissions_history(message: types.Message):
	last_10_operations = await get_last_10_commissions()
	if not last_10_operations:
		await message.answer("No operations")
		return
	await message.answer("\n".join(
		[
			f"{operation.commission_description} - {operation.date.strftime('%d.%m.%Y %H:%M:%S')}"
			for
			operation
			in last_10_operations]),
		reply_markup=export_commissions_history_keyboard)


@admin_required
async def process_export_history(call: types.CallbackQuery,
								 state: FSMContext):
	await call.message.answer(
		"Введите период для истории операций в формате 'ДД.ММ.ГГГГ-ДД.ММ.ГГГГ':",
		reply_markup=cancel_period_process_keyboard
	)
	await StatisticsStates.history_excel_period.set()
	await call.answer()


@admin_required
async def process_export_commissions_history(call: types.CallbackQuery,
											 state: FSMContext):
	await call.message.answer(
		"Введите период для истории комиссий в формате 'ДД.ММ.ГГГГ-ДД.ММ.ГГГГ':",
		reply_markup=cancel_period_process_keyboard
	)
	await StatisticsStates.commissions_excel_period.set()
	await call.answer()


@admin_required
async def process_history_excel_period(message: types.Message,
									   state: FSMContext):
	try:
		period = message.text.split('-')
		start_date = datetime.strptime(period[0], '%d.%m.%Y').date()
		end_date = datetime.strptime(period[1],
									 '%d.%m.%Y').date() + timedelta(days=1)
		operations = await get_operations_by_period(start_date, end_date)

		# Вызываем функцию для создания Excel файла и получаем его байт-код и название файла
		excel_file, filename = await export_operations_to_excel(operations,
																start_date,
																end_date)

		# Создаем объект types.InputFile с указанием типа файла
		input_file = types.InputFile(excel_file, filename=filename)

		# Отправляем сгенерированный файл пользователю с указанным названием файла
		await message.answer_document(input_file)

		await add_to_history(message.from_user.username, "history",
							 f"Выгрузка истории операций в Excel пользователем {message.from_user.username}")
	except Exception as e:
		await message.answer(
			f"Ошибка при выгрузке истории операций: {e}\nЕсли хотите попробовать еще раз, нажмите на кнопку еще раз",
			reply_markup=history_stats_keyboard)
	finally:
		await state.finish()


@admin_required
async def process_commissions_excel_period(message: types.Message,
										   state: FSMContext):
	try:
		period = message.text.split('-')
		start_date = datetime.strptime(period[0], '%d.%m.%Y').date()
		end_date = datetime.strptime(period[1],
									 '%d.%m.%Y').date() + timedelta(days=1)
		commissions = await get_commissions_by_period(start_date, end_date)

		# Вызываем функцию для создания Excel файла и получаем его байт-код и название файла
		excel_file, filename = await export_commissions_to_excel(commissions,
																 start_date,
																 end_date)

		# Создаем объект types.InputFile с указанием типа файла
		input_file = types.InputFile(excel_file, filename=filename)

		# Отправляем сгенерированный файл пользователю с указанным названием файла
		await message.answer_document(input_file)

		await add_to_history(message.from_user.username, "commission",
							 f"Выгрузка истории комиссий в Excel пользователем {message.from_user.username}")
	except Exception as e:
		await message.answer(
			f"Ошибка при выгрузке истории комиссий: {e}\nЕсли хотите попробовать еще раз, нажмите на кнопку еще раз",
			reply_markup=history_stats_keyboard)
	finally:
		await state.finish()


@admin_required
async def get_report_stats(message: types.Message):
	await message.answer("Выберите действие:", reply_markup=reports_keyboard)


@admin_required
async def show_balance_stats_menu(message: types.Message):
	await message.answer("Выберите категорию статистики по балансам:",
						 reply_markup=balance_stats_keyboard)


@admin_required
async def show_statistics_menu(message: types.Message):
	await message.answer("Выберите категорию статистики:",
						 reply_markup=general_stats_keyboard)


@admin_required
async def get_total_stats(message: types.Message, state: FSMContext):
	if message.text == "Общая статистика":
		await StatisticsStates.period_input.set()
		await message.answer(
			"Введите промежуток времени для отчета в формате 'ДД.ММ.ГГГГ-ДД.ММ.ГГГГ'",
			reply_markup=cancel_period_process_keyboard
		)


@admin_required
async def process_period_input(message: types.Message, state: FSMContext):
	try:
		period = message.text.split('-')
		start_date = datetime.strptime(period[0], '%d.%m.%Y').date()
		end_date = datetime.strptime(period[1],
									 '%d.%m.%Y').date() + timedelta(days=1)
		stats = await get_total_stats_by_period(start_date, end_date)
		output = f"Общая статистика за период от {start_date} до {end_date}\n\n"
		output += f"Сумма проставленных: {stats.total_bet:.2f} EUR\n"
		output += "➖➖➖➖➖➖➖➖➖➖➖➖\n"
		output += f"Сумма профита: {stats.total_profit:.2f} EUR\n"
		output += "➖➖➖➖➖➖➖➖➖➖➖➖\n"
		output += f"Сумма накопленной зарплаты: {stats.total_salary:.2f} EUR"
		await message.answer(output)
	except Exception as e:
		await message.answer(f"Ошибка при обработке периода: {e}")
	finally:
		await state.finish()


@admin_required
async def get_balance_stats(message: types.Message):
	stats = await get_total_balances()
	if stats:
		output = await format_balance_stats(stats)
		await message.answer(output[0])
		await message.answer(output[1] + '\n\n' + output[3][0])
		for info in output[3][1:]:
			await message.answer(info)

		await message.answer(output[2])
	else:
		await message.answer("Нет данных для отображения.")


@admin_required
async def get_country_stats(message: types.Message):
	countries = await get_countries()
	if countries:
		keyboard = types.InlineKeyboardMarkup()
		for country in countries:
			keyboard.add(
				types.InlineKeyboardButton(f"{country.flag} {country.name}",
										   callback_data=f"country_stats:{country.id}"))
		await message.answer("Выберите страну:", reply_markup=keyboard)
		await StatisticsStates.country_stats.set()
	else:
		await message.answer("Нет доступных стран.")


@admin_required
async def process_country_stats(call: types.CallbackQuery, state: FSMContext):
	country_id = int(call.data.split(':')[1])
	await call.answer()
	stats = await get_country_stats_by_id(country_id)
	if stats:
		output = await format_country_stats(stats)
		await call.message.answer(output)
		keyboard = types.InlineKeyboardMarkup()
		keyboard.add(types.InlineKeyboardButton("Выбрать период",
												callback_data=f"country_period:{country_id}"))
		await call.message.answer(
			"Для просмотра статистики за определенный период нажмите кнопку ниже:",
			reply_markup=keyboard)
	else:
		await call.message.answer("Нет данных для выбранной страны.")
	await state.finish()


@admin_required
async def process_country_period_start(call: types.CallbackQuery,
									   state: FSMContext):
	country_id = int(call.data.split(':')[1])
	await call.answer()
	await state.update_data(country_id=country_id)
	await call.message.answer("Введите начальную дату (ДД.ММ.ГГГГ):",
							  reply_markup=cancel_period_process_keyboard)
	await StatisticsStates.country_start_date.set()


@admin_required
async def process_country_start_date(message: types.Message,
									 state: FSMContext):
	try:
		start_date = datetime.strptime(message.text, '%d.%m.%Y').date()
		await state.update_data(start_date=start_date)
		await message.answer("Введите конечную дату (ДД.ММ.ГГГГ):",
							 reply_markup=cancel_period_process_keyboard)
		await StatisticsStates.country_end_date.set()
	except ValueError:
		await message.answer(
			"Неверный формат даты. Введите дату в формате ДД.ММ.ГГГГ.",
			reply_markup=cancel_period_process_keyboard
		)


@admin_required
async def process_country_end_date(message: types.Message, state: FSMContext):
	try:
		end_date = datetime.strptime(message.text,
									 '%d.%m.%Y').date() + timedelta(days=1)
		data = await state.get_data()
		country_id = data['country_id']
		start_date = data['start_date']
		stats = await get_country_stats_by_period(country_id, start_date,
												  end_date)
		if stats:
			output = await format_country_stats_by_period(stats)
			await message.answer(output)
		else:
			await message.answer("Нет данных для выбранной страны и периода.")
		await state.finish()
	except ValueError:
		await message.answer(
			"Неверный формат даты. Введите дату в формате ДД.ММ.ГГГГ.",
			reply_markup=cancel_period_process_keyboard
		)


@admin_required
async def get_bks_stats_by_reports(message: types.Message):
	countries = await get_countries()
	output = []

	for i, country in enumerate(countries):
		output.append("")
		for bk in country.bookmakers:
			ind = '🔴' if any([r for r in bk.reports if not r.is_admin_checked or not r.is_employee_checked]) else '🟢'
			uncalc_balance = round(sum([r.bet_amount for r in bk.reports if not r.is_employee_checked]), 2)

			output[i] += (
					f"({ind}) {country.flag} {country.name} | "
					f"{bk.bk_name} | {bk.name} | "
					f"{round(bk.get_deposit())} ({round(bk.get_balance())} / {uncalc_balance})\n"
			)

	await message.answer("Балансы основной/нерассчитаный профилей:")
	for text in output:
		if text != '':
			await message.answer(text)

@admin_required
async def get_bookmaker_stats(message: types.Message):
	countries = await get_countries()
	if countries:
		keyboard = types.InlineKeyboardMarkup()
		for country in countries:
			keyboard.add(
				types.InlineKeyboardButton(f"{country.flag} {country.name}",
										   callback_data=f"bookmaker_country:{country.id}"))
		await message.answer("Выберите страну:", reply_markup=keyboard)
	else:
		await message.answer("Нет доступных стран.")


@admin_required
async def process_bookmaker_country(call: types.CallbackQuery):
	country_id = int(call.data.split(':')[1])
	bookmakers = await get_bookmakers_by_country(country_id)
	if bookmakers:
		keyboard = types.InlineKeyboardMarkup()
		for bookmaker in bookmakers:
			keyboard.add(types.InlineKeyboardButton(f"{bookmaker.bk_name} | {bookmaker.name}",
													callback_data=f"bookmaker_stats:{bookmaker.id}"))
		await call.message.answer("Выберите букмекера:",
								  reply_markup=keyboard)
	else:
		await call.message.answer(
			"Нет доступных букмекеров для выбранной страны.")
	await call.answer()


@admin_required
async def process_bookmaker_stats(call: types.CallbackQuery):
	bookmaker_id = int(call.data.split(':')[1])
	stats = await get_bookmaker_stats_by_id(bookmaker_id)
	if stats:
		output = await format_bookmaker_stats(stats)
		await call.message.answer(output)
	else:
		await call.message.answer("Нет данных для выбранного букмекера.")
	await call.answer()


@admin_required
async def get_source_stats(message: types.Message):
	sources = await get_sources()
	if sources:
		keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
		for source in sources:
			keyboard.add(types.KeyboardButton(source.name))
		await message.answer("Выберите источник:", reply_markup=keyboard)
		await StatisticsStates.source_stats.set()
	else:
		await message.answer("Нет доступных источников.")


@admin_required
async def process_source_stats(message: types.Message, state: FSMContext):
	source_name = message.text
	source = await get_source_by_name(source_name)
	if source:
		await state.update_data(source_id=source.id)
		await message.answer("Введите начальную дату (ДД.ММ.ГГГГ):",
							 reply_markup=cancel_period_process_keyboard)
		await StatisticsStates.source_start_date.set()
	else:
		await message.answer(f"Источник {source_name} не найден.")
		await state.finish()


@admin_required
async def process_source_start_date(message: types.Message,
									state: FSMContext):
	try:
		start_date = datetime.strptime(message.text, '%d.%m.%Y').date()
		await state.update_data(start_date=start_date)
		await message.answer("Введите конечную дату (ДД.ММ.ГГГГ):",
							 reply_markup=cancel_period_process_keyboard)
		await StatisticsStates.source_end_date.set()
	except ValueError:
		await message.answer(
			"Неверный формат даты. Введите дату в формате ДД.ММ.ГГГГ",
			reply_markup=cancel_period_process_keyboard
		)


@admin_required
async def process_source_end_date(message: types.Message, state: FSMContext):
	try:
		end_date = datetime.strptime(message.text,
									 '%d.%m.%Y').date() + timedelta(days=1)
		data = await state.get_data()
		source_id = data['source_id']
		start_date = data['start_date']
		stats = await get_source_stats_data(source_id, start_date, end_date)
		if stats:
			output = await format_source_stats(stats)
			await message.answer(output, reply_markup=general_stats_keyboard)
		else:
			await message.answer(
				"Нет данных для выбранного источника и периода.",
				reply_markup=general_stats_keyboard)
		await state.finish()
	except ValueError:
		await message.answer(
			"Неверный формат даты. Введите дату в формате ДД.ММ.ГГГГ",
			reply_markup=cancel_period_process_keyboard
		)


@admin_required
async def get_salary_stats(message: types.Message):
	await message.answer("Выберите тип статистики по зарплате:",
						 reply_markup=salary_stats_keyboard)


@admin_required
async def get_total_salary_stats(message: types.Message):
	stats = await salary_stats()
	if stats:
		output = await format_salary_stats(stats)
		await message.answer(output)
		await message.answer(
			"Нажмите кнопку ниже, чтобы выдать зарплату всем сотрудникам:",
			reply_markup=pay_salaries_keyboard
		)
	else:
		await message.answer("Нет данных для отображения.")


@admin_required
async def pay_salaries(message: types.Message):
	await pay_all_salaries(message)
	await message.answer("Зарплаты выданы всем сотрудникам.")
	operation_description = f"Выдача зарплат всем сотрудникам пользователем {message.from_user.username}"
	await add_to_history(message.from_user.username, "salary",
						 operation_description)


@admin_required
async def get_employee_stats(message: types.Message):
	employees = await get_employees()
	if employees:
		keyboard = types.InlineKeyboardMarkup()
		for employee in employees:
			keyboard.add(types.InlineKeyboardButton(employee.name,
													callback_data=f"employee_stats_|_{employee.id}"))
		await message.answer("Выберите сотрудника:", reply_markup=keyboard)
		await StatisticsStates.employee_stats_variant.set()
	else:
		await message.answer("Нет доступных сотрудников.")


@admin_required
async def process_employee_stats(call: types.CallbackQuery,
								 state: FSMContext):
	await call.answer()
	employee_id = int(call.data.split('_|_')[1])
	stats = await get_employee_stats_by_id(employee_id)
	if stats:
		output = await format_employee_stats(stats)
		await call.message.answer(output)
		await state.update_data(employee_id=employee_id)

		# Добавляем кнопки для изменения баланса и выплаты зарплаты
		keyboard = types.InlineKeyboardMarkup()
		keyboard.add(types.InlineKeyboardButton("Изменить баланс",
												callback_data=f"change_balance_|_{employee_id}"))
		keyboard.add(types.InlineKeyboardButton("Выплатить зарплату",
												callback_data=f"pay_salary_|_{employee_id}"))
		await call.message.answer("Выберите действие:", reply_markup=keyboard)
		await StatisticsStates.employee_wait_action.set()
	else:
		await call.message.answer("Нет данных для выбранного сотрудника.")


@admin_required
async def process_change_balance(call: types.CallbackQuery,
								 state: FSMContext):
	await call.answer()
	employee_id = int(call.data.split('_|_')[1])
	await state.update_data(employee_id=employee_id)
	await call.message.answer(
		"Введите сумму для изменения баланса сотрудника:")
	await StatisticsStates.employee_salary.set()


@admin_required
async def process_pay_salary(call: types.CallbackQuery,
							 state: FSMContext):
	await call.answer()
	employee_id = int(call.data.split('_|_')[1])
	employee = await get_employee(employee_id)
	if employee:
		empl_balance = await employee.get_balance()
		if empl_balance <= 0:
			await call.message.answer("У сотрудника нет денег на балансе.")
			return
		await pay_employee_salary(employee_id)
		await call.message.answer(
			f"Зарплата выплачена сотруднику {employee.name}.")
		await call.bot.send_message(employee.id,
									f"Вам была выплачена зарплата в размере {empl_balance:.2f} EUR.")
		await add_to_history(call.from_user.username, "salary",
							 f"Выплата зарплаты сотруднику {employee.name} пользователем {call.from_user.username}")
	else:
		await call.message.answer("Сотрудник не найден.")
	await state.finish()


@admin_required
async def process_employee_salary(message: types.Message, state: FSMContext):
	data = await state.get_data()
	employee_id = data['employee_id']
	employee = await get_employee(employee_id)
	if not employee:
		await message.answer("Сотрудник не найден.")
		await state.finish()
		return
	if message.text:
		try:
			empl_balance = await employee.get_balance()
			adjustment_now = float(message.text)
			await update_employee_salary(employee_id, adjustment_now)
			employee = await get_employee(employee_id)
			await message.answer(
				f"Зарплата сотрудника обновлена на {empl_balance:.2f} EUR.")
			await message.bot.send_message(employee.id,
										   f"Ваш баланс изменен\nВаш баланс: {empl_balance:.2f} EUR.")

			operation_description = f"Изменение зарплаты сотрудника {employee.name} пользователем {message.from_user.username}"
			await add_to_history(message.from_user.username, "salary",
								 operation_description)

		except ValueError:
			await message.answer("Неверный формат зарплаты. Отмена.")
	else:
		await message.answer("Зарплата сотрудника не изменена.")
	await state.finish()


@admin_required
async def get_report_stats_by_date(message: types.Message):
	await StatisticsStates.report_period.set()
	await message.answer(
		"Введите период для отчетов в формате 'ДД.ММ.ГГГГ-ДД.ММ.ГГГГ':",
		reply_markup=cancel_period_process_keyboard
	)


@admin_required
async def process_report_period(message: types.Message, state: FSMContext):
	try:
		period = message.text.split('-')
		start_date = datetime.strptime(period[0], '%d.%m.%Y').date()
		end_date = datetime.strptime(period[1],
									 '%d.%m.%Y').date() + timedelta(days=1)
		await state.update_data(start_date=start_date, end_date=end_date)
		sources = await get_sources()
		if sources:
			keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
			for source in sources:
				keyboard.add(types.KeyboardButton(source.name))
			await message.answer("Выберите источник:", reply_markup=keyboard)
			await StatisticsStates.report_source.set()
		else:
			await message.answer("Нет доступных источников.")
			await state.finish()
	except ValueError:
		await message.answer(
			"Неверный формат периода. Введите период в формате ДД.ММ.ГГГГ-ДД.ММ.ГГГГ",
			reply_markup=cancel_period_process_keyboard
		)


@admin_required
async def process_report_source(message: types.Message, state: FSMContext):
	source_name = message.text
	source = await get_source_by_name(source_name)
	if source:
		data = await state.get_data()
		start_date = data['start_date']
		end_date = data['end_date']
		reports = await get_reports_by_period(start_date, end_date, source.id)
		if reports:
			keyboard = await format_report_stats(reports)

			await message.answer(".",
								 reply_markup=general_stats_keyboard)
			await message.answer(
				"Выберите отчет для просмотра деталей:",
				reply_markup=keyboard)
		else:
			await message.answer(
				"Нет отчетов для выбранного источника и периода.",
				reply_markup=general_stats_keyboard)
	else:
		await message.answer(f"Источник {source_name} не найден.",
							 reply_markup=general_stats_keyboard)
	await state.finish()


@admin_required
async def cancel_report(call: types.CallbackQuery, state: FSMContext):
	await call.answer()
	await state.finish()
	await call.message.answer("Отменено.")


@admin_required
async def process_report_details(message: types.Message, state: FSMContext):
	try:
		report_number = int(message.text)
		report = await get_report_by_id(report_number)
		if report:
			output = await format_report_details(report)
			await message.answer(output, reply_markup=general_stats_keyboard)
		else:
			await message.answer("Неверный номер отчета.")
	except ValueError:
		await message.answer("Неверный формат номера отчета. Введите число.")
	finally:
		await state.finish()


async def history_menu(message: types.Message):
	await message.answer("Выберите категорию статистики:",
						 reply_markup=history_stats_keyboard)


@admin_required
async def process_export_reports(message: types.Message, state: FSMContext):
	try:
		period = message.text.split('-')
		start_date = datetime.strptime(period[0], '%d.%m.%Y').date()
		end_date = datetime.strptime(period[1],
									 '%d.%m.%Y').date() + timedelta(days=1)
		# Включаем неподтвержденные отчеты в выгрузку (задача 4)
		reports = await get_reports_by_period(start_date, end_date, include_unconfirmed=True)

		# Вызываем функцию для создания Excel файла и получаем его байт-код
		excel_file = await export_reports_to_excel(reports, start_date,
												   end_date)

		# Отправляем сгенерированный файл пользователю
		await message.answer_document(types.InputFile(excel_file,
													  filename=f"reports_{start_date}_{end_date}.xlsx"))

		await add_to_history(message.from_user.username, "report",
							 f"Выгрузка отчетов в Excel пользователем {message.from_user.username}")
	except Exception as e:
		await message.answer(f"Ошибка при выгрузке отчетов: {e}")
	finally:
		await state.finish()


@admin_required
async def get_excel_reports(message: types.Message):
	await StatisticsStates.report_excel_period.set()
	await message.answer(
		"Введите период для отчетов в формате 'ДД.ММ.ГГГГ-ДД.ММ.ГГГГ':",
		reply_markup=cancel_period_process_keyboard
	)


@admin_required
async def delete_report(message: types.Message):
	await message.answer("Введите номер отчета для удаления:")
	await StatisticsStates.delete_report.set()


@admin_required
async def process_delete_report(message: types.Message, state: FSMContext):
	try:
		report_number = int(message.text)
		report = await get_report_by_id(report_number)
		if report:
			output = await format_report_details(report)
			await message.answer(output)
			keyboard = types.InlineKeyboardMarkup()
			keyboard.add(types.InlineKeyboardButton("Удалить отчет",
													callback_data=f"confirm_delete_report_|_{report_number}"))
			await state.finish()

			await message.answer("Подтвердите удаление отчета:",
								 reply_markup=keyboard)
		else:
			await state.finish()
			await message.answer("Отчет не найден.")
	except ValueError:
		await message.answer("Неверный формат номера отчета. Введите число.")


@admin_required
async def confirm_delete_report(call: types.CallbackQuery):
	await call.answer()

	report_id = int(call.data.split('_|_')[1])
	report = await get_report_by_id(report_id)
	if report:
		await delete_report_by_id(report_id)
		await call.message.answer("Отчет удален.")
	else:
		await call.message.answer("Отчет не найден.")


def register_stats_handlers(dp):
	dp.register_callback_query_handler(cancel_period_process, lambda
		call: call.data == "cancel_period_process", state="*")
	dp.register_callback_query_handler(cancel_report, lambda
		call: call.data == "cancel", state="*")
	dp.register_message_handler(show_statistics_menu, lambda
		message: message.text == "📊 Статистика")
	dp.register_message_handler(get_total_stats, lambda
		message: message.text == "Общая статистика")
	dp.register_message_handler(process_period_input,
								state=StatisticsStates.period_input)
	dp.register_message_handler(get_balance_stats, lambda
		message: message.text == "Общая статистика балансов")
	dp.register_message_handler(get_country_stats, lambda
		message: message.text == "Статистика по стране")
	dp.register_callback_query_handler(process_country_stats,
									   lambda call: call.data.startswith(
										   "country_stats"),
									   state=StatisticsStates.country_stats)
	dp.register_message_handler(process_country_start_date,
								state=StatisticsStates.country_start_date)
	dp.register_message_handler(process_country_end_date,
								state=StatisticsStates.country_end_date)
	dp.register_message_handler(get_bookmaker_stats, lambda
		message: message.text == "Статистика одной BK")
	dp.register_callback_query_handler(process_bookmaker_country,
									   lambda call: call.data.startswith(
										   "bookmaker_country"))
	dp.register_callback_query_handler(process_bookmaker_stats,
									   lambda call: call.data.startswith(
										   "bookmaker_stats"))
	dp.register_message_handler(get_source_stats, lambda
		message: message.text == "Статистика по направлению")
	dp.register_message_handler(process_source_stats,
								state=StatisticsStates.source_stats)
	dp.register_message_handler(process_source_start_date,
								state=StatisticsStates.source_start_date)
	dp.register_message_handler(process_source_end_date,
								state=StatisticsStates.source_end_date)
	dp.register_message_handler(get_bks_stats_by_reports, lambda
		message: message.text == "Статистика БК по отчётам")
	dp.register_message_handler(get_salary_stats, lambda
		message: message.text == "Статистика по зарплате")
	dp.register_message_handler(get_total_salary_stats, lambda
		message: message.text == "Общая статистика зарплаты")
	dp.register_message_handler(pay_salaries, lambda
		message: message.text == "Выдать зарплату всем сотрудникам")
	dp.register_message_handler(get_employee_stats, lambda
		message: message.text == "Статистика по пользователю")
	dp.register_callback_query_handler(process_employee_stats,
									   lambda call: call.data.startswith(
										   "employee_stats"),
									   state=StatisticsStates.employee_stats_variant)
	dp.register_message_handler(process_employee_salary,
								state=StatisticsStates.employee_salary)
	dp.register_message_handler(get_report_stats, lambda
		message: message.text == "Статистика по отчетам")
	dp.register_message_handler(get_report_stats_by_date, lambda
		message: message.text == "Посмотреть все отчеты")
	dp.register_message_handler(process_report_period,
								state=StatisticsStates.report_period)
	dp.register_message_handler(process_report_source,
								state=StatisticsStates.report_source)
	dp.register_message_handler(process_report_details,
								state=StatisticsStates.report_details)

	dp.register_message_handler(history_menu, lambda
		message: message.text == "📑 История операций")
	dp.register_message_handler(show_balance_stats_menu, lambda
		message: message.text == "Статистика по балансам")
	dp.register_message_handler(show_history, lambda
		message: message.text == "История операций")
	dp.register_callback_query_handler(process_change_balance,
									   lambda call: call.data.startswith(
										   "change_balance"),
									   state=StatisticsStates.employee_wait_action)
	dp.register_callback_query_handler(process_pay_salary,
									   lambda call: call.data.startswith(
										   "pay_salary"),
									   state=StatisticsStates.employee_wait_action)
	dp.register_message_handler(process_export_reports,
								state=StatisticsStates.report_excel_period)
	dp.register_message_handler(get_excel_reports, lambda
		message: message.text == "Выгрузить отчеты в Excel")
	dp.register_message_handler(delete_report, lambda
		message: message.text == "Удалить отчет по номеру")
	dp.register_message_handler(process_delete_report,
								state=StatisticsStates.delete_report)
	dp.register_message_handler(show_commissions_history, lambda
		message: message.text == "История комиссий")
	dp.register_callback_query_handler(process_country_period_start,
									   lambda call: call.data.startswith(
										   "country_period"), state="*")
	dp.register_callback_query_handler(confirm_delete_report, lambda
		call: call.data.startswith("confirm_delete_report"))
	dp.register_callback_query_handler(process_export_history, lambda
		call: call.data == "export_history_excel")
	dp.register_message_handler(process_history_excel_period,
								state=StatisticsStates.history_excel_period)
	dp.register_callback_query_handler(process_export_commissions_history,
									   lambda
										   call: call.data == "export_commissions_excel")
	dp.register_message_handler(process_commissions_excel_period,
								state=StatisticsStates.commissions_excel_period)
