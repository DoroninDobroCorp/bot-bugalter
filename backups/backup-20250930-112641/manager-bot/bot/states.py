from aiogram.dispatcher.filters.state import StatesGroup, State


class AddingSourceState(StatesGroup):
    waiting_for_source_name = State()


class AddingCountryState(StatesGroup):
    waiting_for_country_name = State()
    waiting_for_country_flag = State()


class AddingTemplateState(StatesGroup):
    waiting_for_template_name = State()
    waiting_for_template_percent = State()


class AddingBkState(StatesGroup):
    waiting_for_profile_name = State()


class EditBkState(StatesGroup):
    waiting_for_profile_name = State()
    waiting_for_percent = State()
    waiting_for_action = State()
    waiting_for_balance_choice = State()
    waiting_for_balance_amount = State()
    waiting_for_balance_reason = State()


class AddingWalletState(StatesGroup):
    waiting_for_wallet_name = State()
    waiting_for_wallet_deposit = State()
    waiting_for_type = State()
    waiting_for_general_type = State()
    waiting_for_country_id = State()


class EditWalletState(StatesGroup):
    waiting_for_country_id = State()
    waiting_for_wallet_id = State()
    waiting_for_action = State()
    waiting_for_reason = State()
    waiting_for_new_balans = State()
    waiting_for_new_country = State()


class TransferMoneyState(StatesGroup):
    waiting_for_second_wallet_id = State()
    waiting_for_action = State()
    waiting_for_from = State()
    waiting_for_second_variant = State()
    waiting_for_where = State()
    waiting_for_sent_sum = State()
    waiting_for_received_sum = State()
    waiting_for_second_variant_id = State()
    waiting_for_second_variant_country_id = State()
    waiting_for_type_operation = State()
    waiting_for_second_variant_template_id = State()


class AddingReportState(StatesGroup):
    waiting_for_report_file = State()


class StatisticsStates(StatesGroup):
    period_input = State()
    source_stats = State()
    source_start_date = State()
    source_end_date = State()
    report_period = State()
    report_source = State()
    report_details = State()
    country_stats = State()
    country_start_date = State()
    country_end_date = State()
    employee_stats = State()
    employee_salary = State()
    employee_stats_variant = State()
    employee_wait_action = State()
    report_excel_period = State()
    delete_report = State()
    history_excel_period = State()
    commissions_excel_period = State()


class UserStates(StatesGroup):
    waiting_for_period = State()
    waiting_for_report_number = State()


class AddingMatch(StatesGroup):
    waiting_match_name = State()
    waiting_match_id = State()
