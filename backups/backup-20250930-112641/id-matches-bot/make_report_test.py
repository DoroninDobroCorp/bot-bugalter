from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from data.models import *
import random
import string

# Создаем engine для работы с базой данных SQLite
engine = create_engine('sqlite:///test_db.db', echo=True)

# Создаем сессию для взаимодействия с базой данных
Session = sessionmaker(bind=engine)
session = Session()

# Создаем таблицы в базе данных
Model.metadata.create_all(engine)

try:
    # Создаем страну
    country = Country(name='USA', flag='🇺🇸')
    session.add(country)
    session.commit()

    # Создаем букмекера
    bookmaker = Bookmaker(name='Bookmaker1', country=country,
                          salary_percentage=10, bk_name='BetWay')
    session.add(bookmaker)
    session.commit()

    # Создаем источник
    source = Source(name='MySource')
    session.add(source)
    session.commit()

    # Создаем сотрудников
    employees = []
    for i in range(20):
        employee = Employee(name=f'Employee{i}', username=f'employee{i}')
        session.add(employee)
        employees.append(employee)
    session.commit()

    # Создаем матчи
    matches = []
    for i in range(10):
        match_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        match = Match(id=match_id, name=f'Match{i}')
        session.add(match)
        matches.append(match)
    session.commit()

    # Создаем отчеты
    for match in matches:
        for i in range(10):
            employees_in_report = random.sample(employees, random.randint(1, 5))
            report = Report(date=datetime.date(2021, 1, 1),
                            source=source, country=country,
                            bookmaker=bookmaker, match=match,
                            nickname='emploee1', bet_amount=100,
                            return_amount=200, employees=employees_in_report)
            session.add(report)

    session.commit()

    # Создаем токен
    token = Token(access_token='token')
    session.add(token)
    session.commit()

    print("Тестовая база данных успешно создана!")
except Exception as e:
    session.rollback()
    print(f"Ошибка при создании тестовой базы данных: {e}")
finally:
    session.close()