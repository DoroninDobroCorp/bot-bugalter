import os
import time
import random as rd
from string import ascii_lowercase
from datetime import datetime as dt, timedelta as td

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import ParseMode

from bot.utils import *
from bot.keyboards import *
from bot.states import *
from report_logic.excel_reports import *


@admin_required
async def main(message: types.Message, state: FSMContext):
    await message.answer("Привет, админ!",
                         reply_markup=main_menu_keyboard)
    await state.finish()


@admin_required
async def edit_bk_balance(callback_query: types.CallbackQuery, state: FSMContext):
    """Старт изменения депозита/баланса БК"""
    await callback_query.answer()
    bk_id = int(callback_query.data.split('_|_')[-1])
    if not await get_bk_by_id(bk_id):
        await callback_query.message.answer("Ошибка, профиль БК не найден")
        return
    await state.update_data(bk_id=bk_id)
    await EditBkState.waiting_for_balance_choice.set()
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("Депозит", callback_data="bk_balance_choice_|_deposit"),
        types.InlineKeyboardButton("Баланс", callback_data="bk_balance_choice_|_balance")
    )
    keyboard.add(types.InlineKeyboardButton("Отмена", callback_data="cancel_editing_bk"))
    await callback_query.message.answer("Что изменить?", reply_markup=keyboard)


@admin_required
async def process_bk_balance_choice(callback_query: types.CallbackQuery, state: FSMContext):
    """Выбор типа корректируемого баланса (депозит/баланс)"""
    await callback_query.answer()
    choice = callback_query.data.split('_|_')[-1]
    await state.update_data(balance_field=choice)
    await EditBkState.waiting_for_balance_amount.set()
    await callback_query.message.answer("Введите число на которое нужно изменить (можно отрицательное)",
                                        reply_markup=cancel_editing_wallet_keyboard)


@admin_required
async def process_bk_balance_amount(message: types.Message, state: FSMContext):
    """Ввод суммы корректировки"""
    amount_text = message.text
    if amount_text.count("-") > 1 or not is_number(amount_text):
        await message.answer("Изменение должно быть числом, попробуйте снова")
        return
    await state.update_data(balance_amount=float(amount_text))
    await EditBkState.waiting_for_balance_reason.set()
    await message.answer("Введите причину изменения",
                         reply_markup=cancel_editing_wallet_keyboard)


@admin_required
async def process_bk_balance_reason(message: types.Message, state: FSMContext):
    """Применение корректировки с записью в историю и транзакции"""
    reason = message.text
    data = await state.get_data()
    bk_id = data.get("bk_id")
    field = data.get("balance_field")  # 'deposit' | 'balance'
    amount = data.get("balance_amount")

    bk = await get_bk_by_id(bk_id)
    if not bk:
        await message.answer("Ошибка, профиль БК не найден")
        await state.finish()
        return

    # Для изменения депозита/баланса используем внутреннюю транзакцию на БК
    if field == "deposit":
        if amount >= 0:
            await create_transaction(sender_wallet_id=None, receiver_wallet_id=None,
                                     sender_bk_id=None, receiver_bk_id=bk_id,
                                     sum=amount, sum_received=amount, from_="", where="deposit")
        else:
            amt = abs(amount)
            await create_transaction(sender_wallet_id=None, receiver_wallet_id=None,
                                     sender_bk_id=bk_id, receiver_bk_id=None,
                                     sum=amt, sum_received=amt, from_="deposit", where="")
    else:  # balance
        if amount >= 0:
            await create_transaction(sender_wallet_id=None, receiver_wallet_id=None,
                                     sender_bk_id=None, receiver_bk_id=bk_id,
                                     sum=amount, sum_received=amount, from_="", where="balance")
        else:
            amt = abs(amount)
            await create_transaction(sender_wallet_id=None, receiver_wallet_id=None,
                                     sender_bk_id=bk_id, receiver_bk_id=None,
                                     sum=amt, sum_received=amt, from_="balance", where="")

    await add_to_history(message.from_user.id, "bookmaker",
                         f"Изменён {('депозит' if field=='deposit' else 'баланс')} БК '{bk.name}' на {amount} ({reason}) пользователем {message.from_user.username}")

    # Показать новые значения
    bk_refreshed = await get_bk_by_id(bk_id)
    await message.answer(
        f"Готово. Депозит: {bk_refreshed.get_deposit():.2f} | Баланс: {bk_refreshed.get_balance():.2f}",
        reply_markup=management_bk_keyboard)
    await state.finish()


@admin_required
async def management_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Меню управления",
                         reply_markup=management_menu_keyboard)


@admin_required
async def employee_admin_management(message: types.Message):
    await message.answer("Управление сотрудниками",
                         reply_markup=employee_admin_management_keyboard)


@admin_required
async def admin_management(message: types.Message):
    await message.answer("Управление админами",
                         reply_markup=admin_management_keyboard)


@admin_required
async def employee_management(message: types.Message):
    await message.answer("Сотрудники",
                         reply_markup=employee_management_keyboard)


@admin_required
async def manage_sources(message: types.Message):
    """Управление источниками"""
    await message.answer("Управление источниками",
                         reply_markup=manage_sources_keyboard)


"""УПРАВЛЕНИЕ ИСТОЧНИКАМИ"""


@admin_required
async def untie_source(message: types.Message):
    """Отвязать источник от группы"""
    sources = await get_sources()
    if not sources:
        await message.answer("Нет источников")
        return
    keyboard = types.InlineKeyboardMarkup()
    for source in [s for s in sources if s.chat_id != 0]:
        button_untie_source = types.InlineKeyboardButton(source.name,
                                                         callback_data=f"untie_source_|_{source.id}")
        keyboard.add(button_untie_source)
    await message.answer("Выберите источник чтобы отвязать его от группы",
                         reply_markup=keyboard)


@admin_required
async def process_untie_source(callback_query: types.CallbackQuery):
    """Обработка отвязки источника от группы"""
    await callback_query.answer()
    source_id = int(callback_query.data.split('_|_')[-1])
    source = await Source.get(id=source_id)
    if source:
        await source.update(chat_id=0)
        await callback_query.message.answer(f"Источник '{source.name}' был отвязан от группы")
        await add_to_history(callback_query.from_user.id, "source",
                             f"Источник '{source.name}' был отвязан от группы пользователем {callback_query.from_user.username}")
    else:
        await callback_query.message.answer("Ошибка ,источник не найден")


@admin_required
async def remove_source(message: types.Message):
    """Удалить источник"""
    sources = await get_sources()
    if not sources:
        await message.answer("Нет источников")
        return
    keyboard = types.InlineKeyboardMarkup()
    for source in sources:
        button_remove_source = types.InlineKeyboardButton(source.name,
                                                          callback_data=f"remove_source_|_{source.id}")
        keyboard.add(button_remove_source)
    await message.answer("Выберите источник для удаления",
                         reply_markup=keyboard)


@admin_required
async def process_remove_source(callback_query: types.CallbackQuery):
    """Обработка удаления источника"""
    await callback_query.answer()
    source_id = int(callback_query.data.split('_|_')[-1])
    source = await Source.get(id=source_id)
    ans = await remove_source_from_db(source_id)
    if ans:
        await callback_query.message.answer("Источник был удален")
        await add_to_history(callback_query.from_user.id, "source",
                             f"Источник '{source.name}' был удалён пользователем {callback_query.from_user.username}")
    else:
        await callback_query.message.answer("Ошибка, источник не найден")


@admin_required
async def add_source(message: types.Message, state: FSMContext):
    """Добавить источник"""
    cancel_keyboard = types.InlineKeyboardMarkup()
    cancel_button = types.InlineKeyboardButton("Отмена",
                                               callback_data="cancel_adding_source")
    cancel_keyboard.add(cancel_button)
    await message.answer("Введите имя источника или нажмите кнопку отмены",
                         reply_markup=cancel_keyboard)
    await AddingSourceState.waiting_for_source_name.set()


@admin_required
async def process_add_source(message: types.Message, state: FSMContext):
    source_name = message.text
    if source_name.lower() == "отмена":
        await state.finish()
        await message.answer("Добавление источника отменено")
    else:
        await add_source_to_db(source_name)
        await state.finish()
        await message.answer(f"Источник {source_name} успешно добавлен")
        await add_to_history(message.from_user.id, "source",
                             f"Источник '{source_name}' добавлен пользователем {message.from_user.username}")


@admin_required
async def cancel_adding_source(callback_query: types.CallbackQuery,
                               state: FSMContext):
    """Отмена добавления источника"""
    await callback_query.answer()
    if callback_query.data == "cancel_adding_source":
        await state.finish()
        await callback_query.message.answer("Добавление источника отменено")


"""УПРАВЛЕНИЕ СОТРУДНИКАМИ"""


@admin_required
async def employee_list(message: types.Message):
    """Список сотрудников"""
    employees = await get_employees()
    if not employees:
        await message.answer("Нет сотрудников")
        return
    message_text = "Список сотрудников:\n"
    for employee in employees:
        message_text += f"{employee.name} (@{employee.username}) - {employee.id}\n"
    await message.answer(message_text)


@admin_required
async def cmd_view_waiting_users(message: types.Message):
    """Показать всех пользователей, ожидающих подтверждения"""
    pending_users = await get_pending_users()
    if not pending_users:
        await message.answer("Нет пользователей, ожидающих подтверждения")
        return
    for user in pending_users:
        # клавиатура для подтверждения или отклонения
        keyboard = types.InlineKeyboardMarkup()
        yes_button = types.InlineKeyboardButton("✅ Yes",
                                                callback_data=f"confirm_user_|_{user.id}")
        no_button = types.InlineKeyboardButton("🚫 No",
                                               callback_data=f"reject_user_|_{user.id}")
        keyboard.add(yes_button, no_button)
        await message.answer(f"{user.name} (@{user.username})",
                             reply_markup=keyboard)


@admin_required
async def employee_remove_keyboard(message: types.Message):
    """Отобразить клавиатуру для удаления сотрудника"""
    employees = await get_employees()
    if not employees:
        await message.answer("Нет сотрудников")
        return
    keyboard = types.InlineKeyboardMarkup()
    for employee in employees:
        button_remove_employee = types.InlineKeyboardButton(employee.name,
                                                            callback_data=f"remove_employee_|_{employee.id}")
        keyboard.add(button_remove_employee)
    await message.answer("Выберите сотрудника для удаления",
                         reply_markup=keyboard)


@admin_required
async def process_confirm_callback(callback_query: types.CallbackQuery):
    """Подтвердить запрос на добавление в список сотрудников"""
    await callback_query.answer()
    user_id = int(callback_query.data.split('_|_')[-1])
    if await if_user_employee(user_id):
        await callback_query.bot.answer_callback_query(callback_query.id,
                                                       "Юзер уже сотрудник")
        return
    if not await if_user_pending(user_id):
        await callback_query.bot.answer_callback_query(callback_query.id,
                                                       "Юзер не в списке ожидания")
        return

    ans = await make_employee_from_pending(user_id)
    employee = await get_employee(user_id)
    if ans:
        await callback_query.bot.send_message(callback_query.message.chat.id,
                                              "Сотрудник был добавлен")
        token = await create_token(user_id)
        await callback_query.bot.send_message(user_id,
                                              "Вы были добавлены в список сотрудников🎉",
                                              reply_markup=employee_main_menu_keyboard(token))
        await add_to_history(callback_query.from_user.id, "employee",
                             f"Сотрудник '{employee.name}' был добавлен пользователем {callback_query.from_user.username}")
    else:
        await callback_query.bot.send_message(callback_query.message.chat.id,
                                              "Запрос был отклонен")


@admin_required
async def process_reject_callback(callback_query: types.CallbackQuery):
    """Отклонить запрос на добавление в список сотрудников"""
    await callback_query.answer()
    user_id = int(callback_query.data.split('_|_')[-1])
    if await if_user_employee(user_id):
        await callback_query.bot.answer_callback_query(callback_query.id,
                                                       "Юзер уже сотрудник")
        return
    if not await if_user_pending(user_id):
        await callback_query.bot.answer_callback_query(callback_query.id,
                                                       "Юзер не в списке ожидания")
        return
    ans = await remove_user_from_pending(user_id)
    if ans:
        await callback_query.bot.send_message(callback_query.message.chat.id,
                                              "Запрос был отклонен")
        await callback_query.bot.send_message(user_id,
                                              "Ваш запрос был отклонен")
    else:
        await callback_query.bot.send_message(callback_query.message.chat.id,
                                              "Ошибка")


@admin_required
async def show_admin_creation_keyboard(message: types.Message):
    """Отобразить клавиатуру для создания админа"""
    ans = await get_employees_without_admins()
    if not ans:
        await message.answer("Нет сотрудников без админских прав")
        return
    # создаем клавиатуру со всеми сотрудниками кроме админов
    keyboard = types.InlineKeyboardMarkup()
    for employee in ans:
        button = types.InlineKeyboardButton(employee.name,
                                            callback_data=f"make_admin_|_{employee.id}")
        keyboard.add(button)

    await message.answer("Выберите сотрудника для назначения админом",
                         reply_markup=keyboard)


@admin_required
async def display_admin_removal_options(message: types.Message):
    """Отобразить клавиатуру для удаления админа"""
    ans = await get_admins()
    if not ans:
        await message.answer("Нет админов")
        return
    # создаем клавиатуру со всеми админами
    keyboard = types.InlineKeyboardMarkup()
    for admin in ans:
        employee = await get_employee(admin.employee_id)
        button = types.InlineKeyboardButton(employee.name,
                                            callback_data=f"remove_admin_|_{admin.employee_id}")
        keyboard.add(button)

    await message.answer("Выберите админа для удаления",
                         reply_markup=keyboard)


@admin_required
async def make_admin_callback(callback_query: types.CallbackQuery):
    """Сделать админом по callback"""
    await callback_query.answer()
    employee_id = int(callback_query.data.split('_|_')[-1])
    if not await if_user_employee(employee_id):
        await callback_query.message.answer(
            "Этот пользователь не является сотрудником")
        return
    if await is_admin(employee_id):
        await callback_query.message.answer("Этот сотрудник уже админ")
        return
    await make_admin(employee_id)
    admin = await Employee.get(id=employee_id)
    await callback_query.message.answer("Сотрудник стал админом")
    await add_to_history(callback_query.from_user.id, "admin",
                         f"Админ '{admin.name}' добавлен пользователем {callback_query.from_user.username}")


@admin_required
async def remove_admin_callback(callback_query: types.CallbackQuery):
    """Удалить админа по callback"""
    await callback_query.answer()
    admin_id = int(callback_query.data.split('_|_')[-1])
    if admin_id == callback_query.from_user.id:
        await callback_query.message.answer("Нельзя удалить самого себя")
        return
    if not await is_admin(admin_id):
        await callback_query.message.answer(
            "Этот пользователь не является админом")
        return
    admin = Admin.get(id=admin_id)
    await remove_admin(admin_id)
    await callback_query.message.answer("Админ был удален")
    await add_to_history(callback_query.from_user.id, "admin",
                         f"Админ '{admin.name}' был удалён пользователем {callback_query.from_user.username}")


@admin_required
async def remove_employee_callback(callback_query: types.CallbackQuery):
    """Удалить сотрудника по callback"""
    await callback_query.answer()
    employee_id = int(callback_query.data.split('_|_')[-1])
    employee = await get_employee(employee_id)
    ans = await remove_employee(employee_id)
    if ans:
        await callback_query.message.answer("Сотрудник был удален")
        await add_to_history(callback_query.from_user.id, "employee",
                             f"Сотрудник '{employee.name}' был удалён пользователем {callback_query.from_user.username}")
    else:
        await callback_query.message.answer("Ошибка сотрудник не найден")


"""УПРАВЛЕНИЕ СТРАНАМИ"""


@admin_required
async def country_management(message: types.Message):
    await message.answer("Страны", reply_markup=country_keyboard)


@admin_required
async def process_remove_country(callback_query: types.CallbackQuery):
    """Обработка удаления страны"""
    await callback_query.answer()
    country_id = int(callback_query.data.split('_|_')[-1])
    country = await get_country_by_id(country_id)
    if not country:
        await callback_query.message.answer("Страна не найдена")
        return
    if await is_country_balance_positive(country_id):
        await callback_query.message.answer(
            "Нельзя удалить страну с ненулевым балансом")
        return
    ans = await remove_country_from_db(country_id)
    if ans is True:
        await callback_query.message.answer("Страна была удалена")
        await add_to_history(callback_query.from_user.id, "country",
                             f"Страна '{country.flag} {country.name}' была удалена пользователем {callback_query.from_user.username}")
    elif isinstance(ans, str):
        # Возвращена строка с ошибкой о балансе
        await callback_query.message.answer(ans)
    else:
        await callback_query.message.answer("Ошибка, страна не найдена")


@admin_required
async def add_country(message: types.Message, state: FSMContext):
    """Добавить страну"""
    cancel_keyboard = types.InlineKeyboardMarkup()
    cancel_button = types.InlineKeyboardButton("Отмена",
                                               callback_data="cancel_adding_country")
    cancel_keyboard.add(cancel_button)
    await message.answer("Введите название страны или нажмите кнопку отмены",
                         reply_markup=cancel_keyboard)
    await AddingCountryState.waiting_for_country_name.set()


@admin_required
async def process_add_country(message: types.Message, state: FSMContext):
    country_name = message.text
    if country_name.lower() == "отмена":
        await state.finish()
        await message.answer("Добавление страны отменено")
    else:
        await state.update_data(country_name=country_name)
        await message.answer(
            "Введите флаг (смайлик) страны или нажмите кнопку отмены")
        await AddingCountryState.waiting_for_country_flag.set()


@admin_required
async def process_add_country_flag(message: types.Message, state: FSMContext):
    country_flag = message.text
    if country_flag.lower() == "отмена":
        await state.finish()
        await message.answer("Добавление страны отменено")
    else:
        async with state.proxy() as data:
            country_name = data['country_name']
        await add_country_to_db(country_name, country_flag)
        await state.finish()
        await message.answer(
            f"Страна {country_name} {country_flag} успешно добавлена")
        await add_to_history(message.from_user.id, "country",
                             f"Страна '{country_flag} {country_name}' добавлена пользователем {message.from_user.username}")


@admin_required
async def cancel_adding_country(callback_query: types.CallbackQuery,
                                state: FSMContext):
    """Отмена добавления страны"""
    await callback_query.answer()
    if callback_query.data == "cancel_adding_country":
        await state.finish()
        await callback_query.message.answer("Добавление страны отменено")


@admin_required
async def remove_country(message: types.Message):
    """Удалить страну"""
    countries = await get_countries()
    if not countries:
        await message.answer("Нет стран")
        return
    keyboard = types.InlineKeyboardMarkup()
    for country in countries:
        button_remove_country = types.InlineKeyboardButton(
            f"{country.flag} {country.name}",
            callback_data=f"remove_country_|_{country.id}")
        keyboard.add(button_remove_country)
    await message.answer("Выберите страну для удаления",
                         reply_markup=keyboard)


"""УПРАВЛЕНИЕ ШАБЛОНАМИ БК"""


@admin_required
async def templates_management(message: types.Message):
    """Управление шаблонами"""
    await message.answer("Шаблоны", reply_markup=template_keyboard)


@admin_required
async def process_remove_template(callback_query: types.CallbackQuery):
    """Обработка удаления шаблона"""
    await callback_query.answer()
    template_id = int(callback_query.data.split('_|_')[-1])
    exist = await get_template_by_id(template_id)
    if not exist:
        await callback_query.message.answer("Шаблон не найден")
        return
    template = await get_template_by_id(template_id)
    ans = await remove_template_from_db(template_id)
    if ans:
        await callback_query.message.answer("Шаблон был удален")
        await add_to_history(callback_query.from_user.id, "template",
                             f"Шаблон '{template.name}' удалён пользователем {callback_query.from_user.username}")
    else:
        await callback_query.message.answer("Ошибка, шаблон не найден")


@admin_required
async def add_template(message: types.Message, state: FSMContext):
    """Добавить шаблон"""
    countries = await get_countries()
    if not countries:
        await message.answer("Нет стран")
        await state.finish()
        return
    keyboard = types.InlineKeyboardMarkup()
    for country in countries:
        button_add_template = types.InlineKeyboardButton(
            f"{country.flag} {country.name}",
            callback_data=f"add_template_|_{country.id}")
        keyboard.add(button_add_template)

    await message.answer("Выберите страну для добавления шаблона",
                         reply_markup=keyboard)


@admin_required
async def countries_adding_template(callback_query: types.CallbackQuery,
                                    state: FSMContext):
    """Выбор страны для добавления шаблона"""
    country_id = int(callback_query.data.split('_|_')[-1])
    if not await get_country_by_id(country_id):
        await callback_query.answer("Ошибка, страна не найдена")
        return
    await state.update_data(country_id=country_id)
    await callback_query.answer()
    await AddingTemplateState.waiting_for_template_name.set()
    keyboard = types.InlineKeyboardMarkup()
    cancel_button = types.InlineKeyboardButton("Отмена",
                                               callback_data="cancel_adding_template")
    keyboard.add(cancel_button)
    await callback_query.message.answer("Введите название шаблона",
                                        reply_markup=keyboard)


@admin_required
async def process_add_template_name(message: types.Message,
                                    state: FSMContext):
    template_name = message.text
    if template_name.lower() == "отмена":
        await state.finish()
        await message.answer("Добавление шаблона отменено")
    else:
        await state.update_data(template_name=template_name)
        await AddingTemplateState.waiting_for_template_percent.set()
        keyboard = types.InlineKeyboardMarkup()
        cancel_button = types.InlineKeyboardButton("Отмена",
                                                   callback_data="cancel_adding_template")
        keyboard.add(cancel_button)
        await message.answer("Введите процент шаблона",
                             reply_markup=keyboard)


@admin_required
async def process_add_template_percent(message: types.Message,
                                       state: FSMContext):
    """Добавление процента шаблона"""
    template_percent = message.text
    if template_percent.lower() == "отмена":
        await state.finish()
        await message.answer("Добавление шаблона отменено")
    else:
        if not is_number(template_percent):
            await message.answer(
                "Процент должен быть числом, попробуйте снова")
            return
        data = await state.get_data()
        country_id = data.get("country_id")
        template_name = data.get("template_name").capitalize()
        if await is_template_exists(country_id=country_id,
                                    template_name=template_name):
            await message.answer("Шаблон с таким именем уже существует")
            await state.finish()
            return
        await add_template_to_db(template_name, template_percent, country_id)
        await state.finish()
        await message.answer(f"Шаблон {template_name} успешно добавлен")
        await add_to_history(message.from_user.id, "template",
                             f"Шаблон '{template_name}' добавлен пользователем {message.from_user.username}")


@admin_required
async def cancel_adding_template(callback_query: types.CallbackQuery,
                                 state: FSMContext):
    """Отмена добавления шаблона"""
    await callback_query.answer()
    if callback_query.data == "cancel_adding_template":
        await state.finish()
        await callback_query.message.answer("Добавление шаблона отменено")


@admin_required
async def remove_template(message: types.Message):
    """Удалить шаблон"""
    countries = await get_countries()
    if not countries:
        await message.answer("Нет стран")
        return
    keyboard = types.InlineKeyboardMarkup()
    for country in countries:
        button_country = types.InlineKeyboardButton(
            f"{country.flag} {country.name}",
            callback_data=f"remove_template_country_|_{country.id}")
        keyboard.add(button_country)
    await message.answer("Выберите страну для удаления шаблона",
                         reply_markup=keyboard)


@admin_required
async def process_remove_template_country(
        callback_query: types.CallbackQuery):
    """Обработка выбора страны для удаления шаблона"""
    await callback_query.answer()
    country_id = int(callback_query.data.split('_|_')[-1])
    templates = await get_templates_by_country_id(country_id)
    if not templates:
        await callback_query.message.answer("Нет шаблонов для этой страны")
        return
    keyboard = types.InlineKeyboardMarkup()
    for template in templates:
        button_remove_template = types.InlineKeyboardButton(template.name,
                                                            callback_data=f"remove_template_|_{template.id}")
        keyboard.add(button_remove_template)
    await callback_query.message.answer("Выберите шаблон для удаления",
                                        reply_markup=keyboard)


"""Управление БК"""


@admin_required
async def bk_management(message: types.Message):
    # Оппортунистическая очистка деактивированных БК старше 90 дней с нулевыми балансами
    try:
        await cleanup_inactive_bookmakers()
    except Exception:
        # Тихо игнорируем ошибки очистки, чтобы не мешать UX
        pass
    await message.answer("Управление БК", reply_markup=management_bk_keyboard)


@admin_required
async def add_bk_country(message: types.Message, state: FSMContext):
    """Выбрать страну для добавления БК"""
    countries = await get_countries()
    if not countries:
        await message.answer("Нет стран")
        await state.finish()
        return
    keyboard = types.InlineKeyboardMarkup()
    for country in countries:
        button_add_bk = types.InlineKeyboardButton(
            f"{country.flag} {country.name}",
            callback_data=f"add_bk_by_country_|_{country.id}")
        keyboard.add(button_add_bk)
    cancel_button = types.InlineKeyboardButton("Отмена",
                                               callback_data="cancel_adding_bk")
    keyboard.add(cancel_button)

    await message.answer("Выберите страну для добавления БК",
                         reply_markup=keyboard)


@admin_required
async def add_bk_by_template(callback_query: types.CallbackQuery,
                             state: FSMContext):
    """Выбор шаблона для добавления БК"""
    country_id = int(callback_query.data.split('_|_')[-1])
    if not await get_country_by_id(country_id):
        await callback_query.answer("Ошибка, страна не найдена")
        return
    await state.update_data(country_id=country_id)
    await callback_query.answer()
    templates = await get_templates_by_country_id(country_id)
    if not templates:
        await callback_query.message.answer("Нет шаблонов для этой страны")
        return
    keyboard = types.InlineKeyboardMarkup()
    for template in templates:
        button_add_bk = types.InlineKeyboardButton(template.name,
                                                   callback_data=f"add_bk_by_template_|_{template.id}")
        keyboard.add(button_add_bk)
    cancel_button = types.InlineKeyboardButton("Отмена",
                                               callback_data="cancel_adding_bk")
    keyboard.add(cancel_button)
    await callback_query.message.answer("Выберите шаблон для добавления БК",
                                        reply_markup=keyboard)


@admin_required
async def cancel_adding_bk(callback_query: types.CallbackQuery,
                           state: FSMContext):
    """Отмена добавления БК"""
    await callback_query.answer()
    await state.finish()
    await callback_query.message.answer("Добавление БК отменено",
                                        reply_markup=management_bk_keyboard)


@admin_required
async def process_add_bk_by_template(callback_query: types.CallbackQuery,
                                     state: FSMContext):
    """Обработка выбора шаблона для добавления БК"""
    template_id = int(callback_query.data.split('_|_')[-1])
    if not await get_template_by_id(template_id):
        await callback_query.answer("Ошибка, шаблон не найден")
        return
    await state.update_data(template_id=template_id)
    await callback_query.answer()
    await AddingBkState.waiting_for_profile_name.set()
    keyboard = types.InlineKeyboardMarkup()
    cancel_button = types.InlineKeyboardButton("Отмена",
                                               callback_data="cancel_adding_bk")
    keyboard.add(cancel_button)
    await callback_query.message.answer("Введите имя профиля БК",
                                        reply_markup=keyboard)


@admin_required
async def process_add_bk_by_all_info(message: types.Message,
                                     state: FSMContext):
    """Добавление БК по всей информации"""
    profile_name = message.text.capitalize()
    if profile_name.lower() == "отмена":
        await state.finish()
        await message.answer("Добавление профиля БК отменено")
    else:
        data = await state.get_data()
        template_id = data.get("template_id")
        country_id = data.get("country_id")
        template = await get_template_by_id(template_id)
        country = await get_country_by_id(country_id)
        if not template:
            await message.answer("Ошибка, шаблон не найден")
            await state.finish()
            return
        if not country:
            await message.answer("Ошибка, страна не найдена")
            await state.finish()
            return
        if await is_bk_exists(template_id, country_id, template.name,
                              profile_name):
            await message.answer("Профиль БК с таким именем уже существует")
            await state.finish()
            return
        await add_bk_to_db(profile_name, template_id, country_id)
        await state.finish()
        await message.answer(
            "✅ БК успешно создана\n\n"
            "Информация о БК:\n"
            f"Название: {template.name}\n"
            f"Страна: {country.flag} {country.name}\n"
            f"Профиль: {profile_name}\n"
            f"Баланс: 0 💶"
        )
        await add_to_history(message.from_user.id, "bookmaker",
                             f"Букмекер '{template.name}' ({profile_name}) добавлен пользователем {message.from_user.username}")


@admin_required
async def edit_bk_country(message: types.Message):
    """Редактирование БК"""
    countries = await get_countries()
    if not countries:
        await message.answer("Нет стран")
        return
    keyboard = types.InlineKeyboardMarkup()
    for country in countries:
        button_edit_bk = types.InlineKeyboardButton(
            f"{country.flag} {country.name}",
            callback_data=f"edit_bk_by_country_|_{country.id}")
        keyboard.add(button_edit_bk)
    cancel_button = types.InlineKeyboardButton("Отмена",
                                               callback_data="cancel_editing_bk")
    keyboard.add(cancel_button)
    await message.answer("Выберите страну для редактирования БК",
                         reply_markup=keyboard)


@admin_required
async def edit_bk_by_country(callback_query: types.CallbackQuery,
                             state: FSMContext):
    """Выбор профиля БК по стране"""
    country_id = int(callback_query.data.split('_|_')[-1])
    country = await get_country_by_id(country_id)
    if not country:
        await callback_query.answer("Ошибка, страна не найдена")
        return
    await state.update_data(country_id=country_id)
    await callback_query.answer()

    bks = country.bookmakers
    if not bks:
        await callback_query.message.answer(
            "Нет профилей БК для этой страны")
        return

    keyboard = types.InlineKeyboardMarkup()
    for bk in bks:
        button_edit_bk = types.InlineKeyboardButton(
            f"{bk.template.name} | {bk.name} | {round(bk.get_balance(), 3)}",
            callback_data=f"edit_bk_by_profile_|_{bk.id}")
        keyboard.add(button_edit_bk)

    cancel_button = types.InlineKeyboardButton("Отмена",
                                               callback_data="cancel_editing_bk")
    keyboard.add(cancel_button)

    await callback_query.message.answer(
        "Выберите профиль БК для редактирования",
        reply_markup=keyboard)


@admin_required
async def cancel_editing_bk(callback_query: types.CallbackQuery,
                            state: FSMContext):
    """Отмена редактирования БК"""
    await callback_query.answer()
    if callback_query.data == "cancel_editing_bk":
        await state.finish()
        await callback_query.message.answer("Редактирование БК отменено",
                                            reply_markup=management_bk_keyboard)


@admin_required
async def process_edit_bk_by_profile(callback_query: types.CallbackQuery,
                                     state: FSMContext):
    """Обработка выбора профиля БК для редактирования"""
    bk_id = int(callback_query.data.split('_|_')[-1])
    if not await get_bk_by_id(bk_id):
        await callback_query.answer("Ошибка, профиль БК не найден")
        return
    await callback_query.answer()
    keyboard = types.InlineKeyboardMarkup()
    edit_profile_name_button = types.InlineKeyboardButton(
        "Изменить имя профиля",
        callback_data=f"edit_profile_name_|_{bk_id}")
    edit_profile_percentage_button = types.InlineKeyboardButton(
        "Изменить процент",
        callback_data=f"edit_profile_percentage_|_{bk_id}")

    delite_profile_button = types.InlineKeyboardButton("Удалить",
                                                       callback_data=f"delite_profile_|_{bk_id}")
    cancel_button = types.InlineKeyboardButton("Отмена",
                                               callback_data="cancel_editing_bk")
    keyboard.add(edit_profile_name_button, edit_profile_percentage_button)
    if await is_bk_active(bk_id):

        deactivate_profile_button = types.InlineKeyboardButton(
            "Деактивировать",
            callback_data=f"deactivate_profile_|_{bk_id}")
        keyboard.add(delite_profile_button, deactivate_profile_button)
    else:
        activate_profile_button = types.InlineKeyboardButton("Активировать",
                                                             callback_data=f"activate_profile_|_{bk_id}")
        keyboard.add(delite_profile_button, activate_profile_button)
    edit_bk_balance_button = types.InlineKeyboardButton("Изменить баланс",
                                                        callback_data=f"edit_bk_balance_|_{bk_id}")
    keyboard.add(edit_bk_balance_button)
    transfer_money_button = types.InlineKeyboardButton("Перевести деньги",
                                                       callback_data=f"transfer_money_from_bk_|_{bk_id}")
    keyboard.add(transfer_money_button)
    keyboard.add(cancel_button)
    await EditBkState.waiting_for_action.set()
    await state.update_data(bk_id=bk_id)
    bk_info = await get_bk_by_id(bk_id)

    await callback_query.message.answer(
        f"Профиль БК {bk_info.name}\nПроцент: {bk_info.salary_percentage}\nСтрана: {bk_info.country.flag} {bk_info.country.name}\nШаблон: {bk_info.template.name}\nАктивен: {bk_info.is_active}\nДепозит: {bk_info.get_deposit()}\nБаланс: {bk_info.get_balance()}\nВыберите действие",
        reply_markup=keyboard)


@admin_required
async def transfer_money_from_bk(callback_query: types.CallbackQuery,
                                 state: FSMContext):
    """Перевод денег с бк"""
    await callback_query.answer()
    bk_id = int(callback_query.data.split('_|_')[-1])
    if not await get_bk_by_id(bk_id):
        await callback_query.message.answer("Ошибка, профиль БК не найден")
        return
    await TransferMoneyState.waiting_for_action.set()
    await state.update_data(bk_id=bk_id)
    await callback_query.message.answer("Выберите тип операции",
                                        reply_markup=transfer_wallet_keyboard)


@admin_required
async def edit_profile_name(callback_query: types.CallbackQuery,
                            state: FSMContext):
    """Изменение имени профиля БК"""
    await callback_query.answer()
    await EditBkState.waiting_for_profile_name.set()
    if not await get_bk_by_id(int(callback_query.data.split('_|_')[-1])):
        await callback_query.message.answer("Ошибка, профиль БК не найден")
        await state.finish()
        return
    keyboard = types.InlineKeyboardMarkup()
    cancel_button = types.InlineKeyboardButton("Отмена",
                                               callback_data="cancel_editing_bk")
    keyboard.add(cancel_button)
    await callback_query.message.answer("Введите новое имя профиля",
                                        reply_markup=keyboard)


@admin_required
async def process_edit_profile_name(message: types.Message,
                                    state: FSMContext):
    """Обработка изменения имени профиля БК"""
    profile_name = message.text
    if profile_name.lower() == "отмена":
        await state.finish()
        await message.answer("Изменение имени профиля отменено")
    else:
        data = await state.get_data()
        bk_id = data.get("bk_id")
        profile_name = profile_name.capitalize()
        if not await get_bk_by_id(bk_id):
            await message.answer("Ошибка, профиль БК не найден")
            await state.finish()
            return
        bk = await get_bk_by_id(bk_id)
        await edit_bk_name(bk_id, profile_name)
        await state.finish()
        await message.answer(
            f"Имя профиля успешно изменено на {profile_name}")
        await add_to_history(message.from_user.id, "bookmaker",
                             f"Имя профиля изменено с '{bk.name}' на '{profile_name}' пользователем {message.from_user.username}")


@admin_required
async def edit_profile_percentage(callback_query: types.CallbackQuery,
                                  state: FSMContext):
    """Изменение процента профиля БК"""
    await callback_query.answer()
    await EditBkState.waiting_for_percent.set()
    if not await get_bk_by_id(int(callback_query.data.split('_|_')[-1])):
        await callback_query.message.answer("Ошибка, профиль БК не найден")
        await state.finish()
        return
    keyboard = types.InlineKeyboardMarkup()
    cancel_button = types.InlineKeyboardButton("Отмена",
                                               callback_data="cancel_editing_bk")
    keyboard.add(cancel_button)
    await callback_query.message.answer("Введите новый процент профиля",
                                        reply_markup=keyboard)


@admin_required
async def process_edit_profile_percentage_percentage(message: types.Message,
                                                     state: FSMContext):
    """Обработка изменения процента профиля БК"""
    profile_percent = message.text
    if profile_percent.lower() == "отмена":
        await state.finish()
        await message.answer("Изменение процента профиля отменено")
    else:
        if not is_number(profile_percent):
            await message.answer(
                "Процент должен быть числом, попробуйте снова")
            return
        data = await state.get_data()
        bk_id = data.get("bk_id")
        if not await get_bk_by_id(bk_id):
            await message.answer("Ошибка, профиль БК не найден")
            await state.finish()
            return
        bk = await get_bk_by_id(bk_id)
        await edit_bk_percent(bk_id, profile_percent)
        await state.finish()
        await message.answer(
            f"Процент профиля изменен на {profile_percent}")
        await add_to_history(message.from_user.id, "bookmaker",
                             f"Процент БК '{bk.name}' изменён с '{bk.salary_percentage}' на '{profile_percent}' пользователем {message.from_user.username}")
        await state.finish()


@admin_required
async def deactivate_profile(callback_query: types.CallbackQuery,
                             state: FSMContext):
    """Деактивация профиля БК"""
    await callback_query.answer()
    bk_id = int(callback_query.data.split('_|_')[-1])
    if not await get_bk_by_id(bk_id):
        await callback_query.message.answer("Ошибка, профиль БК не найден")
        return
    bk = await get_bk_by_id(bk_id)
    await deactivate_bk(bk_id)
    await callback_query.message.answer("Профиль деактивирован")
    await add_to_history(callback_query.from_user.id, "bookmaker",
                         f"Букмекер '{bk.name}' деактивирован пользователем {callback_query.from_user.username}")
    await state.finish()


@admin_required
async def activate_profile(callback_query: types.CallbackQuery,
                           state: FSMContext):
    """Активация профиля БК"""
    await callback_query.answer()
    bk_id = int(callback_query.data.split('_|_')[-1])
    if not await get_bk_by_id(bk_id):
        await callback_query.message.answer("Ошибка, профиль БК не найден")
        return
    bk = await get_bk_by_id(bk_id)
    await activate_bk(bk_id)
    await callback_query.message.answer("Профиль активирован")
    await add_to_history(callback_query.from_user.id, "bookmaker",
                         f"Букмекер '{bk.name}' активирован пользователем {callback_query.from_user.username}")
    await state.finish()


@admin_required
async def delite_profile(callback_query: types.CallbackQuery,
                         state: FSMContext):
    await callback_query.answer()
    bk_id = int(callback_query.data.split('_|_')[-1])
    if not await get_bk_by_id(bk_id):
        await callback_query.message.answer("Ошибка, профиль БК не найден")
        return

    await state.update_data(bk_id=bk_id)
    keyboard = types.InlineKeyboardMarkup()
    confirm_button = types.InlineKeyboardButton("Подтвердить удаление",
                                                callback_data="confirm_delete_bk")
    cancel_button = types.InlineKeyboardButton("Отмена",
                                               callback_data="cancel_delete_bk")
    keyboard.add(confirm_button, cancel_button)
    await callback_query.message.answer(
        "Вы уверены, что хотите удалить этот профиль БК навсегда?",
        reply_markup=keyboard)
    await state.set_state("waiting_delete_confirmation")


@admin_required
async def confirm_delete_bk(callback_query: types.CallbackQuery,
                            state: FSMContext):
    await callback_query.answer()
    data = await state.get_data()
    bk_id = data.get("bk_id")
    bk = await get_bk_by_id(bk_id)
    await delite_bk(bk_id)
    await callback_query.message.answer("Профиль удален")
    await add_to_history(callback_query.from_user.id, "bookmaker",
                         f"Букмекер '{bk.name}' удалён пользователем {callback_query.from_user.username}")
    await state.finish()


@admin_required
async def cancel_delete_bk(callback_query: types.CallbackQuery,
                           state: FSMContext):
    await callback_query.answer()
    await callback_query.message.answer("Удаление профиля БК отменено")
    await state.finish()


"""УПРАВЛЕНИЕ КОШЕЛЬКАМИ"""


@admin_required
async def wallets_management(message: types.Message):
    await message.answer("Кошельки", reply_markup=wallets_keyboard)


@admin_required
async def add_wallet(message: types.Message):
    await AddingWalletState.waiting_for_wallet_name.set()
    keyboard = types.InlineKeyboardMarkup()
    cancel_button = types.InlineKeyboardButton("Отмена",
                                               callback_data="cancel_adding_wallet")
    keyboard.add(cancel_button)
    await message.answer("Введите название кошелька", reply_markup=keyboard)


@admin_required
async def process_wallet_name(message: types.Message, state: FSMContext):
    wallet_name = message.text
    await state.update_data(wallet_name=wallet_name)
    await AddingWalletState.waiting_for_general_type.set()
    keyboard = types.InlineKeyboardMarkup()
    binance_button = types.InlineKeyboardButton("Binance",
                                                callback_data="add_binance_wallet")
    card_button = types.InlineKeyboardButton("Карта",
                                             callback_data="add_card_wallet")
    keyboard.add(binance_button, card_button)
    cancel_button = types.InlineKeyboardButton("Отмена",
                                               callback_data="cancel_adding_wallet")
    keyboard.add(cancel_button)
    await message.answer("Выберите тип кошелька", reply_markup=keyboard)


@admin_required
async def add_binance_wallet(callback_query: types.CallbackQuery,
                             state: FSMContext):
    await state.update_data(general_wallet_type="Binance")
    await callback_query.answer()
    await AddingWalletState.waiting_for_type.set()

    keyboard = types.InlineKeyboardMarkup()
    country_button = types.InlineKeyboardButton("Страна",
                                                callback_data="select_country")
    common_button = types.InlineKeyboardButton("Общий",
                                               callback_data="enter_deposit")
    keyboard.add(country_button, common_button)
    cancel_button = types.InlineKeyboardButton("Отмена",
                                               callback_data="cancel_adding_wallet")
    keyboard.add(cancel_button)
    await callback_query.message.answer("Выберите тип кошелька Binance",
                                        reply_markup=keyboard)


@admin_required
async def add_card_wallet(callback_query: types.CallbackQuery,
                          state: FSMContext):
    await callback_query.answer()
    await state.update_data(general_wallet_type="Карта")
    await AddingWalletState.waiting_for_type.set()
    keyboard = types.InlineKeyboardMarkup()
    country_button = types.InlineKeyboardButton("Страна",
                                                callback_data="select_country")
    common_button = types.InlineKeyboardButton("Общий",
                                               callback_data="enter_deposit")
    keyboard.add(country_button, common_button)
    cancel_button = types.InlineKeyboardButton("Отмена",
                                               callback_data="cancel_adding_wallet")
    keyboard.add(cancel_button)
    await callback_query.message.answer("Выберите тип кошелька Карта",
                                        reply_markup=keyboard)


@admin_required
async def select_country_wallet(callback_query: types.CallbackQuery,
                                state: FSMContext):
    await callback_query.answer()
    await state.update_data(wallet_type="Страна")
    await AddingWalletState.waiting_for_country_id.set()

    countries = await get_countries()
    if not countries:
        await callback_query.message.answer("Нет стран",
                                            reply_markup=wallets_keyboard)
        await state.finish()
        return
    keyboard = types.InlineKeyboardMarkup()
    for country in countries:
        button_country = types.InlineKeyboardButton(
            f"{country.flag} {country.name}",
            callback_data=f"add_wallet_by_country_|_{country.id}")
        keyboard.add(button_country)
    cancel_button = types.InlineKeyboardButton("Отмена",
                                               callback_data="cancel_adding_wallet")
    keyboard.add(cancel_button)
    await callback_query.message.answer(
        "Выберите страну для добавления кошелька",
        reply_markup=keyboard)


@admin_required
async def process_add_wallet_by_country(callback_query: types.CallbackQuery,
                                        state: FSMContext):
    await callback_query.answer()
    country_id = int(callback_query.data.split('_|_')[-1])
    if not await get_country_by_id(country_id):
        await callback_query.answer("Ошибка, страна не найдена")
        await state.finish()
        await callback_query.message.answer("Добавление кошелька отменено",
                                            reply_markup=wallets_keyboard)
        return
    await state.update_data(country_id=country_id)
    await callback_query.answer()
    keyboard = types.InlineKeyboardMarkup()
    cancel_button = types.InlineKeyboardButton("Отмена",
                                               callback_data="cancel_adding_wallet")
    keyboard.add(cancel_button)
    await callback_query.message.answer("Введите депозит",
                                        reply_markup=keyboard)
    await AddingWalletState.waiting_for_wallet_deposit.set()


@admin_required
async def enter_deposit(callback_query: types.CallbackQuery,
                        state: FSMContext):
    await callback_query.answer()
    await AddingWalletState.waiting_for_wallet_deposit.set()

    keyboard = types.InlineKeyboardMarkup()
    cancel_button = types.InlineKeyboardButton("Отмена",
                                               callback_data="cancel_adding_wallet")
    keyboard.add(cancel_button)
    await callback_query.message.answer("Введите депозит",
                                        reply_markup=keyboard)


@admin_required
async def process_deposit(message: types.Message, state: FSMContext):
    deposit = message.text
    if deposit.lower() == "отмена":
        await state.finish()
        await message.answer("Добавление кошелька отменено")
        return
    if not is_number(deposit):
        await message.answer("Депозит должен быть числом, попробуйте снова")
        return
    data = await state.get_data()
    wallet_name = data.get("wallet_name")
    wallet_type = data.get("wallet_type")
    general_wallet_type = data.get("general_wallet_type")
    if wallet_type == "Страна":
        country_id = data.get("country_id")
        if not await get_country_by_id(country_id):
            await message.answer("Ошибка, страна не найдена",
                                 reply_markup=wallets_keyboard)
            await state.finish()
            return
        await add_wallet_to_db(wallet_name=wallet_name,
                               wallet_type=wallet_type,
                               general_wallet_type=general_wallet_type,
                               deposit=deposit, country_id=country_id)
    else:
        wallet_type = "Общий"
        await add_wallet_to_db(wallet_name=wallet_name,
                               wallet_type=wallet_type,
                               general_wallet_type=general_wallet_type,
                               deposit=deposit)
    await state.finish()
    await add_to_history(message.from_user.id, "wallet",
                         f"Кошелёк '{wallet_name}' добавлен пользователем {message.from_user.username}")

    await message.answer(
        "✅ Кошелек успешно создан\n\n"
        "Информация о кошельке:\n"
        f"Название: {wallet_name}\n"
        f"Баланс кошелька: {deposit} 💶\n"
        f"Тип кошелька: {wallet_type}\n"
        f"Система кошелька: {general_wallet_type}"
    )


@admin_required
async def cancel_adding_wallet(callback_query: types.CallbackQuery,
                               state: FSMContext):
    await callback_query.answer()
    if callback_query.data == "cancel_adding_wallet":
        await state.finish()
        await callback_query.message.answer("Добавление кошелька отменено",
                                            reply_markup=wallets_keyboard)


@admin_required
async def return_to_wallet_management(message: types.Message,
                                      state: FSMContext):
    await state.finish()
    await message.answer("Управление кошельками",
                         reply_markup=wallets_keyboard)


@admin_required
async def delite_wallet(message: types.Message):
    """Удалить кошелек"""
    countries = await get_countries()
    wallets = await get_wallets()
    if not wallets:
        await message.answer("Нет кошельков")
        return
    keyboard = types.InlineKeyboardMarkup()
    for country in countries:
        button_country = types.InlineKeyboardButton(
            f"{country.flag} {country.name}",
            callback_data=f"remove_wallet_country_|_{country.id}")
        keyboard.add(button_country)
    keyboard.add(types.InlineKeyboardButton("Общий",
                                            callback_data="remove_wallet_country_|_O"))
    await message.answer("Выберите страну для удаления кошелька",
                         reply_markup=keyboard)


@admin_required
async def process_remove_wallet_country(callback_query: types.CallbackQuery):
    """Обработка выбора страны для удаления кошелька"""
    await callback_query.answer()
    country_id = callback_query.data.split('_|_')[-1]
    if country_id == "O":
        wallets = await get_wallets_by_wallet_type("Общий")
    else:
        wallets = await get_wallets_by_country_id(country_id)
    if not wallets:
        await callback_query.message.answer(
            "Нет кошельков для этой страны, выберите другую")
        return
    keyboard = types.InlineKeyboardMarkup()
    for wallet in wallets:
        button_remove_wallet = types.InlineKeyboardButton(wallet.name,
                                                          callback_data=f"remove_wallet_|_{wallet.id}")
        keyboard.add(button_remove_wallet)
    await callback_query.message.answer("Выберите кошелек для удаления",
                                        reply_markup=keyboard)


@admin_required
async def process_remove_wallet(callback_query: types.CallbackQuery):
    """Обработка удаления кошелька"""
    await callback_query.answer()
    wallet_id = callback_query.data.split('_|_')[-1]
    if not await get_wallet_by_id(wallet_id):
        await callback_query.message.answer("Ошибка, кошелек не найден")
        return
    if await is_wallet_balance_positive(wallet_id):
        await callback_query.message.answer(
            "Нельзя удалить кошелек с ненулевым балансом")
        return
    wallet = await get_wallet_by_id(wallet_id)
    ans = await remove_wallet_from_db(wallet_id)
    if ans is True:
        await callback_query.message.answer("Кошелек удален")
        await add_to_history(callback_query.from_user.id, "wallet",
                             f"Кошелёк '{wallet.name}' удалён пользователем {callback_query.from_user.username}")
    elif isinstance(ans, str):
        # Возвращена строка с ошибкой о балансе
        await callback_query.message.answer(ans)
    else:
        await callback_query.message.answer("Ошибка при удалении кошелька")


@admin_required
async def edit_wallet(message: types.Message):
    """Редактирование кошелька"""
    countries = await get_countries()
    wallets = await get_wallets()
    if not wallets:
        await message.answer("Нет кошельков")
        return
    await EditWalletState.waiting_for_country_id.set()
    keyboard = types.InlineKeyboardMarkup()
    for country in countries:
        button_country = types.InlineKeyboardButton(
            f"{country.flag} {country.name}",
            callback_data=f"edit_wallet_by_country_|_{country.id}")
        keyboard.add(button_country)
    keyboard.add(types.InlineKeyboardButton("Общий",
                                            callback_data="edit_wallet_by_country_|_O"))
    await message.answer("Выберите страну для редактирования кошелька",
                         reply_markup=keyboard)


@admin_required
async def process_edit_wallet_country(callback_query: types.CallbackQuery,
                                      state: FSMContext):
    """Обработка выбора страны для редактирования кошелька"""
    await callback_query.answer()
    country_id = callback_query.data.split('_|_')[-1]
    if country_id == "O":
        wallets = await get_wallets_by_wallet_type("Общий")
    else:
        wallets = await get_wallets_by_country_id(country_id)
    if not wallets:
        await callback_query.message.answer(
            "Нет кошельков для этой страны, выберите другую")
        return
    await state.update_data(country_id=country_id)
    keyboard = types.InlineKeyboardMarkup()
    for wallet in wallets:
        button_edit_wallet = types.InlineKeyboardButton(
            f"{wallet.name} | {round(wallet.get_balance(), 3)}",
            callback_data=f"edit_wallet_by_wallet_|_{wallet.id}")
        keyboard.add(button_edit_wallet)
    await callback_query.message.answer("Выберите кошелек для редактирования",
                                        reply_markup=keyboard)
    await EditWalletState.waiting_for_wallet_id.set()


@admin_required
async def process_edit_wallet(callback_query: types.CallbackQuery,
                              state: FSMContext):
    """Обработка редактирования кошелька"""
    await callback_query.answer()
    wallet_id = callback_query.data.split('_|_')[-1]
    if not await get_wallet_by_id(wallet_id):
        await callback_query.message.answer("Ошибка, кошелек не найден")
        return
    await state.update_data(wallet_id=wallet_id)
    data_wallet = await get_wallet_by_id(wallet_id)
    await callback_query.message.answer(
        f"""Кошелек: {data_wallet.name}\nСтрана: {data_wallet.country.flag + ' ' + data_wallet.country.name if data_wallet.country else "Общий"}\nБаланс: {data_wallet.get_balance()}\nВыберите действие""",
        reply_markup=edit_wallet_keyboard)
    await EditWalletState.waiting_for_action.set()


@admin_required
async def edit_balans_wallet(message: types.Message, state: FSMContext):
    """Изменение баланса кошелька"""
    await message.answer("Введите число на которое нужно изменить баланс",
                         reply_markup=cancel_editing_wallet_keyboard)
    await EditWalletState.waiting_for_new_balans.set()


@admin_required
async def process_adjustment_balans_wallet(message: types.Message,
                                           state: FSMContext):
    """Обработка сумы изменения баланса"""
    adjustment = message.text
    await state.update_data(adjustment=adjustment)

    await message.answer("Введите причину изменения баланса",
                         reply_markup=cancel_editing_wallet_keyboard)
    await EditWalletState.waiting_for_reason.set()


@admin_required
async def process_edit_balans_wallet(message: types.Message,
                                     state: FSMContext):
    """Обработка изменения баланса кошелька"""
    data = await state.get_data()
    reason = message.text
    adjustment = data.get("adjustment")
    if adjustment.count("-") > 1:
        await message.answer(
            "Изменение баланса должно быть числом, попробуйте снова")
        return
    if not is_number(adjustment):
        await message.answer(
            "Изменение баланса должно быть числом, попробуйте снова")
        return
    adjustment = float(adjustment)
    data = await state.get_data()
    wallet_id = data.get("wallet_id")
    wallet = await get_wallet_by_id(wallet_id)
    await edit_wallet_balans(wallet_id, adjustment)
    await state.finish()
    data_wallet = await get_wallet_by_id(wallet_id)
    await message.answer(
        f"Баланс кошелька изменен \nБаланс: {data_wallet.get_balance()}\nПричина: {reason}",
        reply_markup=wallets_keyboard)
    await state.finish()
    await add_to_history(message.from_user.id, "wallet",
                         f"Баланс кошелька '{wallet.name}' изменён на '{adjustment}' ({reason}) пользователем {message.from_user.username}")


@admin_required
async def edit_wallet_country(message: types.Message, state: FSMContext):
    """Выбор новой страны для кошелька"""
    countries = await get_countries()
    if not countries:
        await message.answer("Нет стран")
        await state.finish()
        return
    keyboard = types.InlineKeyboardMarkup()
    for country in countries:
        button_country = types.InlineKeyboardButton(
            f"{country.flag} {country.name}",
            callback_data=f"edit_wallet_country_new_|_{country.id}")
        keyboard.add(button_country)
    keyboard.add(types.InlineKeyboardButton("Общий",
                                            callback_data="edit_wallet_country_new_|_O"))
    keyboard.add(cancel_edit_wallet_button)
    await message.answer("Выберите новую страну для кошелька",
                         reply_markup=keyboard)

    await EditWalletState.waiting_for_new_country.set()


@admin_required
async def process_edit_wallet_country_new(callback_query: types.CallbackQuery,
                                          state: FSMContext):
    """Обработка выбора новой страны для кошелька"""
    await callback_query.answer()
    country_id = callback_query.data.split('_|_')[-1]
    if country_id == "O":
        ...
    elif not await get_country_by_id(country_id):
        await callback_query.message.answer("Ошибка, страна не найдена")
        return
    data = await state.get_data()
    wallet_id = data.get("wallet_id")
    wallet = await get_wallet_by_id(wallet_id)
    country = await get_country_by_id(country_id)
    await edit_wallet_country_by_id(wallet_id, country_id)
    await state.finish()
    wallet_data = await get_wallet_by_id(wallet_id)
    await callback_query.message.answer(
        f"Страна кошелька изменена на {wallet_data.country.flag + ' ' + wallet_data.country.name if wallet_data.country else 'Общий'}",
        reply_markup=wallets_keyboard)

    await state.finish()
    await add_to_history(callback_query.from_user.id, "wallet",
                         f"Страна кошелька '{wallet.name}' изменена на '{country.flag} {country.name}' пользователем {callback_query.from_user.username}")


@admin_required
async def cancel_editing_wallet(callback_query: types.CallbackQuery,
                                state: FSMContext):
    """Отмена редактирования кошелька"""
    await callback_query.answer()
    await state.finish()
    await callback_query.message.answer("Редактирование отменено",
                                        reply_markup=management_menu_keyboard)


@admin_required
async def transfer_money(message: types.Message, state: FSMContext):
    """Выбор операции перевода денег"""
    data = await state.get_data()
    await TransferMoneyState.waiting_for_action.set()
    await state.update_data(**data)
    await message.answer("Выберите тип операции",
                         reply_markup=transfer_wallet_keyboard)


@admin_required
async def process_transfer_from(callback_query: types.CallbackQuery,
                                state: FSMContext):
    """Обработка выбора типа баланса"""
    await callback_query.answer()
    data = await state.get_data()
    if callback_query.data == "withdraw_wallet" and data.get("wallet_id"):
        await TransferMoneyState.waiting_for_second_variant.set()
        await state.update_data(action="withdraw")

        await callback_query.message.answer("Куда переводим?",
                                            reply_markup=withdraw_wallet_keyboard)
        return

    elif callback_query.data == "replenish_wallet" and data.get("wallet_id"):
        await TransferMoneyState.waiting_for_second_variant.set()
        await state.update_data(action="replenish")
        await callback_query.message.answer("Откуда переводим?",
                                            reply_markup=replenish_wallet_keyboard)
        return

    if callback_query.data == "replenish_wallet":
        await state.update_data(action="replenish")
        await callback_query.message.answer("Что пополняем?",
                                            reply_markup=transfer_from_where_keyboard(
                                                "Баланс", "Депозит"))


    elif callback_query.data == "withdraw_wallet":
        await state.update_data(action="withdraw")
        await callback_query.message.answer("Откуда выводим?",
                                            reply_markup=transfer_from_where_keyboard(
                                                "С баланса", "С депозита"))

    await TransferMoneyState.waiting_for_from.set()


@admin_required
async def process_transfer_money(callback_query: types.CallbackQuery,
                                 state: FSMContext):
    """Обработка выбора операции"""
    await callback_query.answer()
    data = await state.get_data()

    if data.get("action") == "replenish":
        where = callback_query.data
        await state.update_data(where=where)
        await callback_query.message.answer("Откуда переводим?",
                                            reply_markup=replenish_wallet_keyboard)

    elif data.get("action") == "withdraw":
        from_ = callback_query.data
        await state.update_data(from_=from_)
        await callback_query.message.answer("Куда переводим?",
                                            reply_markup=withdraw_wallet_keyboard)

    await TransferMoneyState.waiting_for_second_variant.set()


@admin_required
async def process_choice_second_variant(callback_query: types.CallbackQuery,
                                        state: FSMContext):
    """Обработка выбора второго варианта"""
    await callback_query.answer()
    countries = await get_countries()

    keyboard = types.InlineKeyboardMarkup()
    for country in countries:
        button_country = types.InlineKeyboardButton(
            f"{country.flag} {country.name}",
            callback_data=f"transfer_country_|_{country.id}")
        keyboard.add(button_country)
    if callback_query.data == "wallet":
        await state.update_data(second_variant="wallet")
        button_general = types.InlineKeyboardButton("Общий",
                                                    callback_data="transfer_country_|_O")
        keyboard.add(button_general)
        if not await get_wallets():
            await callback_query.message.answer("Нет кошельков")
            await state.finish()
            return
    elif callback_query.data == "bk":
        if not countries:
            await callback_query.message.answer("Нет стран")
            await state.finish()
            return
        await state.update_data(second_variant="bk")
        if not await get_templates():
            await callback_query.message.answer("Нет шаблонов")
            await state.finish()
            return

    await callback_query.message.answer("Выберите страну",
                                        reply_markup=keyboard)
    await TransferMoneyState.waiting_for_second_variant_country_id.set()


@admin_required
async def process_transfer_country(callback_query: types.CallbackQuery,
                                   state: FSMContext):
    """Обработка выбора страны"""
    await callback_query.answer()
    await state.update_data(country_id=callback_query.data.split("_|_")[-1])
    data = await state.get_data()
    if data.get("second_variant") == "wallet":
        if data.get("country_id") == "O":
            wallets = await get_wallets_by_wallet_type("Общий")
        else:
            wallets = await get_wallets_by_country_id(data.get("country_id"))
        if not wallets:
            await callback_query.message.answer(
                "Нет кошельков для этой страны, выберите другую")
            return
        keyboard = types.InlineKeyboardMarkup()
        for wallet in wallets:
            button_wallet = types.InlineKeyboardButton(wallet.name,
                                                       callback_data=f"transfer_wallet_{wallet.id}")
            keyboard.add(button_wallet)
        await callback_query.message.answer("Выберите кошелек",
                                            reply_markup=keyboard)
        await TransferMoneyState.waiting_for_second_variant_id.set()
    elif data.get("second_variant") == "bk":
        bks = [
            bk for bk in (
                await get_country_by_id(data.get('country_id'))).bookmakers
            if bk.is_active
        ]
        if not bks:
            await callback_query.message.answer(
                "Нет профилей БК для этой страны")
            return
        keyboard = types.InlineKeyboardMarkup()
        for bk in bks:
            button_bk = types.InlineKeyboardButton(
                f"{bk.template.name} | {bk.name} | {round(bk.get_balance(), 3)}",
                callback_data=f"transfer_wallet_{bk.id}")
            keyboard.add(button_bk)
        await callback_query.message.answer("Выберите профиль БК",
                                            reply_markup=keyboard)
        await TransferMoneyState.waiting_for_second_variant_id.set()


@admin_required
async def process_transfer_wallet(callback_query: types.CallbackQuery,
                                  state: FSMContext):
    """Обработка выбора кошелька"""
    await callback_query.answer()
    second_variant_id = callback_query.data.split("_")[-1]
    await state.update_data(second_variant_id=second_variant_id)
    data = await state.get_data()
    if data.get("second_variant") == "wallet":
        wallet = await get_wallet_by_id(second_variant_id)
        if not wallet:
            await callback_query.message.answer("Ошибка, кошелек не найден")
            await state.finish()
            return
        # Если выбран кошелек, то сразу переходим к вводу суммы
        await callback_query.message.answer("Введите отправленную сумму",
                                            reply_markup=cancel_editing_wallet_keyboard)
        await TransferMoneyState.waiting_for_sent_sum.set()
        return


    elif data.get("second_variant") == "bk":
        bk = await get_bk_by_id(second_variant_id)
        if not bk:
            await callback_query.message.answer("Ошибка, бк не найден")
            await state.finish()
            return

        if data.get("action") == "replenish":
            await callback_query.message.answer("Откуда выводим?",
                                                reply_markup=transfer_from_where_keyboard(
                                                    "С баланса",
                                                    "С депозита"))
        elif data.get("action") == "withdraw":
            await callback_query.message.answer("Куда переводим?",
                                                reply_markup=transfer_from_where_keyboard(
                                                    "На баланс",
                                                    "На депозит"))
        await TransferMoneyState.waiting_for_where.set()


@admin_required
async def process_transfer_where(callback_query: types.CallbackQuery,
                                 state: FSMContext):
    """Обработка выбора баланс/депозит"""
    await callback_query.answer()
    data = await state.get_data()

    if data.get("action") == "replenish":
        from_ = callback_query.data
        await state.update_data(from_=from_)

    elif data.get("action") == "withdraw":
        where = callback_query.data
        await state.update_data(where=where)

    await callback_query.message.answer("Введите отправленную сумму",
                                        reply_markup=cancel_editing_wallet_keyboard)
    await TransferMoneyState.waiting_for_sent_sum.set()


@admin_required
async def process_transfer_sum(message: types.Message, state: FSMContext):
    """Обработка ввода суммы"""
    sum_ = message.text
    if not is_number(sum_):
        await message.answer("Сумма должна быть числом, попробуйте снова")
        return
    sum_ = float(sum_)
    await state.update_data(sum_=sum_)
    await message.answer("Введите полученную сумму",
                         reply_markup=cancel_editing_wallet_keyboard)
    await TransferMoneyState.waiting_for_received_sum.set()


@admin_required
async def process_transfer_received_sum(message: types.Message,
                                        state: FSMContext):
    """Обработка ввода полученной суммы"""

    if not is_number(message.text):
        await message.answer("Сумма должна быть числом, попробуйте снова")
        return

    data = await state.get_data()
    ans_text = "Ошибка при переводе"

    second_variant = data.get("second_variant")
    second_variant_id = data.get("second_variant_id")

    from_ = data.get("from_")
    where = data.get("where")

    wallet_id = data.get("wallet_id")
    wallet = await get_wallet_by_id(wallet_id)

    bk_id = data.get("bk_id")
    bk = await get_bk_by_id(bk_id)

    sum_received = float(message.text)
    sum_ = data.get("sum_")

    replenish = (True if data.get("action") == "replenish" else False)

    # Определение исходной и целевой сущностей
    source_entity = "wallet" if wallet else "bk"
    target_entity = second_variant

    # Определение источника и получателя перевода
    source_id = wallet_id if source_entity == "wallet" else bk_id
    target_id = second_variant_id if target_entity == "wallet" else second_variant_id

    # Определение параметров для создания транзакции
    sender_wallet_id = source_id if source_entity == "wallet" else None
    receiver_wallet_id = target_id if target_entity == "wallet" else None
    sender_bk_id = source_id if source_entity == "bk" else None
    receiver_bk_id = target_id if target_entity == "bk" else None

    # Определение направления перевода
    transfers_types = {
        ("wallet", "wallet"): (
            receiver_wallet_id, sender_wallet_id, None, None),
        ("bk", "bk"): (None, None, receiver_bk_id, sender_bk_id),
        ("wallet", "bk"): (None, sender_wallet_id, receiver_bk_id, None),
        ("bk", "wallet"): (receiver_wallet_id, None, None, sender_bk_id),
    }

    if replenish:
        sender_wallet_id, receiver_wallet_id, sender_bk_id, receiver_bk_id = \
            transfers_types[(source_entity, target_entity)]
        source_entity, target_entity = target_entity, source_entity
        source_id, target_id = target_id, source_id

    # Создание транзакции
    ans = await create_transaction(
        sender_wallet_id=sender_wallet_id,
        receiver_wallet_id=receiver_wallet_id,
        sender_bk_id=sender_bk_id,
        receiver_bk_id=receiver_bk_id,
        sum=sum_,
        sum_received=sum_received,
        from_=from_,
        where=where
    )

    # Формирование текста операции
    source_name = (await get_wallet_by_id(
        source_id)).name if source_entity == "wallet" else (
        await get_bk_by_id(source_id)).name
    target_name = (await get_wallet_by_id(
        target_id)).name if target_entity == "wallet" else (
        await get_bk_by_id(target_id)).name

    source_template_name = f" {(await get_bk_by_id(source_id)).template.name}" if source_entity == 'bk' else ''
    target_template_name = f" {(await get_bk_by_id(target_id)).template.name}" if target_entity == 'bk' else ''
    ans_text = f"Отправлено {sum_} с {source_entity}{source_template_name} '{source_name}' - Поступило {sum_received} на {target_entity}{target_template_name} '{target_name}' пользователем {message.from_user.username}"

    if ans:
        await message.answer("Перевод выполнен",
                             reply_markup=management_menu_keyboard)
        await add_to_history(message.from_user.id, "transfer", ans_text)

        commission = sum_ - sum_received
        direction = f"{source_entity}->{target_entity}"
        await add_to_commission_history(
            user_name=message.from_user.username,
            commission=commission,
            commission_type=f"{data.get('action')} {direction}",
            commission_description=(
                f"Комиссия {commission} "
                f"при {'пополнении' if replenish else 'переводе'} ({direction}) "
                f"с {source_entity}{source_template_name} '{source_name}' на {target_entity}{target_template_name} '{target_name}' "
                f"пользователем {message.from_user.username}"
            )
        )
    else:
        if not bk:
            ans_text = "Ошибка, бк не найден"
        elif not wallet:
            ans_text = "Ошибка, кошелёк не найден"
        await message.answer(ans_text, reply_markup=management_menu_keyboard)

    await state.finish()


"""СОЗДАНИЕ ОТЧЕТОВ"""


@admin_required
async def create_report(message: types.Message):
    await AddingReportState.waiting_for_report_file.set()
    cancel_add_report_button = types.InlineKeyboardButton("Отмена",
                                                          callback_data="cancel_add_report")
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(cancel_add_report_button)
    await message.answer("Пожалуйста, загрузите файл excel для отчета",
                         reply_markup=keyboard)


@admin_required
async def process_report_file(message: types.Message, state: FSMContext):
    # проверяем что в сообщении есть документ
    if not message.document:
        await message.answer("Пожалуйста, загрузите файл excel для отчета")
        return
    # скачивание файла и обработка process_excel_file
    file_id = message.document.file_id
    file_info = await message.bot.get_file(file_id)
    file_path = file_info.file_path

    # Получение имени файла
    file_name = message.document.file_name
    if not file_name.endswith('.xlsx'):
        await message.answer("Файл должен быть формата .xlsx")
        return

    # делаем уникальное имя файла
    file_name = file_name.replace(".xlsx", "") + file_id + ".xlsx"
    dir_path = 'reports_folder'

    # Создание папки для сохранения файла
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    # Создание пути для сохранения файла
    destination_path = os.path.join(dir_path, file_name)

    await message.bot.download_file(file_path, destination=destination_path)

    ans = await process_excel_file(destination_path)
    if ans:
        await message.answer("Файл excel обработан.")
        await add_to_history(message.from_user.id, "report",
                             f"Создан отчет пользователем {message.from_user.username}")
    else:
        with open('errors.xlsx', 'rb') as file:
            await message.bot.send_document(message.chat.id,
                                            file,
                                            caption="В вашем файле найдены ошибки. Пожалуйста, исправьте их в этом файле и отправьте снова.")
            await add_to_history(message.from_user.id, "report",
                                 f"Найдены ошибки при создании отчета пользователем {message.from_user.username}")
    await state.finish()


@admin_required
async def cancel_add_report(callback_query: types.CallbackQuery,
                            state: FSMContext):
    await callback_query.answer()
    await state.finish()
    await callback_query.message.answer("Добавление отчета отменено")


"""УПРАВЛЕНИЯ МАТЧАМИ"""


async def matches_management(message: types.Message):
    await message.answer("Управление матчами",
                         reply_markup=matches_management_keyboard)


async def link_to_check_reports(message: types.Message):
    access_token = await get_token(message.from_user.id)
    await message.answer(
        f"[Проверка отчётов \(ссылка\)](https://ibet.team:6201/login?token={access_token}&to=1)",
        reply_markup=matches_management_keyboard,
        parse_mode=ParseMode.MARKDOWN_V2
    )


async def list_not_named_matches(message: types.Message):
    texted_matches = '\n'.join([
        f"`{m.id}`" for m in (await get_matches())
        if not m.name and m.is_active]
    )

    text = (
        "IDшники без названия матча:\n"
        f"{texted_matches}"
    )

    await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)


async def create_new_match(message: types.Message):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Отмена", callback_data="cancel_add_match"))

    await message.answer("Введите id матча",
                         reply_markup=keyboard)

    await AddingMatch.waiting_match_id.set()


async def create_match_id_process(message: types.Message,
                                  state: FSMContext):
    match_id = message.text
    match = await get_match(match_id)

    if not match:
        await message.answer(f"Матч с id {match_id} не найден")
        await state.finish()
        return

    await state.update_data(match_id=message.text)

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Отмена", callback_data="cancel_add_match"))

    await message.answer(
        text=(
            "Введите имя матча\n"
            "```Имя\n"
            f"{match.name}\n"
            "```"
        ),
        reply_markup=keyboard,
        parse_mode="MARKDOWN"
    )

    await AddingMatch.waiting_match_name.set()


async def create_match_name_process(message: types.Message,
                                    state: FSMContext):
    data = await state.get_data()

    match_name = message.text
    match_id = data.get("match_id")

    match = await get_match(match_id)
    existed_match = await Match.get(name=match_name, canonical_id=None)

    if existed_match:
        await match.update(name=match_name, canonical_id=existed_match.id)
    else:
        await update_match_name(match_id=match_id, match_name=match_name)

    await message.answer("Имя матча изменено")
    await add_to_history(message.from_user.username, "match",
                         f"Задано имя {match_name} для матча с id {match_id} пользователем {message.from_user.username}")

    await state.finish()


async def cancel_add_match(callback_query: types.CallbackQuery,
                           state: FSMContext):
    await callback_query.answer()
    await state.finish()
    await callback_query.message.answer("Изменение имени матча отменено")


"""РЕГИСТРАЦИЯ ХЭНДЛЕРОВ"""


def register_matches_handlers(dp):
    """УПРАВЛЕНИЯ МАТЧАМИ"""
    dp.register_message_handler(matches_management, lambda
                                message: message.text == "Матчи")

    dp.register_message_handler(link_to_check_reports, lambda
                                message: message.text == "Проверить отчёты")

    dp.register_message_handler(list_not_named_matches, lambda
                                message: message.text == "Список ID без имён")

    dp.register_message_handler(create_new_match, lambda
                                message: message.text == "Установить имя матча")
    dp.register_message_handler(create_match_id_process,
                                state=AddingMatch.waiting_match_id)
    dp.register_message_handler(create_match_name_process,
                                state=AddingMatch.waiting_match_name)

    dp.register_callback_query_handler(cancel_add_match, lambda
                                       c: c.data == "cancel_add_match",
                                       state="*")


def register_reports_handlers(dp):
    """СОЗДАНИЕ ОТЧЕТОВ"""
    dp.register_message_handler(create_report, lambda
                                message: message.text == "📝 Сделать отчет")
    dp.register_message_handler(process_report_file,
                                state=AddingReportState.waiting_for_report_file,
                                content_types=types.ContentType.DOCUMENT)
    dp.register_callback_query_handler(cancel_add_report, lambda
        c: c.data == "cancel_add_report", state="*")


def register_wallets_handlers(dp):
    """УПРАВЛЕНИЕ КОШЕЛЬКАМИ"""
    dp.register_message_handler(wallets_management, lambda
                                message: message.text == "💳 Управление кошельками")
    dp.register_message_handler(add_wallet, lambda
                                message: message.text == "💳 Добавить кошелек")
    dp.register_message_handler(process_wallet_name,
                                state=AddingWalletState.waiting_for_wallet_name)
    dp.register_callback_query_handler(add_binance_wallet, lambda
        c: c.data == "add_binance_wallet",
                                       state=AddingWalletState.waiting_for_general_type)
    dp.register_callback_query_handler(add_card_wallet,
                                       lambda c: c.data == "add_card_wallet",
                                       state=AddingWalletState.waiting_for_general_type)
    dp.register_callback_query_handler(select_country_wallet,
                                       lambda c: c.data == "select_country",
                                       state=AddingWalletState.waiting_for_type)
    dp.register_callback_query_handler(process_add_wallet_by_country,
                                       lambda c: c.data.startswith(
                                           'add_wallet_by_country'),
                                       state=AddingWalletState.waiting_for_country_id)
    dp.register_callback_query_handler(enter_deposit,
                                       lambda c: c.data == "enter_deposit",
                                       state=[
                                           AddingWalletState.waiting_for_type,
                                           AddingWalletState.waiting_for_country_id])
    dp.register_message_handler(process_deposit,
                                state=AddingWalletState.waiting_for_wallet_deposit)
    dp.register_callback_query_handler(cancel_adding_wallet, lambda
        c: c.data == "cancel_adding_wallet", state="*")
    dp.register_message_handler(return_to_wallet_management, lambda
        message: message.text == "В меню кошельков", state="*")
    dp.register_message_handler(delite_wallet, lambda
        message: message.text == "💳 Удалить кошелек")
    dp.register_callback_query_handler(process_remove_wallet_country,
                                       lambda c: c.data.startswith(
                                           'remove_wallet_country'))
    dp.register_callback_query_handler(process_remove_wallet,
                                       lambda c: c.data.startswith(
                                           'remove_wallet'))
    dp.register_message_handler(edit_wallet, lambda
                                message: message.text == "💳 Изменить кошелек")
    dp.register_callback_query_handler(process_edit_wallet_country,
                                       lambda c: c.data.startswith(
                                           'edit_wallet_by_country_|_'),
                                       state=EditWalletState.waiting_for_country_id)

    dp.register_callback_query_handler(process_edit_wallet,
                                       lambda c: c.data.startswith(
                                           'edit_wallet_by_wallet'),
                                       state=EditWalletState.waiting_for_wallet_id)

    dp.register_message_handler(edit_balans_wallet, lambda
                                message: message.text == "Изменить баланс",
                                state=EditWalletState.waiting_for_action)
    dp.register_message_handler(process_adjustment_balans_wallet,
                                state=EditWalletState.waiting_for_new_balans)
    dp.register_message_handler(process_edit_balans_wallet,
                                state=EditWalletState.waiting_for_reason)
    dp.register_message_handler(edit_wallet_country, lambda
                                message: message.text == "Изменить страну",
                                state=EditWalletState.waiting_for_action)
    dp.register_callback_query_handler(process_edit_wallet_country_new,
                                       lambda c: c.data.startswith(
                                           "edit_wallet_country_new_|_"),
                                       state=EditWalletState.waiting_for_new_country)
    dp.register_callback_query_handler(cancel_editing_wallet, lambda
        c: c.data == "cancel_editing_wallet", state="*")

    dp.register_message_handler(edit_wallet_country, lambda
                                message: message.text == "Изменить страну",
                                state=EditWalletState.waiting_for_action)

    dp.register_message_handler(transfer_money, lambda
                                message: message.text == "Переводы и выводы",
                                state=EditWalletState.waiting_for_action)
    dp.register_callback_query_handler(process_transfer_from, lambda
                                       c: c.data == "replenish_wallet" or c.data == "withdraw_wallet",
                                       state=TransferMoneyState.waiting_for_action)
    dp.register_callback_query_handler(process_transfer_money, lambda
                                       c: c.data == "balance" or c.data == "deposit",
                                       state=TransferMoneyState.waiting_for_from)
    dp.register_callback_query_handler(process_choice_second_variant, lambda
                                       c: c.data == "wallet" or c.data == "bk",
                                       state=TransferMoneyState.waiting_for_second_variant)
    dp.register_callback_query_handler(process_transfer_country, lambda
                                       c: c.data.startswith('transfer_country'),
                                       state=TransferMoneyState.waiting_for_second_variant_country_id)
    dp.register_callback_query_handler(process_transfer_wallet,
                                       lambda c: c.data.startswith(
                                           'transfer_wallet'),
                                       state=TransferMoneyState.waiting_for_second_variant_id)
    dp.register_callback_query_handler(process_transfer_where,
                                       lambda
                                           c: c.data == "balance" or c.data == "deposit",
                                       state=TransferMoneyState.waiting_for_where)
    dp.register_message_handler(process_transfer_sum,
                                state=TransferMoneyState.waiting_for_sent_sum)
    dp.register_message_handler(process_transfer_received_sum,
                                state=TransferMoneyState.waiting_for_received_sum)


def register_bk_management_handlers(dp):
    """УПРАВЛЕНИЕ БК"""
    dp.register_callback_query_handler(cancel_adding_bk,
                                       lambda c: c.data == 'cancel_adding_bk',
                                       state="*")
    dp.register_callback_query_handler(confirm_delete_bk, lambda
        c: c.data == "confirm_delete_bk", state="waiting_delete_confirmation")
    dp.register_callback_query_handler(cancel_delete_bk,
                                       lambda c: c.data == "cancel_delete_bk",
                                       state="waiting_delete_confirmation")

    dp.register_message_handler(bk_management, lambda
        message: message.text == "🏦 Управление БК")
    dp.register_message_handler(add_bk_country, lambda
        message: message.text == "🏦 Добавить БК")
    dp.register_callback_query_handler(add_bk_by_template,
                                       lambda c: c.data.startswith(
                                           'add_bk_by_country'))

    dp.register_callback_query_handler(process_add_bk_by_template,
                                       lambda c: c.data.startswith(
                                           'add_bk_by_template'))
    dp.register_message_handler(process_add_bk_by_all_info,
                                state=AddingBkState.waiting_for_profile_name)
    dp.register_message_handler(edit_bk_country, lambda
        message: message.text == "🏦 Изменить данные БК")
    dp.register_callback_query_handler(edit_bk_by_country,
                                       lambda c: c.data.startswith(
                                           'edit_bk_by_country'))
    dp.register_callback_query_handler(cancel_editing_bk, lambda
        c: c.data == 'cancel_editing_bk', state="*")
    dp.register_callback_query_handler(process_edit_bk_by_profile,
                                       lambda c: c.data.startswith(
                                           'edit_bk_by_profile'))
    dp.register_callback_query_handler(edit_bk_balance,
                                       lambda c: c.data.startswith(
                                           'edit_bk_balance'),
                                       state=EditBkState.waiting_for_action)
    dp.register_callback_query_handler(process_bk_balance_choice,
                                       lambda c: c.data.startswith(
                                           'bk_balance_choice'),
                                       state=EditBkState.waiting_for_balance_choice)
    dp.register_message_handler(process_bk_balance_amount,
                                state=EditBkState.waiting_for_balance_amount)
    dp.register_message_handler(process_bk_balance_reason,
                                state=EditBkState.waiting_for_balance_reason)
    dp.register_callback_query_handler(edit_profile_name,
                                       lambda c: c.data.startswith(
                                           'edit_profile_name'),
                                       state=EditBkState.waiting_for_action)
    dp.register_callback_query_handler(edit_profile_percentage,
                                       lambda c: c.data.startswith(
                                           'edit_profile_percentage'),
                                       state=EditBkState.waiting_for_action)
    dp.register_callback_query_handler(deactivate_profile,
                                       lambda c: c.data.startswith(
                                           'deactivate_profile'),
                                       state=EditBkState.waiting_for_action)
    dp.register_callback_query_handler(activate_profile,
                                       lambda c: c.data.startswith(
                                           'activate_profile'),
                                       state=EditBkState.waiting_for_action)
    dp.register_callback_query_handler(delite_profile,
                                       lambda c: c.data.startswith(
                                           'delite_profile'),
                                       state=EditBkState.waiting_for_action)
    dp.register_message_handler(process_edit_profile_percentage_percentage,
                                state=EditBkState.waiting_for_percent)
    dp.register_message_handler(process_edit_profile_name,
                                state=EditBkState.waiting_for_profile_name)
    dp.register_callback_query_handler(transfer_money_from_bk,
                                       lambda c: c.data.startswith(
                                           "transfer_money_from_bk"),
                                       state=EditBkState.waiting_for_action)


def register_employee_handlers(dp):
    """УПРАВЛЕНИЕ СОТРУДНИКАМИ"""

    dp.register_message_handler(employee_list, lambda
        message: message.text == "Список сотрудников")
    dp.register_callback_query_handler(process_confirm_callback,
                                       lambda c: c.data.startswith(
                                           'confirm_user_'))
    dp.register_callback_query_handler(process_reject_callback,
                                       lambda c: c.data.startswith(
                                           'reject_user_'))
    dp.register_callback_query_handler(show_admin_creation_keyboard,
                                       lambda
                                           c: c.data == 'show_admin_creation_keyboard')
    dp.register_callback_query_handler(display_admin_removal_options,
                                       lambda
                                           c: c.data == 'display_admin_removal_options')
    dp.register_callback_query_handler(make_admin_callback,
                                       lambda c: c.data.startswith(
                                           'make_admin'))
    dp.register_callback_query_handler(remove_admin_callback,
                                       lambda c: c.data.startswith(
                                           'remove_admin'))
    dp.register_message_handler(employee_admin_management,
                                lambda
                                    message: message.text == "👨‍💻 Управление сотрудниками"
                                             or message.text == "В меню сотрудников")
    dp.register_message_handler(admin_management,
                                lambda message: message.text == "Админы")
    dp.register_message_handler(employee_management,
                                lambda
                                    message: message.text == "👨‍💻 Сотрудники")
    dp.register_message_handler(show_admin_creation_keyboard,
                                lambda
                                    message: message.text == "Добавить админа")
    dp.register_message_handler(display_admin_removal_options,
                                lambda
                                    message: message.text == "Удалить админа")
    dp.register_message_handler(main, lambda
        message: message.text == "В Админ-меню", state="*")
    dp.register_message_handler(cmd_view_waiting_users,
                                lambda
                                    message: message.text == "Ожидают принятия")
    dp.register_message_handler(employee_remove_keyboard,
                                lambda
                                    message: message.text == "Удалить сотрудника")
    dp.register_callback_query_handler(remove_employee_callback,
                                       lambda c: c.data.startswith(
                                           'remove_employee'))


def register_source_handlers(dp):
    """УПРАВЛЕНИЕ ИСТОЧНИКАМИ"""
    dp.register_message_handler(remove_source, lambda
        message: message.text == "Удалить источник")
    dp.register_callback_query_handler(process_remove_source,
                                       lambda c: c.data.startswith(
                                           'remove_source'))
    dp.register_message_handler(untie_source, lambda
        message: message.text == "Отвязать источник")
    dp.register_callback_query_handler(process_untie_source,
                                       lambda c: c.data.startswith(
                                           "untie_source"))
    dp.register_message_handler(add_source, lambda
        message: message.text == "Добавить источник")
    dp.register_message_handler(process_add_source,
                                state=AddingSourceState.waiting_for_source_name)
    dp.register_callback_query_handler(cancel_adding_source, lambda
        c: c.data == 'cancel_adding_source',
                                       state=AddingSourceState.waiting_for_source_name)
    dp.register_message_handler(manage_sources, lambda
        message: message.text == "📞 Управление источниками")
    dp.register_message_handler(management_menu, lambda
        message: message.text == "В меню-управления" or message.text == "Управление",
                                state="*")


def register_country_handlers(dp):
    """УПРАВЛЕНИЕ СТРАНАМИ"""
    dp.register_message_handler(country_management, lambda
        message: message.text == "🌎 Управление странами")
    dp.register_callback_query_handler(process_remove_country,
                                       lambda c: c.data.startswith(
                                           'remove_country_|_'))
    dp.register_message_handler(add_country, lambda
        message: message.text == "🌎 Добавить страну")

    dp.register_message_handler(remove_country, lambda
        message: message.text == "🌎 Удалить страну")

    dp.register_message_handler(process_add_country,
                                state=AddingCountryState.waiting_for_country_name)
    dp.register_callback_query_handler(cancel_adding_country, lambda
        c: c.data == 'cancel_adding_country',
                                       state=AddingCountryState.waiting_for_country_name)
    dp.register_message_handler(process_add_country_flag,
                                state=AddingCountryState.waiting_for_country_flag)


def register_template_handlers(dp):
    """УПРАВЛЕНИЕ ШАБЛОНАМИ БК"""
    dp.register_message_handler(templates_management, lambda
        message: message.text == "📄 Управление шаблонами")
    dp.register_callback_query_handler(process_remove_template,
                                       lambda c: c.data.startswith(
                                           'remove_template_|_'))
    dp.register_message_handler(add_template, lambda
        message: message.text == "Добавить шаблон", state="*")
    dp.register_message_handler(remove_template, lambda
        message: message.text == "Удалить шаблон")
    dp.register_message_handler(process_add_template_name,
                                state=AddingTemplateState.waiting_for_template_name)
    dp.register_message_handler(process_add_template_percent,
                                state=AddingTemplateState.waiting_for_template_percent)
    dp.register_callback_query_handler(cancel_adding_template, lambda
        c: c.data == 'cancel_adding_template', state='*')
    dp.register_callback_query_handler(countries_adding_template,
                                       lambda c: c.data.startswith(
                                           'add_template_|_'), state='*')
    dp.register_callback_query_handler(process_remove_template_country, lambda
        c: c.data.startswith('remove_template_country'))


def register_admin_handlers(dp):
    register_template_handlers(dp)
    register_employee_handlers(dp)
    register_source_handlers(dp)
    register_country_handlers(dp)
    register_bk_management_handlers(dp)
    register_wallets_handlers(dp)
    register_reports_handlers(dp)
    register_matches_handlers(dp)
