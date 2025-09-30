#!/usr/bin/env python3
"""
Скрипт для очистки удаленных отчетов старше 90 дней.
Физически удаляет записи из таблиц report и report_employee.
Запускать периодически через cron.
"""

import asyncio
import datetime
from sqlalchemy import delete, select
from data.config import async_session
from data.models import Report, ReportEmployee


async def cleanup_old_deleted_reports(days_threshold=90):
    """
    Удаляет отчеты, которые были помечены как удаленные более чем days_threshold дней назад.
    
    Args:
        days_threshold: Количество дней после удаления, после которых происходит физическое удаление
    """
    threshold_date = datetime.datetime.utcnow() - datetime.timedelta(days=days_threshold)
    
    async with async_session() as session:
        # Найти отчеты для удаления
        stmt = select(Report.id).where(
            Report.is_deleted == True,
            Report.deleted_at.isnot(None),
            Report.deleted_at < threshold_date
        )
        result = await session.execute(stmt)
        report_ids = [row[0] for row in result.fetchall()]
        
        if not report_ids:
            print(f"Нет отчетов для удаления (старше {days_threshold} дней)")
            return 0
        
        print(f"Найдено {len(report_ids)} отчетов для удаления")
        
        # Удалить связанные записи из report_employee
        delete_re_stmt = delete(ReportEmployee).where(
            ReportEmployee.report_id.in_(report_ids)
        )
        result_re = await session.execute(delete_re_stmt)
        print(f"Удалено {result_re.rowcount} записей из report_employee")
        
        # Удалить отчеты
        delete_r_stmt = delete(Report).where(
            Report.id.in_(report_ids)
        )
        result_r = await session.execute(delete_r_stmt)
        print(f"Удалено {result_r.rowcount} отчетов")
        
        await session.commit()
        
        return len(report_ids)


async def main():
    print("=" * 50)
    print(f"Запуск очистки удаленных отчетов: {datetime.datetime.utcnow()}")
    print("=" * 50)
    
    deleted_count = await cleanup_old_deleted_reports(days_threshold=90)
    
    print("=" * 50)
    print(f"Очистка завершена. Удалено отчетов: {deleted_count}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
