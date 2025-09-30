import asyncio
import random
import string
import time
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch
from data.base import Model
import pytest_asyncio
from contextlib import asynccontextmanager
import logging
from data.statistic import *
from data.utils import *

# Define the async engine and sessionmaker
engine = create_async_engine("sqlite+aiosqlite:///testing.db")
async_session = sessionmaker(engine, class_=AsyncSession,
                             expire_on_commit=False)

_logger = logging.getLogger(__name__)


@asynccontextmanager
async def session_scope_test() -> AsyncSession:
    session = async_session()
    try:
        yield session
        await session.commit()
    except Exception as e:
        _logger.error("session scope error: {}".format(e))
        await session.rollback()
        raise
    finally:
        await session.close()


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)


async def drop_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Model.metadata.drop_all)


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    async with async_session() as session:
        await create_tables()
        yield session
        await drop_tables()


@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_create_country(db):
    async with session_scope_test() as session:
        country = await Country.create(name="USA")
        assert country.name == "USA"
        assert country.id is not None


@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_create_bookmaker(db):
    async with session_scope_test() as session:
        country = await Country.create(name="USA")
        bookmaker = await Bookmaker.create(name="Bet365",
                                           country_id=country.id)
        assert bookmaker.name == "Bet365"
        assert bookmaker.id is not None
        assert bookmaker.country_id == country.id


@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_wallet_balance(db):
    async with session_scope_test() as session:
        wallet = await Wallet.create(deposit=1000)
        wallet = await Wallet.get(id=wallet.id)
        assert wallet.get_balance() == 1000


@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_country_balance(db):
    async with session_scope_test() as session:
        country = await Country.create(name="USA")
        bookmaker = await Bookmaker.create(name="Bet365",
                                           country_id=country.id)
        wallet = await Wallet.create(deposit=1000, country_id=country.id)

        country = await Country.get(id=country.id)
        assert country.get_active_balance() == 1000
        assert country.get_balance() == 0


@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_country_balance2(db):
    async with session_scope_test() as session:
        country = await Country.create(name="USA")
        bookmaker = await Bookmaker.create(name="Bet365",
                                           country_id=country.id)
        wallet = await Wallet.create(deposit=1000, country_id=country.id)
        wallet2 = await Wallet.create(deposit=1000)

        transaction = await Transaction.create(amount=1000,
                                               sender_wallet_id=wallet2.id,
                                               receiver_wallet_id=wallet.id)

        country = await Country.get(id=country.id)
        assert country.get_active_balance() == 2000
        assert country.get_balance() == 0


@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_bookmaker_balance(db):
    async with session_scope_test() as session:
        country = await Country.create(name="USA")
        bookmaker = await Bookmaker.create(name="Bet365",
                                           country_id=country.id,
                                           salary_percentage=10)
        wallet = await Wallet.create(deposit=1000, country_id=country.id)
        wallet2 = await Wallet.create(deposit=1000)
        transaction = await Transaction.create(amount=1000, from_="deposit",
                                               where="balance",
                                               sender_wallet_id=wallet2.id,
                                               receiver_bookmaker_id=bookmaker.id)
        report = await Report.create(bookmaker_id=bookmaker.id,
                                     bet_amount=1000, return_amount=2000)

        bookmaker = await Bookmaker.get(id=bookmaker.id)
        assert bookmaker.get_balance() == 2000


@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_transaction_real_amount(db):
    async with session_scope_test() as session:
        transaction = await Transaction.create(amount=1000, commission=10)
        assert transaction.real_amount == 990


@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_report_profit_salary_penalty(db):
    async with session_scope_test() as session:
        employee = await Employee.create(name="John Doe")
        bookmaker = await Bookmaker.create(name="Bet365",
                                           salary_percentage=10)
        report = await Report.create(employee_id=employee.id,
                                     bookmaker_id=bookmaker.id,
                                     bet_amount=100, return_amount=0,
                                     is_error=True)
        report = await Report.get(id=report.id)
        assert report.profit == -100
        assert report.salary == 0
        assert report.penalty == 30


@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_employee_salary_penalty(db):
    async with session_scope_test() as session:
        employee = await Employee.create(name="John Doe")
        bookmaker = await Bookmaker.create(name="Bet365",
                                           salary_percentage=10)
        report1 = await Report.create(employee_id=employee.id,
                                      bookmaker_id=bookmaker.id,
                                      bet_amount=100, return_amount=200,
                                      is_error=False)
        report2 = await Report.create(employee_id=employee.id,
                                      bookmaker_id=bookmaker.id,
                                      bet_amount=200, return_amount=100,
                                      is_error=True)

        employee = await Employee.get(id=employee.id)
        assert employee.salary() == 10
        assert employee.penalty() == 30


@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_bookmaker_reports(db):
    async with session_scope_test() as session:
        employee = await Employee.create(name="John Doe")
        bookmaker = await Bookmaker.create(name="Bet365",
                                           salary_percentage=10)
        report1 = await Report.create(employee_id=employee.id,
                                      bookmaker_id=bookmaker.id,
                                      bet_amount=100, return_amount=200,
                                      is_error=False)
        report2 = await Report.create(employee_id=employee.id,
                                      bookmaker_id=bookmaker.id,
                                      bet_amount=200, return_amount=100,
                                      is_error=True)

        bookmaker = await Bookmaker.get(id=bookmaker.id)
        assert len(bookmaker.reports) == 2
        assert bookmaker.reports[0].bet_amount == 100
        assert bookmaker.reports[1].bet_amount == 200
        assert bookmaker.get_balance() == 0


@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_wallet_adjustment(db):
    async with session_scope_test() as session:
        wallet = await Wallet.create(deposit=1000)
        wallet = await Wallet.get(id=wallet.id)
        wallet.adjustment = -200
        assert wallet.get_balance() == 800


@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_employee_adjustment(db):
    async with session_scope_test() as session:
        employee = await Employee.create(name="John Doe")
        bookmaker = await Bookmaker.create(name="Bet365",
                                           salary_percentage=10)
        report = await Report.create(employee_id=employee.id,
                                     bookmaker_id=bookmaker.id,
                                     bet_amount=100, return_amount=200,
                                     is_error=False)
        employee = await Employee.get(id=employee.id)
        await employee.update(adjustment=-50)

        employee = await Employee.get(id=employee.id)
        assert employee.get_balance() == -40


@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_delete_country(db):
    async with session_scope_test() as session:
        country = await Country.create(name="USA")
        await country.delete()
        deleted_country = await Country.get(id=country.id)
        assert deleted_country is None


@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_update_country(db):
    async with session_scope_test() as session:
        country = await Country.create(name="USA")
        await country.update(name="Canada")
        updated_country = await Country.get(id=country.id)
        assert updated_country.name == "Canada"


@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_update_bookmaker(db):
    async with session_scope_test() as session:
        country = await Country.create(name="USA")
        bookmaker = await Bookmaker.create(name="Bet365",
                                           country_id=country.id)
        await bookmaker.update(name="Bet365 Canada")
        updated_bookmaker = await Bookmaker.get(id=bookmaker.id)
        assert updated_bookmaker.name == "Bet365 Canada"


@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_create_and_find_template_by_country(db):
    async with session_scope_test() as session:
        country = await Country.create(name="Russia")
        template = await Template.create(name="Template1",
                                         country_id=country.id,
                                         employee_percentage=10.0)
        found_templates = await Template.filter(
            Template.country_id == country.id)

        assert len(found_templates) == 1
        assert found_templates[0].id == template.id
        assert found_templates[0].name == template.name
        assert found_templates[0].country_id == template.country_id
        assert found_templates[
                   0].employee_percentage == template.employee_percentage


@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_create_transaction(db):
    async with session_scope_test() as session:
        wallet1 = await Wallet.create(deposit=1000)
        wallet2 = await Wallet.create(deposit=1000)

        transaction = await Transaction.create(amount=1000,
                                               sender_wallet_id=wallet1.id,
                                               receiver_wallet_id=wallet2.id)

        wallet1 = await Wallet.get(id=wallet1.id)
        wallet2 = await Wallet.get(id=wallet2.id)
        assert wallet1.get_balance() == 0
        assert wallet2.get_balance() == 2000


@patch('data.statistic.session_scope', new=session_scope_test)
@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_get_total_stats_by_period(db):
    async with session_scope_test() as session:
        bk = await Bookmaker.create(name="Bet365", salary_percentage=10)
        report = await Report.create(bet_amount=100, return_amount=200,
                                     date=datetime.date(2022, 1, 1),
                                     bookmaker_id=bk.id)
        result = await get_total_stats_by_period(datetime.date(2022, 1, 1),
                                                 datetime.date(2022, 1, 2))

        assert result.total_bet == 100
        assert result.total_profit == 100
        assert result.total_salary == 10


@patch('data.statistic.session_scope', new=session_scope_test)
@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_get_total_balances(db):
    async with session_scope_test() as session:
        country = await Country.create(name="USA")
        bookmaker = await Bookmaker.create(name="Bet365",
                                           country_id=country.id)
        wallet = await Wallet.create(deposit=500, country_id=country.id)

        result = await get_total_balances()

        assert result['total_balance'] == 500
        assert result['total_bookmaker_balance'] == 0
        assert result['total_active_bookmaker_balance'] == 0
        assert result['total_wallet_balance'] == 500


@patch('data.statistic.session_scope', new=session_scope_test)
@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_get_bookmaker_stats(db):
    async with session_scope_test() as session:
        bookmaker = await Bookmaker.create(name="Bet365", salary_percentage=0)
        report = await Report.create(bet_amount=100, return_amount=200,
                                     bookmaker_id=bookmaker.id)

        result = await get_bookmaker_stats_by_id(bookmaker.id)

        assert result['balance'] == 100
        assert result['total_reports'] == 1
        assert result['total_bet'] == 100
        assert result['total_return'] == 200
        assert result['total_profit'] == 100


# @patch('data.statistic.session_scope', new=session_scope_test)
# @patch('data.base.session_scope', new=session_scope_test)
# @pytest.mark.asyncio
# async def test_get_source_stats_query(db):
#     async with session_scope_test() as session:
#         source = await Source.create(name="Test Source")
#         bookmaker = await Bookmaker.create(name="Test Bookmaker",
#                                            salary_percentage=10)
#         report = await Report.create(bet_amount=100, return_amount=200,
#                                      source_id=source.id,
#                                      bookmaker_id=bookmaker.id,
#                                      date=datetime.date(2023, 1, 1))
#
#         result = await get_source_stats(source.id, datetime.date(2023, 1, 1),
#                                         datetime.date(2023, 1, 2))
#
#         assert result['total_bet'] == 100
#         assert result['total_return'] == 200
#         assert result['total_profit'] == 100
#         assert result['total_salary'] == 10


@patch('data.statistic.session_scope', new=session_scope_test)
@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_get_country_stats(db):
    async with session_scope_test() as session:
        country = await Country.create(name="USA")
        bookmaker = await Bookmaker.create(name="Bet365",
                                           country_id=country.id,
                                           salary_percentage=10)
        report = await Report.create(bet_amount=100, return_amount=200,
                                     country_id=country.id,
                                     bookmaker_id=bookmaker.id,
                                     date=datetime.date(2023, 1, 1))
        result = await get_country_stats_by_id(country.id)

        assert result['balance'] == 0
        assert result['total_bet'] == 100
        assert result['total_profit'] == 100
        assert result['total_salary'] == 10


@patch('data.statistic.session_scope', new=session_scope_test)
@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_get_salary_stats(db):
    async with session_scope_test() as session:
        employee = await Employee.create(name="John Doe")
        bookmaker = await Bookmaker.create(name="Bet365",
                                           salary_percentage=10)
        report = await Report.create(bet_amount=100, return_amount=200,
                                     employee_id=employee.id,
                                     bookmaker_id=bookmaker.id)

        result = await salary_stats()

        assert result['total_salary'] == 10
        assert len(result['employees']) == 1


@patch('data.statistic.session_scope', new=session_scope_test)
@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_get_employee_stats(db):
    async with session_scope_test() as session:
        employee = await Employee.create(name="John Doe")
        bookmaker = await Bookmaker.create(name="Bet365",
                                           salary_percentage=10)
        report = await Report.create(bet_amount=100, return_amount=200,
                                     employee_id=employee.id,
                                     bookmaker_id=bookmaker.id)

        result = await get_employee_stats_by_id(employee.id)

        assert result['salary'] == 10


@patch('data.statistic.session_scope', new=session_scope_test)
@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_get_reports_by_period(db):
    async with session_scope_test() as session:
        source = await Source.create(name="Test Source")
        report1 = await Report.create(bet_amount=100, return_amount=200,
                                      date=datetime.date(2023, 1, 1),
                                      source_id=source.id)
        report2 = await Report.create(bet_amount=200, return_amount=300,
                                      date=datetime.date(2023, 1, 2),
                                      source_id=source.id)

        result = await get_reports_by_period(datetime.date(2023, 1, 1),
                                             datetime.date(2023, 1, 3),
                                             source.id)

        assert len(result) == 2
        assert result[0].bet_amount == 100
        assert result[1].bet_amount == 200


@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_create_transaction_with_commission(db):
    async with session_scope_test() as session:
        wallet1 = await Wallet.create(deposit=1000)
        wallet2 = await Wallet.create(deposit=1000)

        transaction = await Transaction.create(amount=1000, commission=100,
                                               sender_wallet_id=wallet1.id,
                                               receiver_wallet_id=wallet2.id)

        wallet1 = await Wallet.get(id=wallet1.id)
        wallet2 = await Wallet.get(id=wallet2.id)
        assert wallet1.get_balance() == 0
        assert wallet2.get_balance() == 1900


@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_create_transaction_wallet_to_bookmaker(db):
    async with session_scope_test() as session:
        wallet = await Wallet.create(deposit=1000)
        bookmaker = await Bookmaker.create(name="Bet365")

        transaction = await Transaction.create(amount=500,
                                               sender_wallet_id=wallet.id,
                                               receiver_bookmaker_id=bookmaker.id,
                                               where="balance")

        wallet = await Wallet.get(id=wallet.id)
        bookmaker = await Bookmaker.get(id=bookmaker.id)
        assert wallet.get_balance() == 500
        assert bookmaker.get_balance() == 500


@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_create_transaction_bookmaker_to_wallet(db):
    async with session_scope_test() as session:
        wallet = await Wallet.create(deposit=1000)
        bookmaker = await Bookmaker.create(name="Bet365")

        transaction1 = await Transaction.create(amount=1000, from_="deposit",
                                                where="balance",
                                                receiver_bookmaker_id=bookmaker.id)
        transaction2 = await Transaction.create(amount=500,
                                                sender_bookmaker_id=bookmaker.id,
                                                receiver_wallet_id=wallet.id,
                                                from_="balance")

        wallet = await Wallet.get(id=wallet.id)
        bookmaker = await Bookmaker.get(id=bookmaker.id)
        assert wallet.get_balance() == 1500
        assert bookmaker.get_balance() == 500


@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_create_transaction_with_country(db):
    async with session_scope_test() as session:
        country = await Country.create(name="USA")
        wallet = await Wallet.create(deposit=1000, country_id=country.id)

        transaction = await Transaction.create(amount=500,
                                               sender_wallet_id=wallet.id,
                                               country_id=country.id)

        country = await Country.get(id=country.id)
        assert country.get_active_balance() == 500


@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_create_transaction(db):
    async with session_scope_test() as session:
        wallet1 = await Wallet.create(deposit=1000)
        wallet2 = await Wallet.create(deposit=500)

        transaction = await create_transaction(wallet1.id, wallet2.id, None,
                                               None,
                                               700, 650, "balance", "balance")

        assert transaction.amount == 700
        assert transaction.commission == 50
        assert transaction.from_ == "balance"
        assert transaction.where == "balance"
        assert transaction.sender_wallet_id == wallet1.id
        assert transaction.receiver_wallet_id == wallet2.id
        assert transaction.sender_bookmaker_id is None
        assert transaction.receiver_bookmaker_id is None

        wallet1 = await Wallet.get(id=wallet1.id)
        wallet2 = await Wallet.get(id=wallet2.id)

        assert wallet1.get_balance() == 300
        assert wallet2.get_balance() == 1150


@patch('data.statistic.session_scope', new=session_scope_test)
@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_get_source_stats_data(db):
    async with session_scope_test() as session:
        source = await Source.create(name="Test Source")
        bookmaker = await Bookmaker.create(name="Test Bookmaker",
                                           salary_percentage=10)
        report1 = await Report.create(bet_amount=100, return_amount=200,
                                      source_id=source.id,
                                      bookmaker_id=bookmaker.id,
                                      date=datetime.date(2023, 1, 1))
        report2 = await Report.create(bet_amount=200, return_amount=300,
                                      source_id=source.id,
                                      bookmaker_id=bookmaker.id,
                                      date=datetime.date(2023, 1, 2))

        result = await get_source_stats_data(source.id,
                                             datetime.date(2023, 1, 1),
                                             datetime.date(2023, 1, 2))

        assert result['total_bet'] == 300
        assert result['total_return'] == 500
        assert result['total_profit'] == 200
        assert result['total_salary'] == 30


@patch('data.statistic.session_scope', new=session_scope_test)
@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_employee_salary_calculation(db):
    async with session_scope_test() as session:
        employee1 = await Employee.create(name="John Doe")
        employee2 = await Employee.create(name="Jane Smith")

        bookmaker1 = await Bookmaker.create(name="Bookmaker1",
                                            salary_percentage=10)
        bookmaker2 = await Bookmaker.create(name="Bookmaker2",
                                            salary_percentage=15)

        report1 = await Report.create(employee_id=employee1.id,
                                      bookmaker_id=bookmaker1.id,
                                      bet_amount=1000, return_amount=1500,
                                      is_error=False)
        report2 = await Report.create(employee_id=employee1.id,
                                      bookmaker_id=bookmaker2.id,
                                      bet_amount=500, return_amount=800,
                                      is_error=False)
        report3 = await Report.create(employee_id=employee2.id,
                                      bookmaker_id=bookmaker1.id,
                                      bet_amount=2000, return_amount=2200,
                                      is_error=False)

        employee1 = await Employee.get(id=employee1.id)
        employee2 = await Employee.get(id=employee2.id)

        assert employee1.salary() == 175  # (1000 * 0.1) + (500 * 0.15)
        assert employee2.salary() == 200  # 2000 * 0.1


@patch('data.statistic.session_scope', new=session_scope_test)
@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_large_data_insertion_and_querying(db):
    NUM_COUNTRIES = 10
    NUM_BOOKMAKERS_PER_COUNTRY = 5
    NUM_EMPLOYEES = 20
    NUM_REPORTS_PER_BOOKMAKER = 20

    def random_string(length):
        return ''.join(random.choices(string.ascii_letters, k=length))

    async with session_scope_test() as session:
        # Create countries
        for _ in range(NUM_COUNTRIES):
            await Country.create(name=random_string(10))

        countries = await Country.all()

        # Create bookmakers for each country
        for country in countries:
            for _ in range(NUM_BOOKMAKERS_PER_COUNTRY):
                await Bookmaker.create(name=random_string(10),
                                       country_id=country.id,
                                       salary_percentage=random.uniform(5,
                                                                        15),
                                       bk_name=random_string(10), )

        # Create employees
        for _ in range(NUM_EMPLOYEES):
            await Employee.create(name=random_string(10))

        employees = await Employee.all()
        bookmakers = await Bookmaker.all()
        sources = await asyncio.gather(
            *[Source.create(name=random_string(10)) for _ in range(10)])
        # Create reports
        for i in range(30):
            start_time = time.time()
            await asyncio.gather(*[add_report_to_db(
                date=datetime.date(2022, 1, 1),
                wrong_report_value=random.choice([True, False]),
                source_name=random.choice(sources).name,
                country_name=random.choice(countries).name,
                bk_name=bookmaker.bk_name,
                bk_login=bookmaker.name,
                placed=random.uniform(100, 1000),
                received=random.uniform(100, 1000),
                userid=random.choice(employees).id,
                nick_name=random.choice(employees).name,
                match_name=random_string(10),
                employees=employees, sources=sources, countries=countries
            ) for bookmaker in bookmakers for _ in
                range(NUM_REPORTS_PER_BOOKMAKER)])

            print(f"Insertion time: {time.time() - start_time:.2f} seconds")

        # Measure query times
        start_time = time.time()
        total_stats = await get_total_stats_by_period(
            datetime.date(2022, 1, 1),
            datetime.date(2023, 12, 31))
        total_stats_time = time.time() - start_time
        print(f"Total stats query time: {total_stats_time:.2f} seconds")

        start_time = time.time()
        total_balances = await get_total_balances()
        total_balances_time = time.time() - start_time
        print(f"Total balances query time: {total_balances_time:.2f} seconds")

        start_time = time.time()
        bookmaker_stats = await get_bookmaker_stats_by_id(bookmakers[0].id)
        bookmaker_stats_time = time.time() - start_time
        print(
            f"Bookmaker stats query time: {bookmaker_stats_time:.2f} seconds")

        start_time = time.time()
        country_stats = await get_country_stats_by_id(countries[0].id)
        country_stats_time = time.time() - start_time
        print(f"Country stats query time: {country_stats_time:.2f} seconds")

        start_time = time.time()
        salaries = await salary_stats()
        salary_stats_time = time.time() - start_time
        print(f"Salary stats query time: {salary_stats_time:.2f} seconds")

        start_time = time.time()
        countries = await get_countries()
        print(time.time()-start_time)