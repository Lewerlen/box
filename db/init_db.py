from db.database import create_tables
from db.seed import seed_data


def initialize_database():
    """
    Выполняет полную инициализацию базы данных:
    """
    print("--- Инициализация базы данных ---")

    # Шаг 1: Создание всех таблиц
    print("1. Проверка и создание таблиц...")
    create_tables()

    # Шаг 2: Заполнение справочников данными
    print("\n2. Проверка и заполнение справочников...")
    seed_data()

    print("--- Инициализация базы данных завершена ---")