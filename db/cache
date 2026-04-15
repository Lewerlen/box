import threading
from db.database import get_db_connection
from utils.formatters import format_weight
from utils.excel_generator import _rank_suffix          # для сортировки разрядов в Excel       # noqa: F401    

# Формат: {'название_таблицы': [список_записей]}
CACHED_DATA = {
    "ranks": [],
    "class": [],
    "region": [],
    "city": [],
    "club": [],
    "coach": [],
    "age_category": [],
    "weight_category": [],
}

# Как часто обновлять кэш в секундах
CACHE_TTL = 3600


def _fetch_table_data(table_name, filter_by_status=False):
    """Вспомогательная функция для получения данных из таблицы."""
    conn = get_db_connection()
    cur = conn.cursor()
    query = f"SELECT id, name FROM {table_name}"
    if filter_by_status:
        query += " WHERE status = TRUE"
    cur.execute(query)
    data = [{"id": row[0], "name": row[1]} for row in cur.fetchall()]
    cur.close()
    conn.close()
    return data

def _fetch_weight_categories():
    """Вспомогательная функция для получения данных из таблицы весовых категорий."""
    conn = get_db_connection()
    cur = conn.cursor()
    query = "SELECT id, age_category_id, weight FROM weight_category ORDER BY weight"
    cur.execute(query)
    data = [
        {
            "id": row[0],
            "age_category_id": row[1],
            "name": format_weight(row[2]),
        }
        for row in cur.fetchall()
    ]
    cur.close()
    conn.close()
    return data


def update_cache():
    """Основная функция для обновления всего кэша."""
    print("Обновление кэша...")
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # --- Загрузка таблиц с логической сортировкой по ID ---
        for table in ["ranks", "class"]:
            table_name = f'"{table}"' if table == "class" else table
            cur.execute(f"SELECT id, name FROM {table_name} WHERE status = TRUE ORDER BY id")
            CACHED_DATA[table] = [
                {"id": row[0], "name": row[1]} for row in cur.fetchall()
            ]

        # --- Загрузка возрастных категорий с сортировкой по ID ---
        cur.execute("SELECT id, name, min_year, max_year, gender FROM age_category WHERE status = TRUE ORDER BY id")
        CACHED_DATA["age_category"] = [
            {"id": row[0], "name": row[1], "min_year": row[2], "max_year": row[3], "gender": row[4]}
            for row in cur.fetchall()
        ]

        # --- Загрузка таблиц с алфавитной сортировкой по названию ---
        cur.execute(f"SELECT id, name FROM region ORDER BY name")
        CACHED_DATA["region"] = [
            {"id": row[0], "name": row[1]} for row in cur.fetchall()
        ]

        cur.execute(f"SELECT id, name, region_id FROM city ORDER BY name")
        CACHED_DATA["city"] = [
            {"id": row[0], "name": row[1], "region_id": row[2]} for row in cur.fetchall()
        ]

        cur.execute(f"SELECT id, name, city_id FROM club ORDER BY name")
        CACHED_DATA["club"] = [
            {"id": row[0], "name": row[1], "city_id": row[2]} for row in cur.fetchall()
        ]

        cur.execute(f"SELECT id, name, club_id FROM coach ORDER BY name")
        CACHED_DATA["coach"] = [
            {"id": row[0], "name": row[1], "club_id": row[2]} for row in cur.fetchall()
        ]

        # --- Загрузка весовых категорий ---
        CACHED_DATA["weight_category"] = _fetch_weight_categories()
        cur.close()
        conn.close()
        print("Кэш успешно обновлен.")
    except Exception as e:
        print(f"Ошибка при обновлении кэша: {e}")
    finally:
        if conn:
            conn.close()

def get_age_categories_from_cache():
    """Возвращает кэшированный список возрастных категорий (с min/max year)."""
    return CACHED_DATA["age_category"]

def get_weight_categories_from_cache(age_category_id: int):
    """Возвращает отфильтрованный по возрастной категории кэшированный список весовых категорий."""
    return [
        cat
        for cat in CACHED_DATA["weight_category"]
        if cat["age_category_id"] == age_category_id
    ]

def get_classes_from_cache():
    """Возвращает кэшированный список классов."""
    return CACHED_DATA["class"]

def get_ranks_from_cache():
    """Возвращает кэшированный список разрядов."""
    return CACHED_DATA["ranks"]


def get_regions_from_cache():
    """Возвращает кэшированный список регионов."""
    return CACHED_DATA["region"]


def get_cities_from_cache(region_id: int):
    """Возвращает отфильтрованный по ID региона кэшированный список городов."""
    return [
        city for city in CACHED_DATA["city"] if city["region_id"] == region_id
    ]


def get_clubs_from_cache(city_id: int):
    """Возвращает отфильтрованный по ID города кэшированный список клубов."""
    return [
        club for club in CACHED_DATA["club"] if club["city_id"] == city_id
    ]


def get_coaches_from_cache(club_id: int):
    """Возвращает отфильтрованный по ID клуба кэшированный список тренеров."""
    return [
        coach for coach in CACHED_DATA["coach"] if coach["club_id"] == club_id
    ]


def get_all_clubs_from_cache():
    """Возвращает кэшированный список всех клубов."""
    return CACHED_DATA["club"]

def start_cache_updater():
    """Запускает периодическое обновление кэша в отдельном потоке."""
    # Первый раз обновляем сразу при старте
    update_cache()

    # И запускаем таймер для периодического обновления
    threading.Timer(CACHE_TTL, start_cache_updater).start()
