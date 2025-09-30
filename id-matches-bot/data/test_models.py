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
from models import *

# Define the async engine and sessionmaker
engine = create_async_engine("sqlite+aiosqlite:///:memory:")
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
async def test_report_profit_salary_penalty_multiple_employees(db):
    async with session_scope_test() as session:
        employee1 = await Employee.create(name="John Doe")
        employee2 = await Employee.create(name="Jane Smith")
        bookmaker = await Bookmaker.create(name="Bet365",
                                           salary_percentage=10)
        report = await Report.create(bookmaker_id=bookmaker.id,
                                     bet_amount=100, return_amount=0,
                                     is_error=True)
        await ReportEmployee.create(report_id=report.id,
                                    employee_id=employee1.id)
        await ReportEmployee.create(report_id=report.id,
                                    employee_id=employee2.id)

        report = await Report.get(id=report.id)
        assert report.profit == -100
        assert report.salary == 0
        assert report.penalty == 30


@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_employee_salary_penalty_multiple_reports(db):
    async with session_scope_test() as session:
        employee1 = await Employee.create(name="John Doe")
        employee2 = await Employee.create(name="Jane Smith")
        bookmaker = await Bookmaker.create(name="Bet365",
                                           salary_percentage=10)
        report1 = await Report.create(bookmaker_id=bookmaker.id,
                                      bet_amount=100, return_amount=200,
                                      is_error=False)
        report2 = await Report.create(bookmaker_id=bookmaker.id,
                                      bet_amount=200, return_amount=100,
                                      is_error=True)
        await ReportEmployee.create(report_id=report1.id,
                                    employee_id=employee1.id)
        await ReportEmployee.create(report_id=report1.id,
                                    employee_id=employee2.id)
        await ReportEmployee.create(report_id=report2.id,
                                    employee_id=employee1.id)
        await ReportEmployee.create(report_id=report2.id,
                                    employee_id=employee2.id)

        employee1 = await Employee.get_with_related(id=employee1.id)
        employee2 = await Employee.get_with_related(id=employee2.id)
        assert employee1.salary() == 5 + 0  # salary from report1 divided by 2, no salary from report2
        assert employee1.penalty() == 15  # penalty from report2
        assert employee2.salary() == 5  # salary from report1 divided by 2
        assert employee2.penalty() == 15  # no penalty for employee2


@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_employee_salary_calculation_multiple_employees(db):
    async with session_scope_test() as session:
        employee1 = await Employee.create(name="John Doe")
        employee2 = await Employee.create(name="Jane Smith")
        bookmaker1 = await Bookmaker.create(name="Bookmaker1",
                                            salary_percentage=10)
        bookmaker2 = await Bookmaker.create(name="Bookmaker2",
                                            salary_percentage=15)
        report1 = await Report.create(bookmaker_id=bookmaker1.id,
                                      bet_amount=1000, return_amount=1500,
                                      is_error=False)
        report2 = await Report.create(bookmaker_id=bookmaker2.id,
                                      bet_amount=500, return_amount=800,
                                      is_error=False)
        await ReportEmployee.create(report_id=report1.id,
                                    employee_id=employee1.id)
        await ReportEmployee.create(report_id=report1.id,
                                    employee_id=employee2.id)
        await ReportEmployee.create(report_id=report2.id,
                                    employee_id=employee1.id)

        employee1 = await Employee.get_with_related(id=employee1.id)
        employee2 = await Employee.get_with_related(id=employee2.id)
        assert employee1.salary() == 50 + 75  # (1000 * 0.1 / 2) + (500 * 0.15)
        assert employee2.salary() == 50  # 1000 * 0.1 / 2


@patch('data.base.session_scope', new=session_scope_test)
@pytest.mark.asyncio
async def test_update_report_updates_related_employees(db):
    async with session_scope_test() as session:
        employee1 = await Employee.create(name="John Doe")
        employee2 = await Employee.create(name="Jane Smith")
        bookmaker = await Bookmaker.create(name="Bookmaker1",
                                           salary_percentage=10)
        report = await Report.create(bookmaker_id=bookmaker.id,
                                     bet_amount=100, return_amount=200)
        await ReportEmployee.create(report_id=report.id,
                                    employee_id=employee1.id)
        await ReportEmployee.create(report_id=report.id,
                                    employee_id=employee2.id)

        report = await Report.get_with_related(id=report.id)
        await report.update(bet_amount=150, return_amount=300)

        employee1 = await Employee.get_with_related(id=employee1.id)
        employee2 = await Employee.get_with_related(id=employee2.id)

        assert employee1.salary() == 7.5  # (150 * 0.1)
        assert employee2.salary() == 7.5  # (150 * 0.1)
