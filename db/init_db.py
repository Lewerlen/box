from db.database import create_tables
from db.seed import seed_data, seed_competitions


def initialize_database():
    """
    Выполняет полную инициализацию базы данных:
    """
    print("--- Инициализация базы данных ---")

    print("1. Проверка и создание таблиц...")
    create_tables()

    print("\n2. Проверка и заполнение справочников...")
    seed_data()

    print("\n3. Проверка и заполнение соревнований...")
    seed_competitions()

    print("--- Инициализация базы данных завершена ---")
