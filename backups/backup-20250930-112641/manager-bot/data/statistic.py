from sqlalchemy import select, func, and_, case
from sqlalchemy.orm import selectinload
from dataclasses import dataclass
from data.utils import *
from datetime import timedelta, datetime
# Explicitly import models to ensure names are present in this module's globals
from data.models import Report, Bookmaker, Transaction, Source, Country, Wallet


@dataclass
class TotalStats:
    total_bet: float
    total_profit: float
    total_salary: float


async def get_total_stats_by_period(start_date: datetime.date,
                                    end_date: datetime.date) -> TotalStats:
    async with session_scope() as session:
        salary_pct = case(
            (Report._salary_percentage.isnot(None), Report._salary_percentage),
            else_=Bookmaker.salary_percentage
        )
        query = (
            select(
                func.sum(Report.bet_amount).label('total_bet'),
                func.sum(Report.return_amount - Report.bet_amount).label(
                    'total_profit'),
                func.sum(
                    case(
                        (Report.is_error == False,
                         (Report.bet_amount * salary_pct) / 100),
                        else_=0
                    )
                ).label('total_salary'),
                func.sum(
                    case(
                        (and_(Report.is_error == True,
                              Report.return_amount - Report.bet_amount < 0),
                         (func.abs(Report.return_amount - Report.bet_amount) * 3 * salary_pct) / 100),
                        else_=0
                    )
                ).label('total_penalty')
            )
            .select_from(Report.__table__.join(Bookmaker.__table__,
                                               Report.bookmaker_id == Bookmaker.id))
            .where(Report.date >= start_date)
            .where(Report.date < end_date + timedelta(days=1),
                   Report.is_deleted == False,
                   Report.is_admin_checked == True)
        )

        result = await session.execute(query)
        row = result.first()

        total_bet = row.total_bet or 0
        total_profit = row.total_profit or 0
        total_salary = row.total_salary or 0
        total_penalty = row.total_penalty or 0

    return TotalStats(
        total_bet=total_bet,
        total_profit=total_profit,
        total_salary=total_salary - total_penalty
    )


async def get_total_balances():
    async with session_scope() as session:
        # Eager-load everything needed to compute balances without extra queries after session closes
        countries = (
            await session.execute(
                select(Country)
                .options(
                    selectinload(Country.bookmakers)
                        .selectinload(Bookmaker.transactions_sender),
                    selectinload(Country.bookmakers)
                        .selectinload(Bookmaker.transactions_receiver),
                    selectinload(Country.bookmakers)
                        .selectinload(Bookmaker.reports),
                    selectinload(Country.wallets)
                        .selectinload(Wallet.transactions_sender),
                    selectinload(Country.wallets)
                        .selectinload(Wallet.transactions_receiver),
                )
            )
        ).scalars().unique().all()

        # Filter by is_deleted in Python
        countries = [c for c in countries if not c.is_deleted]

        # Collect all bookmakers and wallets from loaded countries
        all_bookmakers = []
        wallets = []
        for c in countries:
            all_bookmakers.extend([bk for bk in c.bookmakers if not bk.is_deleted])
            wallets.extend([w for w in c.wallets if not w.is_deleted])

        # Use only active bookmakers for main statistics (per ТЗ: deactivated BK should not appear)
        bookmakers = [bk for bk in all_bookmakers if bk.is_active]

    # Now compute balances using preloaded relationships
    total_balance = sum(c.get_active_balance() for c in countries)
    total_bookmaker_balance = sum(b.get_balance() for b in bookmakers)
    total_active_bookmaker_balance = sum(
        b.get_balance() for b in bookmakers if b.is_active)
    total_wallet_balance = sum(w.get_balance() for w in wallets)

    return {
        'total_balance': total_balance,
        'total_bookmaker_balance': total_bookmaker_balance,
        'total_active_bookmaker_balance': total_active_bookmaker_balance,
        'total_wallet_balance': total_wallet_balance,
        'countries': countries,
        'bookmakers': bookmakers,
        'wallets': wallets
    }


async def get_country_stats_by_id(country_id):
    country = await Country.get(id=country_id)
    if not country:
        return None

    today = datetime.today().date()
    month_start = datetime(today.year, today.month, 1).date()
    week_start = today - timedelta(days=today.weekday())

    filters = [Report.country_id == country_id, Report.is_deleted == False, Report.is_admin_checked == True]

    reports = await Report.filter(*filters)
    # For overall country stats (no explicit period), load all transactions for the country
    transactions = await Transaction.filter(
        Transaction.country_id == country_id,
        Transaction.is_deleted == False
    )

    total_bet = sum(r.bet_amount for r in reports)
    total_profit = sum(r.real_profit for r in reports)
    total_expenses = sum(t.real_amount for t in transactions)
    total_salary = sum(r.real_salary for r in reports)

    month_bet = sum(
        r.bet_amount for r in reports if r.date.date() >= month_start)
    month_profit = sum(
        r.real_profit for r in reports if r.date.date() >= month_start)
    month_expenses = sum(
        t.real_amount for t in transactions if t.timestamp and t.timestamp.date() >= month_start)
    month_salary = sum(
        r.real_salary for r in reports if r.date.date() >= month_start)

    week_bet = sum(
        r.bet_amount for r in reports if r.date.date() >= week_start)
    week_profit = sum(
        r.real_profit for r in reports if r.date.date() >= week_start)
    week_expenses = sum(
        t.real_amount for t in transactions if t.timestamp and t.timestamp.date() >= week_start)
    week_salary = sum(
        r.real_salary for r in reports if r.date.date() >= week_start)

    day_bet = sum(r.bet_amount for r in reports if r.date.date() == today)
    day_profit = sum(r.real_profit for r in reports if r.date.date() == today)
    day_expenses = sum(
        t.real_amount for t in transactions if t.timestamp and t.timestamp.date() == today)
    day_salary = sum(r.real_salary for r in reports if r.date.date() == today)

    return {
        'country': country,
        'balance': country.get_balance(),
        'active_balance': country.get_active_balance(),
        'total_bet': total_bet,
        'total_profit': total_profit,
        'total_expenses': total_expenses,
        'total_salary': total_salary,
        'month_bet': month_bet,
        'month_profit': month_profit,
        'month_expenses': month_expenses,
        'month_salary': month_salary,
        'week_bet': week_bet,
        'week_profit': week_profit,
        'week_expenses': week_expenses,
        'week_salary': week_salary,
        'day_bet': day_bet,
        'day_profit': day_profit,
        'day_expenses': day_expenses,
        'day_salary': day_salary
    }


async def get_country_stats_by_period(country_id, start_date=None,
                                      end_date=None):
    country = await Country.get(id=country_id)
    if not country:
        return None

    filters = [Report.country_id == country_id, Report.is_deleted == False, Report.is_admin_checked == True]
    if start_date and end_date:
        filters.append(
            and_(Report.date >= start_date,
                 Report.date < end_date + timedelta(days=1)))

    reports = await Report.filter(*filters)
    # Filter transactions by period using timestamp
    transactions = await Transaction.filter(
        Transaction.country_id == country_id,
        Transaction.is_deleted == False,
        Transaction.timestamp >= start_date,
        Transaction.timestamp < end_date + timedelta(days=1)
    )

    total_bet = sum(r.bet_amount for r in reports)
    total_profit = sum(r.real_profit for r in reports)
    total_expenses = sum(t.real_amount for t in transactions)
    total_salary = sum(r.real_salary for r in reports)

    return {
        "start_date": start_date,
        "end_date": end_date,
        'country': country,
        "balance": country.get_balance(),
        'active_balance': country.get_active_balance(),
        'total_bet': total_bet,
        'total_profit': total_profit,
        'total_expenses': total_expenses,
        'total_salary': total_salary
    }


async def get_bookmaker_stats_by_id(bookmaker_id):
    bookmaker = await get_bk_by_id(bookmaker_id)
    if not bookmaker:
        return None

    today = datetime.today().date()
    month_start = datetime(today.year, today.month, 1).date()
    week_start = today - timedelta(days=today.weekday())

    async with session_scope() as session:
        query = (
            select(
                func.count(Report.id).label('total_reports'),
                func.sum(Report.bet_amount).label('total_bet'),
                func.sum(Report.return_amount).label('total_return'),
                func.sum(Report.return_amount - Report.bet_amount).label('total_profit'),
                func.count(case((Report.date >= month_start, Report.id))).label('month_reports'),
                func.sum(case((Report.date >= month_start, Report.bet_amount))).label('month_bet'),
                func.sum(case((Report.date >= month_start, Report.return_amount))).label('month_return'),
                func.sum(case((Report.date >= month_start, Report.return_amount - Report.bet_amount))).label(
                    'month_profit'),
                func.count(case((Report.date >= week_start, Report.id))).label('week_reports'),
                func.sum(case((Report.date >= week_start, Report.bet_amount))).label('week_bet'),
                func.sum(case((Report.date >= week_start, Report.return_amount))).label('week_return'),
                func.sum(case((Report.date >= week_start, Report.return_amount - Report.bet_amount))).label(
                    'week_profit'),
                func.count(case((Report.date == today, Report.id))).label('day_reports'),
                func.sum(case((Report.date == today, Report.bet_amount))).label('day_bet'),
                func.sum(case((Report.date == today, Report.return_amount))).label('day_return'),
                func.sum(case((Report.date == today, Report.return_amount - Report.bet_amount))).label('day_profit')
            )
            .join(Bookmaker, Report.bookmaker_id == Bookmaker.id)
            .where(Report.bookmaker_id == bookmaker.id)
            .where(Report.is_admin_checked == True)
            .where(Report.is_deleted == False)  # Filtering by is_deleted
        )
        result = await session.execute(query)
        stats = result.fetchone()

    return {
        'bookmaker': bookmaker,
        'deposit': bookmaker.get_deposit(),
        'balance': bookmaker.get_balance(),
        'total_reports': stats.total_reports,
        'total_bet': stats.total_bet,
        'total_return': stats.total_return,
        'total_profit': stats.total_profit,
        'month_reports': stats.month_reports,
        'month_bet': stats.month_bet,
        'month_return': stats.month_return,
        'month_profit': stats.month_profit,
        'week_reports': stats.week_reports,
        'week_bet': stats.week_bet,
        'week_return': stats.week_return,
        'week_profit': stats.week_profit,
        'day_reports': stats.day_reports,
        'day_bet': stats.day_bet,
        'day_return': stats.day_return,
        'day_profit': stats.day_profit
    }


async def get_source_stats_data(source_id, start_date, end_date):
    source = await Source.get(id=source_id)
    if not source:
        return None

    async with session_scope() as session:
        salary_pct = case(
            (Report._salary_percentage.isnot(None), Report._salary_percentage),
            else_=Bookmaker.salary_percentage
        )
        query = (
            select(
                func.sum(Report.bet_amount).label('total_bet'),
                func.sum(Report.return_amount).label('total_return'),
                func.sum(Report.return_amount - Report.bet_amount).label(
                    'total_profit'),
                func.sum(
                    case(
                        (Report.is_error == False,
                         (Report.bet_amount * salary_pct) / 100),
                        else_=0
                    )
                ).label('total_salary'),
                func.sum(
                    case(
                        (and_(Report.is_error == True,
                              Report.return_amount - Report.bet_amount < 0),
                         (func.abs(Report.return_amount - Report.bet_amount) * 3 * salary_pct) / 100),
                        else_=0
                    )
                ).label('total_penalty')
            )
            .join(Bookmaker, Report.bookmaker_id == Bookmaker.id)
            .where(
                and_(
                    Report.source_id == source_id,
                    Report.date >= start_date,
                    Report.date < end_date + timedelta(days=1),
                    Report.is_admin_checked == True,
                    Report.is_deleted == False
                )
            )
        )

        result = await session.execute(query)
        stats = result.fetchone()

        if stats is None or all(value is None for value in stats):
            return {
                "start_date": start_date,
                "end_date": end_date,
                'source': source,
                'total_bet': 0,
                'total_return': 0,
                'total_profit': 0,
                'total_salary': 0
            }

        return {
            "start_date": start_date,
            "end_date": end_date,
            'source': source,
            'total_bet': stats.total_bet or 0,
            'total_return': stats.total_return or 0,
            'total_profit': stats.total_profit or 0,
            'total_salary': (stats.total_salary or 0) - (
                    stats.total_penalty or 0)
        }


async def salary_stats():
    employees = await get_employees()
    total_salary = 0

    for employee in employees:
        total_salary += await employee.get_balance()

    return {
        'total_salary': total_salary,
        'employees': employees
    }


async def get_employee_stats_by_id(employee_id):
    employee = await get_employee(employee_id)
    if not employee:
        return None

    empl_balance = await employee.get_balance()

    return {
        'employee': employee,
        'salary': empl_balance
    }


async def get_reports_by_period(start_date, end_date, source_id=None, include_unconfirmed=False):
    """
    Получает отчеты за период.
    Параметр include_unconfirmed определяет, включать ли неподтвержденные отчеты.
    По умолчанию (для статистики) включаем только подтвержденные (is_admin_checked=True).
    Для выгрузки в Excel ставим include_unconfirmed=True, чтобы включить ВСЕ отчеты.
    """
    filters = [and_(Report.date >= start_date,
                    Report.date < end_date + timedelta(days=1),
                    Report.is_deleted == False)]
    
    # Если не нужны неподтвержденные, добавляем фильтр is_admin_checked
    if not include_unconfirmed:
        filters.append(Report.is_admin_checked == True)
    
    if source_id:
        filters.append(Report.source_id == source_id)

    async with session_scope() as session:
        query = (
            select(Report)
            .where(and_(*filters))
            .options(
                selectinload(Report.employees),
                selectinload(Report.source),
                selectinload(Report.country),
                selectinload(Report.bookmaker).selectinload(Bookmaker.template),
                selectinload(Report.match)
            )
            .order_by(Report.date)
        )
        result = await session.execute(query)
        reports = result.scalars().unique().all()

    return reports


async def format_balance_stats(stats):
    today = datetime.today().strftime('%d.%m.%Y')
    country_output = f"Период: по состоянию на {today}\n\n"
    country_output += "🏦 Общий баланс в бизнесе - {:.2f} EUR\n\n".format(
        stats["total_balance"])
    # For countries total, show sum of all country balances (BK + wallets) per ТЗ
    total_countries_balance = sum(c.get_active_balance() for c in stats["countries"])
    country_output += "🌎 Страны ({}) - {:.2f} EUR\n\n".format(len(stats["countries"]),
                                                              total_countries_balance)
    for country in sorted(stats["countries"], key=lambda c: c.name):
        # Show country active balance (BK + wallets) first, then auxiliary value in brackets
        country_output += "- {} {} - {:.2f}({:.2f}) EUR\n".format(country.flag,
                                                                  country.name,
                                                                  country.get_active_balance(),
                                                                  country.get_balance())

    bk_output = "\n💸 БК ({}) {:2f}({:.2f}) EUR\n".format(
        len(stats["bookmakers"]),
        sum(b.get_deposit() for b in stats["bookmakers"]),
        sum(b.get_balance() for b in stats["bookmakers"]))
    bk_output += "💸 Активные БК ({}) {:.2f}({:.2f}) EUR\n\n".format(
        len([b for b in stats["bookmakers"] if b.is_active]),
        sum(b.get_deposit() for b in stats["bookmakers"] if b.is_active),
        sum(b.get_balance() for b in stats["bookmakers"] if b.is_active))

    bk_outputs = []
    bk_data = ""
    bk_country = ""
    for bookmaker in sorted(stats["bookmakers"], key=lambda bk: bk.country.name):
        if not bookmaker.is_active:
            continue

        if bk_country != bookmaker.country.name:
            bk_country = bookmaker.country.name
            bk_outputs.append(bk_data)
            bk_data = ""

        bk_data += "{} {} | {} | {} | {:.2f} ({:.2f}) EUR\n".format(
            bookmaker.country.flag, bookmaker.country.name, bookmaker.bk_name,
            bookmaker.name,
            bookmaker.get_deposit(), bookmaker.get_balance())

    if bk_data:
        bk_outputs.append(bk_data)


    wallet_output = "\n👛 Кошельки ({}) {:.2f} EUR\n\n".format(len(stats["wallets"]),
                                                              stats[
                                                                  "total_wallet_balance"])
    for wallet in sorted(stats["wallets"],
                         key=lambda w: w.country.name if w.country else 'Общий'):
        if wallet.country:
            wallet_output += "{} {} | {} | {} | {:.2f} EUR\n".format(wallet.country.flag,
                                                                     wallet.country.name,
                                                                     wallet.name,
                                                                     wallet.general_wallet_type,
                                                                     wallet.get_balance())
        else:
            wallet_output += "🌍 Общий | {} | {} | {:.2f} EUR\n".format(wallet.name,
                                                                       wallet.general_wallet_type,
                                                                       wallet.get_balance())
    return country_output, bk_output, wallet_output, bk_outputs


async def format_country_stats(stats):
    output = "🌎 Страна {} {}\n\n".format(stats["country"].name,
                                         stats["country"].flag)
    today = datetime.today().strftime('%d.%m.%Y')
    output += f"Период: по состоянию на {today}\n\n"
    # Show active balance (BK + wallets) first per ТЗ
    output += "Баланс: {:.2f}({:.2f}) EUR\n➖➖➖➖➖➖➖➖➖➖➖➖➖\n".format(
        stats["active_balance"], stats["balance"])

    output += "Сумма проставленных за все время: {:.2f} EUR\n".format(
        stats["total_bet"])
    output += "Сумма проставленных за месяц: {:.2f} EUR\n".format(
        stats["month_bet"])
    output += "Сумма проставленных за неделю: {:.2f} EUR\n".format(
        stats["week_bet"])
    output += "Сумма проставленных за сутки: {:.2f} EUR\n➖➖➖➖➖➖➖➖➖➖➖➖➖\n".format(
        stats["day_bet"])

    output += "Профит за все время: {:.2f} EUR\n".format(
        stats["total_profit"])
    output += "Профит за месяц: {:.2f} EUR\n".format(stats["month_profit"])
    output += "Профит за неделю: {:.2f} EUR\n".format(stats["week_profit"])
    output += "Профит за сутки: {:.2f} EUR\n➖➖➖➖➖➖➖➖➖➖➖➖➖\n".format(
        stats["day_profit"])

    output += "Траты за все время: {:.2f} EUR\n".format(
        stats["total_expenses"])
    output += "Траты за месяц: {:.2f} EUR\n".format(stats["month_expenses"])
    output += "Траты за неделю: {:.2f} EUR\n".format(stats["week_expenses"])
    output += "Траты за сутки: {:.2f} EUR\n➖➖➖➖➖➖➖➖➖➖➖➖➖\n".format(
        stats["day_expenses"])

    output += "Зарплата за все время: {:.2f} EUR\n".format(
        stats["total_salary"])
    output += "Зарплата за месяц: {:.2f} EUR\n".format(stats["month_salary"])
    output += "Зарплата за неделю: {:.2f} EUR\n".format(stats["week_salary"])
    output += "Зарплата за сутки: {:.2f} EUR".format(stats["day_salary"])

    return output


async def format_country_stats_by_period(stats):
    output = "🌎 Страна {} {}\n\n".format(stats["country"].name,
                                         stats["country"].flag)
    output += "Статистика за период с {} по {}\n\n".format(
        stats["start_date"], stats["end_date"])
    output += "Баланс: {:.2f}({:.2f}) EUR\n➖➖➖➖➖➖➖➖➖➖➖➖➖\n".format(
        stats["balance"], stats["active_balance"])
    output += "Сумма проставленных: {:.2f} EUR\n".format(
        stats["total_bet"])
    output += "Профит: {:.2f} EUR\n".format(
        stats["total_profit"])
    output += "Траты: {:.2f} EUR\n".format(
        stats["total_expenses"])
    output += "Зарплата: {:.2f} EUR\n".format(
        stats["total_salary"])
    return output


async def format_bookmaker_stats(stats):
    output = "💸 БК {}({})\n\n".format(stats["bookmaker"].bk_name,
                                      stats["bookmaker"].name)
    today = datetime.today().strftime('%d.%m.%Y')
    output += f"Период: по состоянию на {today}\n\n"
    output += "Баланс: {:.2f}({:.2f}) EUR\n\n".format(stats["deposit"],
                                                      stats["balance"])

    output += "Количество отчетов за:\n"
    output += "Все время - {}\n".format(stats["total_reports"] or 0)
    output += "Текущий месяц - {}\n".format(stats["month_reports"] or 0)
    output += "Текущую неделю - {}\n".format(stats["week_reports"] or 0)
    output += "Текущие сутки - {}\n\n".format(stats["day_reports"] or 0)

    output += "Сумма проставленных за:\n"
    output += "Все время - {:.2f} EUR\n".format(stats["total_bet"] or 0)
    output += "Текущий месяц - {:.2f} EUR\n".format(stats["month_bet"] or 0)
    output += "Текущую неделю - {:.2f} EUR\n".format(stats["week_bet"] or 0)
    output += "Текущие сутки - {:.2f} EUR\n\n".format(stats["day_bet"] or 0)

    output += "Сумма возврата за:\n"
    output += "Все время - {:.2f} EUR\n".format(stats["total_return"] or 0)
    output += "Текущий месяц - {:.2f} EUR\n".format(
        stats["month_return"] or 0)
    output += "Текущую неделю - {:.2f} EUR\n".format(
        stats["week_return"] or 0)
    output += "Текущие сутки - {:.2f} EUR\n\n".format(
        stats["day_return"] or 0)

    output += "Сумма профита за:\n"
    output += "Все время - {:.2f} EUR\n".format(stats["total_profit"] or 0)
    output += "Текущий месяц - {:.2f} EUR\n".format(
        stats["month_profit"] or 0)
    output += "Текущую неделю - {:.2f} EUR\n".format(
        stats["week_profit"] or 0)
    output += "Текущие сутки - {:.2f} EUR\n".format(stats["day_profit"] or 0)

    return output


async def format_source_stats(stats):
    output = "Статистика отчетов по источнику {} от {} до {}\n\n".format(
        stats["source"].name, stats["start_date"],
        stats["end_date"])
    output += "Сумма проставленных: {:.2f} EUR\n".format(stats["total_bet"])
    output += "Сумма возврата: {:.2f} EUR\n➖➖➖➖➖➖➖➖➖➖➖➖\n".format(
        stats["total_return"])
    output += "Сумма профита: {:.2f} EUR\n➖➖➖➖➖➖➖➖➖➖➖➖\n".format(
        stats["total_profit"])
    output += "Сумма накопленной зарплаты: {:.2f} EUR\n".format(
        stats["total_salary"])
    return output


async def format_salary_stats(stats):
    today = datetime.today().strftime('%d.%m.%Y')
    output = "Статистика по зарплате\n\n"

    # Period info (no date filtering implemented yet -> show 'all time' with as-of date)
    output += f"Период: за всё время (по {today})\n\n"

    total = abs(stats["total_salary"])
    output += "Общая сумма накопленной зарплаты: {:.2f} EUR\n\n".format(total)
    for employee in stats["employees"]:
        empl_balance = await employee.get_balance()
        output += "{} - {:.2f}\n".format(employee.name, abs(empl_balance))
    return output


async def format_employee_stats(stats):
    output = "Имя: {}\n".format(stats["employee"].name)
    today = datetime.today().strftime('%d.%m.%Y')
    output += f"Период: по состоянию на {today}\n"

    output += "Username: @{}\n".format(stats["employee"].username)
    output += "Зарплата: {:.2f} EUR\n".format(stats["salary"])
    return output


async def format_report_details(report):
    output = f"Отчет No {report.id}\n\n"
    output += f"Статус: {'Отчет не ошибочный' if not report.is_error else 'Отчет ошибочный'}\n\n"
    output += "Информация о человеке что ставил:\n"
    output += f"Name: {report.employees[0].name}\n"
    output += f"Username: {report.employees[0].username}\n\n"
    output += f"Дата: {report.date.strftime('%d-%m-%Y %H:%M')}\n"
    output += f"Сумма проставленных: {report.bet_amount:.2f} €\n"
    output += f"Сумма возврата: {report.return_amount:.2f} €\n"

    output += f"Профит: {report.profit:.2f} €\n"
    if report.is_error and report.profit < 0:
        output += f"Зарплата за отчет: {report.penalty:.2f} € (штраф)\n"
    else:
        output += f"Зарплата за отчет: {report.salary:.2f} €\n"
    output += f"Процент ЗП: {report.salary_percentage:.2f}%\n"
    output += f"Источник: {report.source.name}\n"
    output += f"Страна: {report.country.flag} {report.country.name}\n"
    output += f"БК: {report.bookmaker.bk_name}\n"
    output += f"Профиль: {report.bookmaker.name}\n"
    match_name = report.match.name if getattr(report, 'match', None) else "-"
    output += "Матч: {}".format(match_name)
    return output
