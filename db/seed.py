from db.database import get_db_connection

# Данные для таблицы разрядов (ranks)
RANKS_DATA = [
    {"name": "III юношеский", "status": True},
    {"name": "II юношеский", "status": True},
    {"name": "I юношеский", "status": True},
    {"name": "III спортивный", "status": True},
    {"name": "II спортивный", "status": True},
    {"name": "I спортивный", "status": True},
    {"name": "КМС", "status": True},
    {"name": "МС", "status": False},
    {"name": "МСМК", "status": False},
    {"name": "ЗМС", "status": False},
]

# Данные для таблицы классов (class)
CLASS_DATA = [
    {"name": "А (Опытный)", "status": True},
    {"name": "В (Новичок)", "status": True},
    {"name": "С (Дебютант)", "status": True},
]

# Данные для регионов и городов
LOCATION_DATA = [
    {
        "region": "Республика Башкортостан",
        "cities": [
            "г. Уфа", "г. Бирск", "с. Бураево", "с. Иглино", "г. Мелеуз",
            "г. Сибай", "с. Старобалтачево", "г. Стерлитамак", "г. Туймазы",
            "с. Чесноковка", "пгт. Чишмы"
        ]
    },
    {
        "region": "Республика Марий Эл",
        "cities": []
    },
    {
        "region": "Республика Удмуртия",
        "cities": ["Ижевск"]
    },
    {
        "region": "Оренбургская область",
        "cities": ["Оренбург", "Сорочинск"]
    },
    {
        "region": "Самарская область",
        "cities": ["Самара"]
    },
    {
        "region": "Ульяновская область",
        "cities": ["Ульяновск"]
    }
]

# Данные для весовых и возрастных категорий
CATEGORIES_DATA = [
    # --- Мужчины ---
    {
        "name": "8-9", "gender": "Мужской",
        "weights": [18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52, 54, 56, 58, 60, 63.5, 67,
                    67.9]
    },
    {
        "name": "10-11", "gender": "Мужской",
        "weights": [24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52, 54, 56, 58, 60, 63.5, 67, 67.9]
    },
    {
        "name": "12-13", "gender": "Мужской",
        "weights": [32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52, 54, 56, 58, 60, 63.5, 67, 71, 71.9]
    },
    {
        "name": "14-15", "gender": "Мужской",
        "weights": [38, 40, 42, 45, 48, 51, 54, 57, 60, 63.5, 67, 71, 75, 81, 81.9]
    },
    {
        "name": "16-17", "gender": "Мужской",
        "weights": [42, 45, 48, 51, 54, 57, 60, 63.5, 67, 71, 75, 81, 86, 91, 91.9]
    },
    {
        "name": "старше 18", "gender": "Мужской",
        "weights": [45, 48, 51, 54, 57, 60, 63.5, 67, 71, 75, 81, 86, 91, 91.9]
    },
    # --- Женщины ---
    {
        "name": "8-9", "gender": "Женский",
        "weights": [18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52, 54, 56, 58, 60, 63.5, 67,
                    67.9]
    },
    {
        "name": "10-11", "gender": "Женский",
        "weights": [24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52, 54, 56, 58, 60, 63.5, 67, 67.9]
    },
    {
        "name": "12-13", "gender": "Женский",
        "weights": [32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52, 54, 56, 58, 60, 63.5, 63.9]
    },
    {
        "name": "14-15", "gender": "Женский",
        "weights": [32, 34, 36, 38, 40, 42, 45, 48, 51, 54, 57, 60, 63.5, 67, 71, 71.9]
    },
    {
        "name": "16-17", "gender": "Женский",
        "weights": [42, 45, 48, 51, 54, 57, 60, 63.5, 67, 71, 75, 75.9]
    },
    {
        "name": "старше 18", "gender": "Женский",
        "weights": [45, 48, 51, 54, 57, 60, 63.5, 67, 71, 75, 75.9]
    },
]


def seed_simple_table(cur, table_name, data):
    """Заполняет простую справочную таблицу (например, ranks, class), используя существующий курсор."""
    print(f"\nЗаполнение таблицы '{table_name}'...")
    for item in data:
        cur.execute(f"SELECT id FROM {table_name} WHERE name = %s", (item["name"],))
        if not cur.fetchone():
            cur.execute(
                f"INSERT INTO {table_name} (name, status) VALUES (%s, %s)",
                (item["name"], item["status"]),
            )
            print(f" -> Добавлена запись: {item['name']}")


def seed_data():
    """Заполняет все справочные таблицы: категории, регионы, города, разряды, классы."""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # --- 1. Заполнение возрастных и весовых категорий ---
        seed_age_categories(cur)

        # --- 2. Заполнение регионов и городов ---
        print("\nЗаполнение регионов и городов...")
        for item in LOCATION_DATA:
            region_name = item["region"]
            cities = item["cities"]

            cur.execute("SELECT id FROM region WHERE name = %s", (region_name,))
            result = cur.fetchone()

            if not result:
                cur.execute(
                    "INSERT INTO region (name) VALUES (%s) RETURNING id",
                    (region_name,)
                )
                region_id = cur.fetchone()[0]
                print(f"Добавлен регион: {region_name}")
            else:
                region_id = result[0]
                print(f"Регион '{region_name}' уже существует.")

            if cities:
                added_cities_count = 0
                for city_name in cities:
                    cur.execute("SELECT id FROM city WHERE name = %s AND region_id = %s", (city_name, region_id))
                    if not cur.fetchone():
                        cur.execute(
                            "INSERT INTO city (name, region_id) VALUES (%s, %s)",
                            (city_name, region_id)
                        )
                        added_cities_count += 1
                if added_cities_count > 0:
                    print(f" -> Добавлено городов: {added_cities_count} шт.")

        # --- 3. Заполнение простых справочников (разряды и классы) ---
        seed_simple_table(cur, "ranks", RANKS_DATA)
        seed_simple_table(cur, "class", CLASS_DATA)
        
        # --- 4. Заполнение исключений для отчеств ---
        seed_patronymic_exceptions(cur)

        conn.commit()
        print("\nВсе справочники успешно заполнены.")

    except Exception as e:
        conn.rollback()
        print(f"Ошибка при заполнении: {e}")
    finally:
        cur.close()
        conn.close()


def seed_patronymic_exceptions(cur):
    """Заполняет таблицу patronymic_exceptions суффиксами отчеств."""
    print("\nЗаполнение таблицы 'patronymic_exceptions'...")
    PATRONYMIC_EXCEPTIONS = ["оглы"]
    
    for suffix in PATRONYMIC_EXCEPTIONS:
        cur.execute("SELECT id FROM patronymic_exceptions WHERE suffix = %s", (suffix,))
        if not cur.fetchone():
            cur.execute("INSERT INTO patronymic_exceptions (suffix) VALUES (%s)", (suffix,))
            print(f" -> Добавлен суффикс: {suffix}")

def seed_age_categories(cur):
    """Заполняет таблицу age_category данными с годами рождения."""
    print("\nЗаполнение таблицы 'age_category'...")
    AGE_CATEGORIES_DATA = [
        # Мужчины (Расчет возраста для 2025 года)
        {"name": "8-9", "min_year": 2016, "max_year": 2017, "gender": "Мужской", "status": True},
        {"name": "10-11", "min_year": 2014, "max_year": 2015, "gender": "Мужской", "status": True},
        {"name": "12-13", "min_year": 2012, "max_year": 2013, "gender": "Мужской", "status": True},
        {"name": "14-15", "min_year": 2010, "max_year": 2011, "gender": "Мужской", "status": True},
        {"name": "16-17", "min_year": 2008, "max_year": 2009, "gender": "Мужской", "status": True},
        {"name": "старше 18", "min_year": None, "max_year": 2007, "gender": "Мужской", "status": True},

        # Женщины
        {"name": "8-9", "min_year": 2016, "max_year": 2017, "gender": "Женский", "status": True},
        {"name": "10-11", "min_year": 2014, "max_year": 2015, "gender": "Женский", "status": True},
        {"name": "12-13", "min_year": 2012, "max_year": 2013, "gender": "Женский", "status": True},
        {"name": "14-15", "min_year": 2010, "max_year": 2011, "gender": "Женский", "status": True},
        {"name": "16-17", "min_year": 2008, "max_year": 2009, "gender": "Женский", "status": True},
        {"name": "старше 18", "min_year": None, "max_year": 2007, "gender": "Женский", "status": True},
    ]

    # Данные для весовых категорий будут заполняться динамически по ID созданных возрастных категорий
    # Весовые категории для муайтая согласно скриншоту
    WEIGHT_CATEGORIES_BY_NAME = {
        # Мужчины
        ("8-9", "Мужской"): [18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52, 54, 56, 58, 60, 63.5, 67, 67.9],
        ("10-11", "Мужской"): [24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52, 54, 56, 58, 60, 63.5, 67, 67.9],
        ("12-13", "Мужской"): [32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52, 54, 56, 58, 60, 63.5, 67, 71, 71.9],
        ("14-15", "Мужской"): [38, 40, 42, 45, 48, 51, 54, 57, 60, 63.5, 67, 71, 75, 81, 81.9],
        ("16-17", "Мужской"): [45, 48, 51, 54, 57, 60, 63.5, 67, 71, 75, 81, 86, 91, 91.9],
        ("старше 18", "Мужской"): [48, 51, 54, 57, 60, 63.5, 67, 71, 75, 81, 86, 91, 91.9],
        # Женщины
        ("8-9", "Женский"): [18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52, 54, 56, 58, 60, 63.5, 63.9],
        ("10-11", "Женский"): [24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52, 54, 56, 58, 60, 63.5, 63.9],
        ("12-13", "Женский"): [32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52, 54, 56, 58, 60, 63.5, 63.9],
        ("14-15", "Женский"): [34, 36, 38, 40, 42, 45, 48, 51, 54, 57, 60, 63.5, 67, 71, 71.9],
        ("16-17", "Женский"): [42, 45, 48, 51, 54, 57, 60, 63.5, 67, 71, 75, 75.9],
        ("старше 18", "Женский"): [48, 51, 54, 57, 60, 63.5, 67, 71, 75, 75.9],
    }

    age_category_ids = {} # Словарь для хранения ID созданных возрастных категорий

    for category in AGE_CATEGORIES_DATA:
        # Проверяем по уникальному ключу (min_year, max_year, gender)
        # Обрабатываем None для min_year
        if category["min_year"] is None:
            cur.execute(
                "SELECT id FROM age_category WHERE min_year IS NULL AND max_year = %s AND gender = %s",
                (category["max_year"], category["gender"])
            )
        else:
             cur.execute(
                 "SELECT id FROM age_category WHERE min_year = %s AND max_year = %s AND gender = %s",
                 (category["min_year"], category["max_year"], category["gender"])
             )

        result = cur.fetchone()
        
        # Если не найдено по (min_year, max_year, gender), проверяем по name и gender
        # (для совместимости со старыми записями, где могут быть NULL в min_year/max_year)
        if not result:
            cur.execute(
                "SELECT id FROM age_category WHERE name = %s AND gender = %s",
                (category["name"], category["gender"])
            )
            old_result = cur.fetchone()
            
            # Если нашли старую запись с таким же name и gender, обновляем её min_year и max_year
            if old_result:
                age_id = old_result[0]
                print(f"  -> Обновление существующей категории '{category['name']} ({category['gender']})' с добавлением min_year/max_year...")
                try:
                    cur.execute(
                        "UPDATE age_category SET min_year = %s, max_year = %s WHERE id = %s",
                        (category["min_year"], category["max_year"], age_id)
                    )
                    result = old_result  # Используем обновленную запись
                    print(f"  -> Категория обновлена успешно.")
                except Exception as e:
                    print(f"  -> Предупреждение: не удалось обновить категорию: {e}")
                    result = None  # Продолжаем как новую запись

        if not result:
            cur.execute(
                """INSERT INTO age_category (name, min_year, max_year, gender, status)
                   VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                (category["name"], category["min_year"], category["max_year"], category["gender"], category["status"])
            )
            age_id = cur.fetchone()[0]
            print(f" -> Добавлена возрастная категория: {category['name']} ({category['gender']})")
            age_category_ids[(category["name"], category["gender"])] = age_id # Сохраняем ID

            # Добавляем весовые категории для только что созданной возрастной
            weights_to_add = WEIGHT_CATEGORIES_BY_NAME.get((category["name"], category["gender"]), []) # Получаем веса по имени и полу
            if weights_to_add:
                added_weights_count = 0
                for weight in weights_to_add:
                    # Проверяем, существует ли уже такая весовая категория
                    cur.execute(
                        "SELECT id FROM weight_category WHERE age_category_id = %s AND weight = %s",
                        (age_id, weight)
                    )
                    if not cur.fetchone():
                        cur.execute(
                            "INSERT INTO weight_category (age_category_id, weight) VALUES (%s, %s)",
                            (age_id, weight)
                        )
                        added_weights_count += 1
                if added_weights_count > 0:
                     print(f"    -> Добавлено весовых категорий: {added_weights_count} шт.")
        else:
            age_id = result[0]
            print(f"Возрастная категория '{category['name']} ({category['gender']})' уже существует.")
            age_category_ids[(category["name"], category["gender"])] = age_id # Сохраняем существующий ID

            # Проверяем и добавляем весовые категории для существующей возрастной
            weights_to_add = WEIGHT_CATEGORIES_BY_NAME.get((category["name"], category["gender"]), []) # Получаем веса по имени и полу
            if weights_to_add:
                added_weights_count = 0
                for weight in weights_to_add:
                    cur.execute(
                        "SELECT id FROM weight_category WHERE age_category_id = %s AND weight = %s",
                        (age_id, weight)
                    )
                    if not cur.fetchone():
                        cur.execute(
                            "INSERT INTO weight_category (age_category_id, weight) VALUES (%s, %s)",
                            (age_id, weight)
                        )
                        added_weights_count += 1
                if added_weights_count > 0:
                    print(f"    -> Добавлено весовых категорий для существующей возрастной: {added_weights_count} шт.")

if __name__ == "__main__":
    seed_data()
