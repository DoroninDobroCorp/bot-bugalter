from aiogram import types
from aiogram.types import WebAppInfo, LoginUrl

button_menu = types.KeyboardButton("В меню-управления")

"""Клавиатура для главного меню"""
main_menu_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
button_management = types.KeyboardButton("Управление")
button_statistic = types.KeyboardButton("📊 Статистика")
button_report = types.KeyboardButton("📝 Сделать отчет")
main_menu_keyboard.add(button_management, button_statistic)
main_menu_keyboard.add(button_report)

"""Клавиатура для меню управления"""
management_menu_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
button_country = types.KeyboardButton("🌎 Управление странами")
button_bk = types.KeyboardButton("🏦 Управление БК")
button_wallets = types.KeyboardButton("💳 Управление кошельками")
button_management_sources = types.KeyboardButton("📞 Управление источниками")
button_template = types.KeyboardButton("📄 Управление шаблонами")
button_employee = types.KeyboardButton("👨‍💻 Управление сотрудниками")
button_match = types.KeyboardButton("Матчи")
button_admin_menu = types.KeyboardButton("В Админ-меню")
management_menu_keyboard.add(button_country, button_bk)
management_menu_keyboard.add(button_wallets, button_management_sources)
management_menu_keyboard.add(button_template, button_employee)
management_menu_keyboard.add(button_match, button_admin_menu)

"""Клавиатура для управления матчами"""

matches_management_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
button_add_match = types.KeyboardButton("Установить имя матча")
button_list_ids = types.KeyboardButton("Список ID без имён")
button_check_matches = types.KeyboardButton("Проверить отчёты")
matches_management_keyboard.add(button_add_match, button_list_ids)
matches_management_keyboard.add(button_check_matches, button_menu)


"""Клавиатура для управления сотрудниками и админами"""
employee_admin_management_keyboard = types.ReplyKeyboardMarkup(
	resize_keyboard=True)
button_employee = types.KeyboardButton("👨‍💻 Сотрудники")
button_admin = types.KeyboardButton("Админы")
employee_admin_management_keyboard.add(button_employee, button_admin)
employee_admin_management_keyboard.add(button_admin_menu)

"""Клавиатура для управления админами"""
admin_management_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
button_add_admin = types.KeyboardButton("Добавить админа")
button_remove_admin = types.KeyboardButton("Удалить админа")
button_employee_management = types.KeyboardButton("В меню сотрудников")
admin_management_keyboard.add(button_add_admin, button_remove_admin)
admin_management_keyboard.add(button_employee_management)

"""Клавиатура для управления сотрудниками"""
employee_management_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
button_add_employee = types.KeyboardButton("Ожидают принятия")
button_remove_employee = types.KeyboardButton("Удалить сотрудника")
button_employee_list = types.KeyboardButton("Список сотрудников")
employee_management_keyboard.add(button_add_employee, button_remove_employee)
employee_management_keyboard.add(button_employee_list)
employee_management_keyboard.add(button_employee_management)

"""Клавиатура для управления источниками"""
manage_sources_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
button_add_source = types.KeyboardButton("Добавить источник")
button_remove_source = types.KeyboardButton("Удалить источник")
manage_sources_keyboard.add(button_add_source, button_remove_source)
button_untie_source = types.KeyboardButton("Отвязать источник")
manage_sources_keyboard.add(button_untie_source, button_menu)

"""Клавиатура для управления странами"""
country_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
button_add_country = types.KeyboardButton("🌎 Добавить страну")
button_remove_country = types.KeyboardButton("🌎 Удалить страну")
country_keyboard.add(button_add_country, button_remove_country)
country_keyboard.add(button_menu)

"""Клавиатура для управления шаблонами"""
template_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
button_add_template = types.KeyboardButton("Добавить шаблон")
button_remove_template = types.KeyboardButton("Удалить шаблон")
template_keyboard.add(button_add_template, button_remove_template)
template_keyboard.add(button_menu)

"""Клавиатура для управления БК"""
management_bk_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
button_add_bk = types.KeyboardButton("🏦 Добавить БК")
button_edit_bk = types.KeyboardButton("🏦 Изменить данные БК")
management_bk_keyboard.add(button_add_bk, button_edit_bk)
management_bk_keyboard.add(button_menu)

"""Клавиатура для управления кошельками"""
wallets_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
button_add_wallet = types.KeyboardButton("💳 Добавить кошелек")
button_edit_wallet = types.KeyboardButton("💳 Изменить кошелек")
button_remove_wallet = types.KeyboardButton("💳 Удалить кошелек")
wallets_keyboard.add(button_add_wallet, button_edit_wallet)
wallets_keyboard.add(button_remove_wallet)
wallets_keyboard.add(button_menu)

"""Клавиатура для редактирования кошелька"""
edit_wallet_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
button_edit_wallet_transfer = types.KeyboardButton("Переводы и выводы")
button_edit_wallet_balance = types.KeyboardButton("Изменить баланс")
button_edit_wallet_country = types.KeyboardButton("Изменить страну")
edit_wallet_keyboard.add(button_edit_wallet_transfer)
edit_wallet_keyboard.add(button_edit_wallet_balance)
edit_wallet_keyboard.add(button_edit_wallet_country)
button_edit_wallets = types.KeyboardButton("В меню кошельков")
edit_wallet_keyboard.add(button_edit_wallets)

"""Клавиатура отмены редактирования кошелька"""
cancel_editing_wallet_keyboard = types.InlineKeyboardMarkup()
cancel_edit_wallet_button = types.InlineKeyboardButton("Отмена",
                                                       callback_data="cancel_editing_wallet")
cancel_editing_wallet_keyboard.add(cancel_edit_wallet_button)

"""Клавиатура для переводов в кошельке"""
transfer_wallet_keyboard = types.InlineKeyboardMarkup()
replenish_wallet_button = types.InlineKeyboardButton("Пополнить",
                                                     callback_data="replenish_wallet")
withdraw_wallet_button = types.InlineKeyboardButton("Вывести",
                                                    callback_data="withdraw_wallet")
transfer_wallet_keyboard.add(replenish_wallet_button, withdraw_wallet_button)
cancel_transfer_wallet_button = types.InlineKeyboardButton("Отмена",
                                                           callback_data="cancel_editing_wallet")
transfer_wallet_keyboard.add(cancel_transfer_wallet_button)

"""Клавиатура для выбора вывести/пополнить с/на баланс/депозит"""


def transfer_from_where_keyboard(balance_button: str,
                                 deposit_button: str) -> types.InlineKeyboardMarkup:
	keyboard = types.InlineKeyboardMarkup()
	keyboard.add(
		types.InlineKeyboardButton(balance_button, callback_data="balance"),
		types.InlineKeyboardButton(deposit_button, callback_data="deposit")
	)
	keyboard.add(
		types.InlineKeyboardButton("Отмена",
		                           callback_data="cancel_editing_wallet")
	)
	return keyboard


"""Клавиатура для выбора поплнить с кошелька или бк"""
replenish_wallet_keyboard = types.InlineKeyboardMarkup()
replenish_wallet_from_wallet_button = types.InlineKeyboardButton("С кошелька",
                                                                 callback_data="wallet")
replenish_wallet_from_bk_button = types.InlineKeyboardButton("С БК",
                                                             callback_data="bk")
replenish_wallet_keyboard.add(replenish_wallet_from_wallet_button,
                              replenish_wallet_from_bk_button)
cancel_replenish_wallet_button = types.InlineKeyboardButton("Отмена",
                                                            callback_data="cancel_editing_wallet")
replenish_wallet_keyboard.add(cancel_replenish_wallet_button)

"""Клавиатура для выбора вывести на кошелек или бк"""
withdraw_wallet_keyboard = types.InlineKeyboardMarkup()
withdraw_wallet_to_wallet_button = types.InlineKeyboardButton("На кошелек",
                                                              callback_data="wallet")
withdraw_wallet_to_bk_button = types.InlineKeyboardButton("На БК",
                                                          callback_data="bk")
withdraw_wallet_keyboard.add(withdraw_wallet_to_wallet_button,
                             withdraw_wallet_to_bk_button)
cancel_withdraw_wallet_button = types.InlineKeyboardButton("Отмена",
                                                           callback_data="cancel_editing_wallet")
withdraw_wallet_keyboard.add(cancel_withdraw_wallet_button)

"""Клавиатура для выбора страны"""
transfer_country_keyboard = types.InlineKeyboardMarkup()
transfer_country_button = types.InlineKeyboardButton("Выбрать страну",
                                                     callback_data="transfer_country")
transfer_country_keyboard.add(transfer_country_button)
cancel_transfer_country_button = types.InlineKeyboardButton("Отмена",
                                                            callback_data="cancel_editing_wallet")
transfer_country_keyboard.add(cancel_transfer_country_button)

"""Клавиатура для выбора типа статистики"""
general_stats_keyboard = types.ReplyKeyboardMarkup(
	keyboard=[
		[
			types.KeyboardButton(text="Статистика по балансам"),
			types.KeyboardButton(text="Статистика по отчетам"),
		],
		[
			types.KeyboardButton(text="Общая статистика"),
			types.KeyboardButton(text="Статистика по зарплате"),
		],
		[
			types.KeyboardButton(text="📑 История операций"),
		],
		[
			button_admin_menu,
		]
	],
	resize_keyboard=True
)
"""Клавиатура для выбора типа отчета"""
reports_keyboard = types.ReplyKeyboardMarkup(
	keyboard=[
		[
			types.KeyboardButton(text="Посмотреть все отчеты"),
			types.KeyboardButton(text="Выгрузить отчеты в Excel"),
		],
		[
			types.KeyboardButton(text="Удалить отчет по номеру"),
		],
		[
			button_admin_menu,
		]
	],
	resize_keyboard=True
)
"""Клавиатура для выбора типа статистики по балансам"""
balance_stats_keyboard = types.ReplyKeyboardMarkup(
	keyboard=[
		[
			types.KeyboardButton(text="Общая статистика балансов"),
			types.KeyboardButton(text="Статистика одной BK"),
		],
		[
			types.KeyboardButton(text="Статистика по стране"),
			types.KeyboardButton(text="Статистика по направлению"),
		],
		[
			types.KeyboardButton(text="Статистика БК по отчётам"),
			button_admin_menu,
		]
	],
	resize_keyboard=True
)
"""Клавиатура для выбора типа статистики по отчетам"""
salary_stats_keyboard = types.ReplyKeyboardMarkup(
	keyboard=[
		[
			types.KeyboardButton(text="Общая статистика зарплаты"),
			types.KeyboardButton(text="Статистика по пользователю"),
		],
		[
			button_admin_menu,
		]
	],
	resize_keyboard=True
)
"""Клавиатура для выбора типа статистики по отчетам"""
history_stats_keyboard = types.ReplyKeyboardMarkup(
	keyboard=[
		[
			types.KeyboardButton(text="История комиссий"),
			types.KeyboardButton(text="История операций"),
		],
		[
			button_admin_menu,
		]
	],
	resize_keyboard=True
)

pay_salaries_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
button_pay_salaries = types.KeyboardButton("Выдать зарплату всем сотрудникам")
pay_salaries_keyboard.add(button_pay_salaries)
pay_salaries_keyboard.add(button_admin_menu)

employee_main_menu_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
button_get_balance = types.KeyboardButton("📊 Моя зарплата")
button_get_reports = types.KeyboardButton("📝 Мои отчеты")
button_confirm_reports = types.KeyboardButton("Подтвердить отчёты")
employee_main_menu_keyboard.add(button_get_balance, button_get_reports)
employee_main_menu_keyboard.add(button_confirm_reports)


export_history_keyboard = types.InlineKeyboardMarkup()
export_history_keyboard.add(
	types.InlineKeyboardButton("Выгрузить историю операций в Excel",
	                           callback_data="export_history_excel"))

export_commissions_history_keyboard = types.InlineKeyboardMarkup()
export_commissions_history_keyboard.add(
	types.InlineKeyboardButton("Выгрузить историю комиссий в Excel",
	                           callback_data="export_commissions_excel"))

cancel_period_process_keyboard = types.InlineKeyboardMarkup()
cancel_period_process_keyboard.add(
	types.InlineKeyboardButton("Отмена",
	                           callback_data="cancel_period_process")
)

cancel_period_employee_process_keyboard = types.InlineKeyboardMarkup()
cancel_period_employee_process_keyboard.add(
	types.InlineKeyboardButton("Отмена",
	                           callback_data="cancel_employee_period_process")
)
