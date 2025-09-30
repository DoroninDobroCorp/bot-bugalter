#!/usr/bin/env python3
"""
Миграция для добавления поля deleted_at в таблицу report
"""

import asyncio
from sqlalchemy import text
from data.config import async_session


async def add_deleted_at_column():
    """Добавляет колонку deleted_at в таблицу report"""
    async with async_session() as session:
        try:
            # Проверяем, есть ли уже колонка (для SQLite используем PRAGMA)
            check_query = text("PRAGMA table_info(report);")
            result = await session.execute(check_query)
            columns = result.fetchall()
            
            # Проверяем наличие колонки deleted_at
            column_names = [col[1] for col in columns]
            if 'deleted_at' in column_names:
                print("Колонка 'deleted_at' уже существует в таблице 'report'")
                return
            
            # Добавляем колонку
            add_column_query = text("""
                ALTER TABLE report 
                ADD COLUMN deleted_at TIMESTAMP;
            """)
            await session.execute(add_column_query)
            
            # Создаем индекс
            create_index_query = text("""
                CREATE INDEX IF NOT EXISTS ix_report_deleted_at 
                ON report (deleted_at);
            """)
            await session.execute(create_index_query)
            
            await session.commit()
            print("Успешно добавлена колонка 'deleted_at' и создан индекс")
            
        except Exception as e:
            print(f"Ошибка при добавлении колонки: {e}")
            await session.rollback()
            raise


async def main():
    print("=" * 50)
    print("Запуск миграции: добавление deleted_at")
    print("=" * 50)
    
    await add_deleted_at_column()
    
    print("=" * 50)
    print("Миграция завершена")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
