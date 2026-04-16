import os
import psycopg2
from psycopg2 import errors as psycopg2_errors
from dotenv import load_dotenv
from utils.formatters import format_weight, normalize_class_name

# Загружаем переменные окружения из .env файла
load_dotenv()

def get_db_connection():
    """Ð£ÑÑÐ°Ð½Ð°Ð²Ð»Ð¸Ð²Ð°ÐµÑ ÑÐ¾ÐµÐ´Ð¸Ð½ÐµÐ½Ð¸Ðµ Ñ Ð±Ð°Ð·Ð¾Ð¹ Ð´Ð°Ð½Ð½ÑÑ."""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        conn = psycopg2.connect(database_url)
    else:
        conn = psycopg2.connect(
            host=os.getenv("PGHOST", os.getenv("POSTGRES_HOST", "localhost")),
            database=os.getenv("PGDATABASE", os.getenv("POSTGRES_DB")),
            user=os.getenv("PGUSER", os.getenv("POSTGRES_USER")),
            password=os.getenv("PGPASSWORD", os.getenv("POSTGRES_PASSWORD")),
            port=os.getenv("PGPORT", os.getenv("POSTGRES_PORT", "5432"))
        )
    return conn

def migrate_participant_table(cur):
    """Добавляет недостающие колонки в таблицу participant."""
    try:
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'participant'
        """)
        existing_columns = {row[0] for row in cur.fetchall()}

        if 'competition_id' not in existing_columns:
            print("  -> Добавление колонки competition_id в participant...")
            cur.execute("""
                ALTER TABLE participant 
                ADD COLUMN competition_id INTEGER REFERENCES competitions(id) ON DELETE SET NULL
            """)

        cur.execute("""
            SELECT constraint_name FROM information_schema.table_constraints
            WHERE table_name = 'participant' AND constraint_type = 'UNIQUE'
              AND constraint_name = 'participant_fio_dob_key'
        """)
        if cur.fetchone():
            print("  -> Обновление уникального ограничения participant: (fio, dob) -> (fio, dob, competition_id)...")
            cur.execute("ALTER TABLE participant DROP CONSTRAINT participant_fio_dob_key")
            cur.execute("""
                ALTER TABLE participant
                ADD CONSTRAINT participant_fio_dob_competition_unique
                UNIQUE NULLS NOT DISTINCT (fio, dob, competition_id)
            """)
    except Exception as e:
        print(f"  -> Предупреждение при миграции participant: {e}")


def migrate_bracket_tables(cur):
    """Добавляет competition_id в таблицы approved_grids и custom_brackets."""
    try:
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'approved_grids'
        """)
        ag_cols = {row[0] for row in cur.fetchall()}

        if 'competition_id' not in ag_cols:
            print("  -> Добавление competition_id в approved_grids...")
            cur.execute("ALTER TABLE approved_grids DROP CONSTRAINT approved_grids_pkey")
            cur.execute("ALTER TABLE approved_grids ADD COLUMN ag_id SERIAL")
            cur.execute("ALTER TABLE approved_grids ADD PRIMARY KEY (ag_id)")
            cur.execute("""
                ALTER TABLE approved_grids
                ADD COLUMN competition_id INTEGER REFERENCES competitions(id) ON DELETE CASCADE
            """)
            cur.execute("""
                ALTER TABLE approved_grids
                ADD CONSTRAINT approved_grids_comp_unique
                UNIQUE NULLS NOT DISTINCT (competition_id, class_name, gender, age_category_name, weight_name)
            """)

        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'custom_brackets'
        """)
        cb_cols = {row[0] for row in cur.fetchall()}

        if 'competition_id' not in cb_cols:
            print("  -> Добавление competition_id в custom_brackets...")
            cur.execute("""
                ALTER TABLE custom_brackets
                DROP CONSTRAINT custom_brackets_class_name_gender_age_category_name_weight__key
            """)
            cur.execute("""
                ALTER TABLE custom_brackets
                ADD COLUMN competition_id INTEGER REFERENCES competitions(id) ON DELETE CASCADE
            """)
            cur.execute("""
                ALTER TABLE custom_brackets
                ADD CONSTRAINT custom_brackets_comp_unique
                UNIQUE NULLS NOT DISTINCT (competition_id, class_name, gender, age_category_name, weight_name)
            """)
    except Exception as e:
        print(f"  -> Предупреждение при миграции bracket таблиц: {e}")


def migrate_age_category_table(cur):
    """Добавляет недостающие колонки в таблицу age_category, если они отсутствуют."""
    try:
        # Проверяем существование колонок
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'age_category'
        """)
        existing_columns = {row[0] for row in cur.fetchall()}
        
        # Добавляем недостающие колонки
        if 'min_year' not in existing_columns:
            print("  -> Добавление колонки min_year в age_category...")
            cur.execute("ALTER TABLE age_category ADD COLUMN min_year INTEGER;")
        
        if 'max_year' not in existing_columns:
            print("  -> Добавление колонки max_year в age_category...")
            cur.execute("ALTER TABLE age_category ADD COLUMN max_year INTEGER;")
        
        if 'gender' not in existing_columns:
            print("  -> Добавление колонки gender в age_category...")
            cur.execute("ALTER TABLE age_category ADD COLUMN gender VARCHAR(10);")
        
        # Добавляем уникальное ограничение, если его нет
        cur.execute("""
            SELECT constraint_name 
            FROM information_schema.table_constraints 
            WHERE table_name = 'age_category' 
            AND constraint_type = 'UNIQUE'
            AND constraint_name LIKE '%min_year%'
        """)
        if not cur.fetchone():
            print("  -> Добавление уникального ограничения на (min_year, max_year, gender)...")
            try:
                cur.execute("""
                    ALTER TABLE age_category 
                    ADD CONSTRAINT age_category_unique_years_gender 
                    UNIQUE (min_year, max_year, gender);
                """)
            except Exception as e:
                # Если не получилось (например, из-за NULL значений), пропускаем
                print(f"  -> Предупреждение: не удалось добавить уникальное ограничение: {e}")
        
    except Exception as e:
        print(f"  -> Предупреждение при миграции age_category: {e}")

def create_tables():
    """Создает все таблицы в базе данных, удаляя старые при необходимости."""
    # Удаляем таблицы в обратном порядке зависимостей
    # drop_commands = (
    #     "DROP TABLE IF EXISTS custom_brackets CASCADE;",
    #     "DROP TABLE IF EXISTS approved_grids CASCADE;",
    #     "DROP TABLE IF EXISTS participant CASCADE;",
    #     "DROP TABLE IF EXISTS weight_category CASCADE;",
    #     "DROP TABLE IF EXISTS age_category CASCADE;",
    #     "DROP TABLE IF EXISTS class CASCADE;",
    #     "DROP TABLE IF EXISTS ranks CASCADE;",
    #     "DROP TABLE IF EXISTS coach CASCADE;",
    #     "DROP TABLE IF EXISTS club CASCADE;",
    #     "DROP TABLE IF EXISTS city CASCADE;",
    #     "DROP TABLE IF EXISTS region CASCADE;",
    # )
    # Команды создания
    create_commands = (
        """
        CREATE TABLE IF NOT EXISTS region (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            tgid_who_added BIGINT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS city (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            region_id INTEGER REFERENCES region(id),
            tgid_who_added BIGINT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS club (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            city_id INTEGER REFERENCES city(id),
            tgid_who_added BIGINT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS coach (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            club_id INTEGER REFERENCES club(id),
            tgid_who_added BIGINT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS ranks (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            status BOOLEAN DEFAULT TRUE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS class (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            status BOOLEAN DEFAULT TRUE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS age_category (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            min_year INTEGER,
            max_year INTEGER,
            gender VARCHAR(10),
            status BOOLEAN DEFAULT TRUE,
            UNIQUE (min_year, max_year, gender)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS weight_category (
            id SERIAL PRIMARY KEY,
            age_category_id INTEGER NOT NULL REFERENCES age_category(id) ON DELETE CASCADE,
            weight NUMERIC(5, 2) NOT NULL,
            UNIQUE (age_category_id, weight)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS participant (
            id SERIAL PRIMARY KEY,
            fio VARCHAR(255) NOT NULL,
            gender VARCHAR(10),
            dob DATE,
            age_category_id INTEGER REFERENCES age_category(id),
            weight_category_id INTEGER REFERENCES weight_category(id),
            region_id INTEGER REFERENCES region(id),
            city_id INTEGER REFERENCES city(id),
            club_id INTEGER REFERENCES club(id),
            coach_id INTEGER REFERENCES coach(id),
            class_id INTEGER REFERENCES class(id),
            rank_title VARCHAR(255),
            rank_assigned_on DATE,
            order_number VARCHAR(255),
            added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            added_by BIGINT,
            updated_at TIMESTAMP WITH TIME ZONE,
            updated_by BIGINT,
            UNIQUE (fio, dob)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS approved_grids (
            class_name VARCHAR(255) NOT NULL,
            gender VARCHAR(10) NOT NULL,
            age_category_name VARCHAR(255) NOT NULL,
            weight_name VARCHAR(255) NOT NULL,
            PRIMARY KEY (class_name, gender, age_category_name, weight_name)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS custom_brackets (
            id SERIAL PRIMARY KEY,
            class_name VARCHAR(255) NOT NULL,
            gender VARCHAR(10) NOT NULL,
            age_category_name VARCHAR(255) NOT NULL,
            weight_name VARCHAR(255) NOT NULL,
            participant_ids INTEGER[] NOT NULL,
            last_updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE (class_name, gender, age_category_name, weight_name)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS patronymic_exceptions (
            id SERIAL PRIMARY KEY,
            suffix VARCHAR(255) NOT NULL UNIQUE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS competitions (
            id SERIAL PRIMARY KEY,
            name VARCHAR(500) NOT NULL,
            discipline VARCHAR(50) NOT NULL DEFAULT 'muay_thai',
            date_start DATE,
            date_end DATE,
            location VARCHAR(500),
            status VARCHAR(20) NOT NULL DEFAULT 'upcoming',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
    )
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # # Сначала удаляем старые таблицы
        # print("Удаление существующих таблиц (если есть)...")
        # for command in drop_commands:
        #     cur.execute(command)
        print("Проверка и создание таблиц (если необходимо)...")  # Изменен текст

        for command in create_commands:
            try:
                cur.execute(command)
            except psycopg2_errors.DuplicateTable:
                # Таблица уже существует, пропускаем
                pass
            except Exception as e:
                # Для CREATE TABLE IF NOT EXISTS ошибка DuplicateTable не должна возникать
                # Но на всякий случай обрабатываем другие ошибки
                error_msg = str(e)
                if "already exists" in error_msg.lower():
                    # Таблица уже существует, пропускаем
                    pass
                else:
                    # Другая ошибка - выводим предупреждение
                    print(f"  -> Предупреждение при создании таблицы: {e}")
        
        # Миграции для существующих таблиц
        migrate_age_category_table(cur)
        migrate_participant_table(cur)
        migrate_bracket_tables(cur)

        # Проверка схемы — быстрый сбой при отсутствии критичных колонок/ограничений
        required_columns = {
            'participant': ['competition_id'],
            'approved_grids': ['competition_id'],
            'custom_brackets': ['competition_id'],
        }
        for table, cols in required_columns.items():
            cur.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
                (table,),
            )
            existing = {row[0] for row in cur.fetchall()}
            missing = [c for c in cols if c not in existing]
            if missing:
                raise RuntimeError(
                    f"Проверка схемы не прошла: {table}.{', '.join(missing)} отсутствует. "
                    "Необходима миграция базы данных."
                )

        required_constraints = [
            ('participant', 'participant_fio_dob_competition_unique'),
            ('approved_grids', 'approved_grids_comp_unique'),
            ('custom_brackets', 'custom_brackets_comp_unique'),
        ]
        cur.execute("""
            SELECT table_name, constraint_name
            FROM information_schema.table_constraints
            WHERE constraint_type = 'UNIQUE'
              AND table_name = ANY(%s)
        """, ([t for t, _ in required_constraints],))
        found_constraints = {(row[0], row[1]) for row in cur.fetchall()}
        for table, cname in required_constraints:
            if (table, cname) not in found_constraints:
                raise RuntimeError(
                    f"Проверка схемы не прошла: ограничение {cname} на таблице {table} отсутствует. "
                    "Необходима миграция базы данных."
                )

        cur.close()
        conn.commit()
        print("Проверка/создание таблиц завершено.")
    except RuntimeError:
        if conn:
            conn.rollback()
        raise
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Ошибка при создании таблиц: {error}") # Уточнено сообщение об ошибке
        if conn:
            conn.rollback() # Откатываем транзакцию при ошибке
    finally:
        if conn is not None:
            conn.close()

def save_participant_data(participant_data: dict, tgid_who_added: int) -> str:
    """
    Сохраняет данные участника. Если участник с таким ФИО и датой рождения
    существует, обновляет его данные. В противном случае, создает новую запись.
    Также обрабатывает "найти или создать" для связанных сущностей (регион, город и т.д.).
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # --- Логика "Найти или создать" для связанных сущностей ---
            # Класс
            if class_name := participant_data.get("class_name"):
                # Нормализуем название класса перед поиском
                class_name_normalized = normalize_class_name(class_name)
                # Ищем по полному и точному совпадению
                cur.execute("SELECT id FROM class WHERE name = %s", (class_name_normalized,))
                if result := cur.fetchone():
                    participant_data["class_id"] = result[0]

            # # Возрастная категория
            # if age_category_name := participant_data.get("age_category_name"):
            #     cur.execute(
            #         "SELECT id FROM age_category WHERE name = %s AND gender = %s",
            #         (age_category_name, participant_data.get("gender"))
            #     )
            #     if result := cur.fetchone():
            #         age_category_id = result[0]
            #         participant_data["age_category_id"] = age_category_id
            #         # Весовая категория (зависит от возрастной)
            #         if weight_category_name := participant_data.get("weight_category_name"):
            #             # Извлекаем числовое значение веса
            #             weight_value_str = str(weight_category_name).replace('+', '').replace('кг', '').strip()
            #             try:
            #                 weight_value = float(weight_value_str)
            #                 cur.execute(
            #                     "SELECT id FROM weight_category WHERE age_category_id = %s AND weight = %s",
            #                     (age_category_id, weight_value)
            #                 )
            #                 if w_result := cur.fetchone():
            #                     participant_data["weight_category_id"] = w_result[0]
            #             except (ValueError, TypeError):
            #                 pass # Если не удалось преобразовать вес, пропускаем
            # Весовая категория (зависит от возрастной, которая определяется в хендлере)
                if age_category_id := participant_data.get("age_category_id"):  # Проверяем наличие ID
                        if weight_category_name := participant_data.get("weight_category_name"):
                            # Извлекаем числовое значение веса
                            weight_value_str = str(weight_category_name).replace('+', '').replace('кг', '').strip()
                            try:
                                weight_value = float(weight_value_str)
                                cur.execute(
                                    "SELECT id FROM weight_category WHERE age_category_id = %s AND weight = %s",
                                    (age_category_id, weight_value)
                                )
                                if w_result := cur.fetchone():
                                    participant_data["weight_category_id"] = w_result[0]
                            except (ValueError, TypeError):
                                pass  # Если не удалось преобразовать вес, пропускаем

                    # Регион

            # Регион
            if region_name := participant_data.get("region_name"):
                cur.execute("SELECT id FROM region WHERE name = %s", (region_name,))
                if result := cur.fetchone():
                    participant_data["region_id"] = result[0]
                else:
                    cur.execute(
                        "INSERT INTO region (name, tgid_who_added) VALUES (%s, %s) RETURNING id",
                        (region_name, tgid_who_added),
                    )
                    participant_data["region_id"] = cur.fetchone()[0]

            # Город (зависит от региона)
            if city_name := participant_data.get("city_name"):
                if region_id := participant_data.get("region_id"):
                    cur.execute("SELECT id FROM city WHERE name = %s AND region_id = %s", (city_name, region_id))
                    if result := cur.fetchone():
                        participant_data["city_id"] = result[0]
                    else:
                        cur.execute(
                            "INSERT INTO city (name, region_id, tgid_who_added) VALUES (%s, %s, %s) RETURNING id",
                            (city_name, region_id, tgid_who_added),
                        )
                        participant_data["city_id"] = cur.fetchone()[0]

            # Клуб (зависит от города)
            if club_name := participant_data.get("club_name"):
                if city_id := participant_data.get("city_id"):
                    cur.execute("SELECT id FROM club WHERE name = %s AND city_id = %s", (club_name, city_id))
                    if result := cur.fetchone():
                        participant_data["club_id"] = result[0]
                    else:
                        cur.execute(
                            "INSERT INTO club (name, city_id, tgid_who_added) VALUES (%s, %s, %s) RETURNING id",
                            (club_name, city_id, tgid_who_added),
                        )
                        participant_data["club_id"] = cur.fetchone()[0]

            # Тренер (зависит от клуба)
            if coach_name := participant_data.get("coach_name"):
                if club_id := participant_data.get("club_id"):
                    # В CSV могут быть несколько тренеров, берем первого для простоты
                    # Можно улучшить, разбив строку и создав/найдя каждого
                    first_coach_name = ' '.join(coach_name.split(' ')[:2]) if len(coach_name.split(' ')) > 1 else coach_name
                    cur.execute("SELECT id FROM coach WHERE name = %s AND club_id = %s", (first_coach_name, club_id))
                    if result := cur.fetchone():
                        participant_data["coach_id"] = result[0]
                    else:
                        cur.execute(
                            "INSERT INTO coach (name, club_id, tgid_who_added) VALUES (%s, %s, %s) RETURNING id",
                            (first_coach_name, club_id, tgid_who_added),
                        )
                        participant_data["coach_id"] = cur.fetchone()[0]


            # --- Проверка существования участника (с учётом соревнования) ---
            competition_id = participant_data.get("competition_id")
            if competition_id is not None:
                cur.execute(
                    "SELECT id FROM participant WHERE fio = %s AND dob = %s AND competition_id = %s",
                    (participant_data["fio"], participant_data["dob"], competition_id),
                )
            else:
                cur.execute(
                    "SELECT id FROM participant WHERE fio = %s AND dob = %s AND competition_id IS NULL",
                    (participant_data["fio"], participant_data["dob"]),
                )
            existing_participant = cur.fetchone()

            fields = {
                "fio": participant_data.get("fio"),
                "gender": participant_data.get("gender"),
                "dob": participant_data.get("dob"),
                "age_category_id": participant_data.get("age_category_id"),
                "weight_category_id": participant_data.get("weight_category_id"),
                "region_id": participant_data.get("region_id"),
                "city_id": participant_data.get("city_id"),
                "club_id": participant_data.get("club_id"),
                "coach_id": participant_data.get("coach_id"),
                "class_id": participant_data.get("class_id"),
                "rank_title": participant_data.get("rank_name"),
                "rank_assigned_on": participant_data.get("rank_assigned_on"),
                "order_number": participant_data.get("order_number"),
                "competition_id": participant_data.get("competition_id"),
            }

            if existing_participant:
                participant_id = existing_participant[0]
                fields['updated_by'] = tgid_who_added
                # Фильтруем поля, чтобы обновлять только те, что не None
                update_fields = {k: v for k, v in fields.items() if v is not None}
                set_clause = ", ".join([f"{key} = %s" for key in update_fields])

                if set_clause: # Убедимся, что есть что обновлять
                    sql = f"UPDATE participant SET {set_clause}, updated_at = NOW() WHERE id = %s"
                    cur.execute(sql, (*update_fields.values(), participant_id))

                status = "updated"
            else:
                # Для новой записи, None значения будут вставлены как NULL
                fields['added_by'] = tgid_who_added
                columns = ", ".join(fields.keys())
                placeholders = ", ".join(["%s"] * len(fields))
                sql = f"INSERT INTO participant ({columns}) VALUES ({placeholders})"
                cur.execute(sql, tuple(fields.values()))
                status = "created"

            conn.commit()
            return status

    except (Exception, psycopg2.DatabaseError) as error:
        conn.rollback()
        print(f"Ошибка транзакции: {error}")
        raise
    finally:
        if conn is not None:
            conn.close()

def update_participant_by_id(participant_id: int, participant_data: dict, tgid_who_updated: int):
    """
    Обновляет данные существующего участника по его ID.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # --- Логика "Найти или создать" для связанных сущностей ---
            if class_name := participant_data.get("class_name"):
                # Нормализуем название класса перед поиском
                class_name_normalized = normalize_class_name(class_name)
                cur.execute("SELECT id FROM class WHERE name = %s", (class_name_normalized,))
                if result := cur.fetchone():
                    participant_data["class_id"] = result[0]

            # if age_category_name := participant_data.get("age_category_name"):
            #     cur.execute(
            #         "SELECT id FROM age_category WHERE name = %s AND gender = %s",
            #         (age_category_name, participant_data.get("gender"))
            #     )
            #     if result := cur.fetchone():
            #         age_category_id = result[0]
            #         participant_data["age_category_id"] = age_category_id
            #         if weight_category_name := participant_data.get("weight_category_name"):
            #             weight_value = ''.join(filter(str.isdigit, weight_category_name.split('+')[0]))
            #             if weight_value:
            #                 cur.execute(
            #                     "SELECT id FROM weight_category WHERE age_category_id = %s AND weight::text LIKE %s",
            #                     (age_category_id, f"{weight_value}%")
            #                 )
            #                 if w_result := cur.fetchone():
            #                     participant_data["weight_category_id"] = w_result[0]
            #
            # if region_name := participant_data.get("region_name"):

            # Весовая категория (зависит от возрастной, которая определяется в хендлере)
            if age_category_id := participant_data.get("age_category_id"):
                if weight_category_name := participant_data.get("weight_category_name"):
                    weight_value_str = str(weight_category_name).replace('+', '').replace('кг', '').strip()
                    try:
                        weight_value = float(weight_value_str)
                        cur.execute(
                            "SELECT id FROM weight_category WHERE age_category_id = %s AND weight = %s",
                            (age_category_id, weight_value)
                        )
                        if w_result := cur.fetchone():
                            participant_data["weight_category_id"] = w_result[0]
                    except (ValueError, TypeError):
                        pass
            if region_name := participant_data.get("region_name"):
                cur.execute("SELECT id FROM region WHERE name = %s", (region_name,))
                if result := cur.fetchone():
                    participant_data["region_id"] = result[0]
                else:
                    cur.execute(
                        "INSERT INTO region (name, tgid_who_added) VALUES (%s, %s) RETURNING id",
                        (region_name, tgid_who_updated),
                    )
                    participant_data["region_id"] = cur.fetchone()[0]

            if city_name := participant_data.get("city_name"):
                if region_id := participant_data.get("region_id"):
                    cur.execute("SELECT id FROM city WHERE name = %s AND region_id = %s",
                                (city_name, region_id))
                    if result := cur.fetchone():
                        participant_data["city_id"] = result[0]
                    else:
                        cur.execute(
                            "INSERT INTO city (name, region_id, tgid_who_added) VALUES (%s, %s, %s) RETURNING id",
                            (city_name, region_id, tgid_who_updated),
                        )
                        participant_data["city_id"] = cur.fetchone()[0]

            if club_name := participant_data.get("club_name"):
                if city_id := participant_data.get("city_id"):
                    cur.execute("SELECT id FROM club WHERE name = %s AND city_id = %s",
                                (club_name, city_id))
                    if result := cur.fetchone():
                        participant_data["club_id"] = result[0]
                    else:
                        cur.execute(
                            "INSERT INTO club (name, city_id, tgid_who_added) VALUES (%s, %s, %s) RETURNING id",
                            (club_name, city_id, tgid_who_updated),
                        )
                        participant_data["club_id"] = cur.fetchone()[0]

            if coach_name := participant_data.get("coach_name"):
                if club_id := participant_data.get("club_id"):
                    cur.execute("SELECT id FROM coach WHERE name = %s AND club_id = %s",
                                (coach_name, club_id))
                    if result := cur.fetchone():
                        participant_data["coach_id"] = result[0]
                    else:
                        cur.execute(
                            "INSERT INTO coach (name, club_id, tgid_who_added) VALUES (%s, %s, %s) RETURNING id",
                            (coach_name, club_id, tgid_who_updated),
                        )
                        participant_data["coach_id"] = cur.fetchone()[0]

            # --- Подготовка полей для обновления ---
            fields = {
                "fio": participant_data.get("fio"),
                "gender": participant_data.get("gender"),
                "dob": participant_data.get("dob"),
                "age_category_id": participant_data.get("age_category_id"),
                "weight_category_id": participant_data.get("weight_category_id"),
                "region_id": participant_data.get("region_id"),
                "city_id": participant_data.get("city_id"),
                "club_id": participant_data.get("club_id"),
                "coach_id": participant_data.get("coach_id"),
                "class_id": participant_data.get("class_id"),
                "rank_title": participant_data.get("rank_title"),
                "rank_assigned_on": participant_data.get("rank_assigned_on"),
                "order_number": participant_data.get("order_number"),
                "updated_by": tgid_who_updated,
            }

            fields_to_update = {k: v for k, v in fields.items() if v is not None}

            if not fields_to_update:
                return

            set_clause = ", ".join([f"{key} = %s" for key in fields_to_update])
            sql = f"UPDATE participant SET {set_clause}, updated_at = NOW() WHERE id = %s"
            values = tuple(fields_to_update.values()) + (participant_id,)
            cur.execute(sql, values)

            conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        conn.rollback()
        print(f"Ошибка транзакции при обновлении: {error}")
        raise
    finally:
        if conn is not None:
            conn.close()

def get_participants(page: int = 1, search_query: str = None):
    """Возвращает список участников (id, fio), общее количество и число страниц."""
    conn = get_db_connection()
    cur = conn.cursor()
    offset = (page - 1) * 20
    total_records = 0

    if search_query:
        search_pattern = f"%{search_query}%"
        cur.execute("SELECT COUNT(*) FROM participant WHERE fio ILIKE %s", (search_pattern,))
        total_records = cur.fetchone()[0]
        cur.execute(
            "SELECT id, fio FROM participant WHERE fio ILIKE %s ORDER BY fio LIMIT 20 OFFSET %s",
            (search_pattern, offset),
        )
    else:
        cur.execute("SELECT COUNT(*) FROM participant")
        total_records = cur.fetchone()[0]
        cur.execute("SELECT id, fio FROM participant ORDER BY fio LIMIT 20 OFFSET %s", (offset,))

    participants = [{"id": row[0], "fio": row[1]} for row in cur.fetchall()]
    total_pages = (total_records + 19) // 20 if total_records > 0 else 1

    cur.close()
    conn.close()
    return participants, total_records, total_pages

def get_participant_by_id(participant_id: int):
    """Возвращает полную информацию об одном участнике по его ID."""
    conn = get_db_connection()
    cur = conn.cursor()
    query = """
            SELECT
                p.fio, p.gender, p.dob,
                ac.name as age_category_name, 
                p.age_category_id,
                wc.weight as weight_category_name,
                c.name as class_name,
                p.rank_title as rank_name,
                p.rank_assigned_on,
                p.order_number,
                r.name as region_name,
                p.region_id,
                ci.name as city_name,
                p.city_id,
                cl.name as club_name,
                co.name as coach_name,
                p.club_id
            FROM participant p
            LEFT JOIN age_category ac ON p.age_category_id = ac.id
            LEFT JOIN weight_category wc ON p.weight_category_id = wc.id
            LEFT JOIN class c ON p.class_id = c.id
            LEFT JOIN region r ON p.region_id = r.id
            LEFT JOIN city ci ON p.city_id = ci.id
            LEFT JOIN club cl ON p.club_id = cl.id
            LEFT JOIN coach co ON p.coach_id = co.id
            WHERE p.id = %s
        """
    cur.execute(query, (participant_id,))
    data = cur.fetchone()

    if not data:
        return None

    columns = [
        "fio", "gender", "dob", "age_category_name", "age_category_id",
        "weight_category_name", "class_name", "rank_name",
        "rank_assigned_on", "order_number", "region_name", "region_id",
        "city_name", "city_id", "club_name", "coach_name", "club_id"
    ]
    participant_dict = dict(zip(columns, data))

    if participant_dict.get("weight_category_name"):
        participant_dict["weight_category_name"] = format_weight(participant_dict["weight_category_name"])

    cur.close()
    conn.close()
    return participant_dict

def get_clubs(page: int = 1, search_query: str = None):
    conn = get_db_connection()
    cur = conn.cursor()
    page_size = 15
    offset = (page - 1) * page_size
    total_records = 0

    count_query_base = """
        SELECT COUNT(DISTINCT cl.id)
        FROM club cl
        JOIN participant p ON cl.id = p.club_id
    """
    select_query_base = """
        SELECT cl.id, cl.name
        FROM club cl
        JOIN participant p ON cl.id = p.club_id
    """
    filter_clause = ""
    params = []

    if search_query:
        search_pattern = f"%{search_query}%"
        filter_clause = " WHERE cl.name ILIKE %s"
        params.append(search_pattern)

    count_query = count_query_base + filter_clause + " GROUP BY cl.id HAVING COUNT(p.id) > 0"
    if params:
        cur.execute(f"SELECT COUNT(*) FROM ({count_query}) as sub", tuple(params))
    else:
        cur.execute(f"SELECT COUNT(*) FROM ({count_query}) as sub")

    total_records_result = cur.fetchone()
    total_records = total_records_result[0] if total_records_result else 0


    select_query = (select_query_base + filter_clause +
                    " GROUP BY cl.id, cl.name HAVING COUNT(p.id) > 0 ORDER BY cl.name LIMIT %s OFFSET %s")
    limit_offset_params = [page_size, offset]
    final_params = params + limit_offset_params

    cur.execute(select_query, tuple(final_params))


    clubs = [{"id": row[0], "name": row[1]} for row in cur.fetchall()]
    total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 1

    cur.close()
    conn.close()
    return clubs, total_records, total_pages

def get_participants_by_club(club_id: int, page: int = 1, search_query: str = None):
    """Возвращает список участников (id, fio) для клуба, общее количество и число страниц."""
    conn = get_db_connection()
    cur = conn.cursor()
    page_size = 20
    offset = (page - 1) * page_size
    total_records = 0
    base_query = "FROM participant WHERE club_id = %s"
    count_params = [club_id]
    select_params = [club_id]

    if search_query:
        search_pattern = f"%{search_query}%"
        base_query += " AND fio ILIKE %s"
        count_params.append(search_pattern)
        select_params.append(search_pattern)

    cur.execute(f"SELECT COUNT(*) {base_query}", tuple(count_params))
    total_records = cur.fetchone()[0]

    select_params.extend([page_size, offset])
    cur.execute(
        f"SELECT id, fio {base_query} ORDER BY fio LIMIT %s OFFSET %s",
        tuple(select_params),
    )

    participants = [{"id": row[0], "fio": row[1]} for row in cur.fetchall()]
    total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 1

    cur.close()
    conn.close()
    return participants, total_records, total_pages

def get_all_participants_for_report(competition_id: int = None):
    conn = get_db_connection()
    cur = conn.cursor()
    where_sql = ""
    params = []
    if competition_id is not None:
        where_sql = "WHERE p.competition_id = %s"
        params.append(competition_id)
    query = f"""
        SELECT
            p.fio,
            p.dob,
            p.rank_title,
            wc.weight as weight,
            c.name as class_name,
            p.gender,
            cl.name as club_name,
            ci.name as city_name,
            co.name as coach_name,
            ac.name as age_category_name
        FROM participant p
        LEFT JOIN age_category ac ON p.age_category_id = ac.id
        LEFT JOIN weight_category wc ON p.weight_category_id = wc.id
        LEFT JOIN class c ON p.class_id = c.id
        LEFT JOIN club cl ON p.club_id = cl.id
        LEFT JOIN city ci ON p.city_id = ci.id
        LEFT JOIN coach co ON p.coach_id = co.id
        {where_sql}
        ORDER BY ac.id, p.gender, wc.weight, c.id, p.fio;
    """
    cur.execute(query, tuple(params))
    columns = [
        "fio", "dob", "rank_title",
        "weight", "class_name", "gender", "club_name",
        "city_name", "coach_name", "age_category_name"
    ]
    participants = [dict(zip(columns, row)) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return participants

def get_participants_for_bracket(age_category_id: int, weight_category_id: int, class_id: int, competition_id: int = None):
    """Возвращает список участников (fio, club_name) для конкретной категории."""
    conn = get_db_connection()
    cur = conn.cursor()
    where = "p.age_category_id = %s AND p.weight_category_id = %s AND p.class_id = %s"
    params = [age_category_id, weight_category_id, class_id]
    if competition_id is not None:
        where += " AND p.competition_id = %s"
        params.append(competition_id)
    query = f"""
                SELECT
                    p.id,
                    p.fio,
                    cl.name as club_name,
                    ci.name as city_name,
                    c.name as class_name
                FROM participant p
                LEFT JOIN club cl ON p.club_id = cl.id
                LEFT JOIN city ci ON p.city_id = ci.id
                LEFT JOIN class c ON p.class_id = c.id
                WHERE {where}
                ORDER BY p.fio;
            """
    cur.execute(query, params)
    columns = ["id", "fio", "club_name", "city_name", "class_name"]
    participants = [dict(zip(columns, row)) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return participants

def delete_participant_by_id(participant_id: int):
    """Удаляет участника из базы данных по его ID."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM participant WHERE id = %s", (participant_id,))
            conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        conn.rollback()
        print(f"Ошибка при удалении участника: {error}")
        raise
    finally:
        if conn is not None:
            conn.close()

def get_age_categories_with_participants():
    """Возвращает возрастные категории с количеством участников в каждой."""
    conn = get_db_connection()
    cur = conn.cursor()
    query = """
        SELECT ac.id, ac.name, ac.gender, COUNT(p.id) as participant_count
        FROM age_category ac
        JOIN participant p ON p.age_category_id = ac.id
        GROUP BY ac.id, ac.name, ac.gender
        ORDER BY ac.id;
    """
    cur.execute(query)
    columns = ["id", "name", "gender", "participant_count"]
    categories = [dict(zip(columns, row)) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return categories

def get_weight_categories_with_participants(age_category_id: int):
    """Возвращает весовые категории с количеством участников в каждой."""
    conn = get_db_connection()
    cur = conn.cursor()
    query = """
        SELECT wc.id, wc.weight, COUNT(p.id) as participant_count
        FROM weight_category wc
        JOIN participant p ON p.weight_category_id = wc.id
        WHERE wc.age_category_id = %s
        GROUP BY wc.id, wc.weight
        ORDER BY wc.weight;
    """
    cur.execute(query, (age_category_id,))
    # Форматируем вес и добавляем количество
    categories = [{
        "id": row[0],
        "name": format_weight(row[1]),
        "participant_count": row[2]
    } for row in cur.fetchall()]
    cur.close()
    conn.close()
    return categories

def get_classes_with_participants(age_category_id: int, weight_category_id: int = None):
    """Возвращает классы с количеством участников в каждом для данной категории."""
    conn = get_db_connection()
    cur = conn.cursor()
    if weight_category_id is None:
        # Получаем классы только по возрастной категории
        query = """
            SELECT c.id, c.name, COUNT(p.id) as participant_count
            FROM class c
            JOIN participant p ON p.class_id = c.id
            WHERE p.age_category_id = %s
            GROUP BY c.id, c.name
            ORDER BY c.id;
        """
        cur.execute(query, (age_category_id,))
    else:
        # Получаем классы по возрастной и весовой категории
        query = """
            SELECT c.id, c.name, COUNT(p.id) as participant_count
            FROM class c
            JOIN participant p ON p.class_id = c.id
            WHERE p.age_category_id = %s AND p.weight_category_id = %s
            GROUP BY c.id, c.name
            ORDER BY c.id;
        """
        cur.execute(query, (age_category_id, weight_category_id))
    columns = ["id", "name", "participant_count"]
    classes = [dict(zip(columns, row)) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return classes

def get_weight_categories_with_participants_by_class(age_category_id: int, class_id: int):
    """Возвращает весовые категории с количеством участников в каждой для данной возрастной категории и класса."""
    conn = get_db_connection()
    cur = conn.cursor()
    query = """
        SELECT wc.id, wc.weight, COUNT(p.id) as participant_count
        FROM weight_category wc
        JOIN participant p ON p.weight_category_id = wc.id
        WHERE wc.age_category_id = %s AND p.class_id = %s
        GROUP BY wc.id, wc.weight
        ORDER BY wc.weight;
    """
    cur.execute(query, (age_category_id, class_id))
    # Форматируем вес и добавляем количество
    categories = [{
        "id": row[0],
        "name": format_weight(row[1]),
        "participant_count": row[2]
    } for row in cur.fetchall()]
    cur.close()
    conn.close()
    return categories



def get_participants_for_approval(competition_id: int = None):
    conn = get_db_connection()
    cur = conn.cursor()
    where = "p.age_category_id IS NOT NULL AND p.weight_category_id IS NOT NULL AND p.class_id IS NOT NULL"
    params = []
    if competition_id is not None:
        where += " AND p.competition_id = %s"
        params.append(competition_id)
    query = f"""
            SELECT
                p.id,
                p.fio,
                p.gender,
                p.dob,
                ac.id as age_category_id,
                ac.name as age_category_name,
                wc.id as weight_category_id,
                wc.weight as weight,
                c.id as class_id,
                c.name as class_name,
                p.rank_title,
                cl.name as club_name,
                ci.name as city_name,
                co.name as coach_name
            FROM participant p
            LEFT JOIN age_category ac ON p.age_category_id = ac.id
            LEFT JOIN weight_category wc ON p.weight_category_id = wc.id
            LEFT JOIN class c ON p.class_id = c.id
            LEFT JOIN club cl ON p.club_id = cl.id
            LEFT JOIN city ci ON p.city_id = ci.id
            LEFT JOIN coach co ON p.coach_id = co.id
            WHERE {where}
            ORDER BY p.gender ASC, c.id DESC, ac.max_year DESC, wc.weight ASC, p.fio;
        """
    cur.execute(query, params)
    columns = [
        "id",
        "fio", "gender", "dob", "age_category_id", "age_category_name",
        "weight_category_id", "weight", "class_id", "class_name", "rank_title",
        "club_name", "city_name", "coach_name"
    ]
    participants = [dict(zip(columns, row)) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return participants

def get_approved_statuses(competition_id: int = None) -> set:
    """Возвращает множество кортежей с ключами утвержденных сеток."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if competition_id is not None:
                cur.execute(
                    "SELECT class_name, gender, age_category_name, weight_name FROM approved_grids WHERE competition_id = %s",
                    (competition_id,)
                )
            else:
                cur.execute("SELECT class_name, gender, age_category_name, weight_name FROM approved_grids")
            return set(cur.fetchall())
    finally:
        if conn:
            conn.close()


def update_approval_status(category_key: tuple, is_approved: bool, competition_id: int = None):
    """Обновляет статус утверждения для конкретной сетки в БД."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            class_name, gender, age_category_name, weight_name = category_key
            if is_approved:
                cur.execute(
                    """
                    INSERT INTO approved_grids (competition_id, class_name, gender, age_category_name, weight_name)
                    VALUES (%s, %s, %s, %s, %s) ON CONFLICT ON CONSTRAINT approved_grids_comp_unique DO NOTHING
                    """,
                    (competition_id, class_name, gender, age_category_name, weight_name)
                )
            else:
                cur.execute(
                    """
                    DELETE FROM approved_grids
                    WHERE class_name = %s AND gender = %s AND age_category_name = %s AND weight_name = %s
                    AND (competition_id = %s OR (competition_id IS NULL AND %s IS NULL))
                    """,
                    (class_name, gender, age_category_name, weight_name, competition_id, competition_id)
                )
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Ошибка при обновлении статуса утверждения: {e}")
    finally:
        if conn:
            conn.close()



def save_custom_bracket_order(category_key: tuple, participant_ids: list[int], competition_id: int = None):
    """
    Сохраняет или обновляет порядок ID участников для заданной категории в таблице custom_brackets.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            class_name, gender, age_category_name, weight_name = category_key
            cur.execute(
                """
                INSERT INTO custom_brackets (competition_id, class_name, gender, age_category_name, weight_name, participant_ids, last_updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT ON CONSTRAINT custom_brackets_comp_unique
                DO UPDATE SET
                    participant_ids = EXCLUDED.participant_ids,
                    last_updated_at = NOW();
                """,
                (competition_id, class_name, gender, age_category_name, weight_name, participant_ids)
            )
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Ошибка при сохранении пользовательского порядка сетки: {e}")
    finally:
        if conn:
            conn.close()

def get_custom_bracket_order(category_key: tuple, competition_id: int = None) -> list[int] | None:
    """
    Извлекает сохраненный порядок ID участников для категории.
    Возвращает список ID или None, если запись не найдена.
    """
    conn = get_db_connection()
    participant_ids = None
    try:
        with conn.cursor() as cur:
            class_name, gender, age_category_name, weight_name = category_key
            cur.execute(
                """
                SELECT participant_ids FROM custom_brackets
                WHERE class_name = %s AND gender = %s AND age_category_name = %s AND weight_name = %s
                AND (competition_id = %s OR (competition_id IS NULL AND %s IS NULL));
                """,
                (class_name, gender, age_category_name, weight_name, competition_id, competition_id)
            )
            result = cur.fetchone()
            if result:
                participant_ids = result[0]
    except Exception as e:
        print(f"Ошибка при получении пользовательского порядка сетки: {e}")
    finally:
        if conn:
            conn.close()
    return participant_ids

def delete_custom_bracket_order(category_key: tuple, competition_id: int = None):
    """
    Удаляет запись о пользовательском порядке для категории.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            class_name, gender, age_category_name, weight_name = category_key
            cur.execute(
                """
                DELETE FROM custom_brackets
                WHERE class_name = %s AND gender = %s AND age_category_name = %s AND weight_name = %s
                AND (competition_id = %s OR (competition_id IS NULL AND %s IS NULL));
                """,
                (class_name, gender, age_category_name, weight_name, competition_id, competition_id)
            )
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Ошибка при удалении пользовательского порядка сетки: {e}")
    finally:
        if conn:
            conn.close()

def get_patronymic_exceptions() -> list[str]:
    """
    Возвращает список суффиксов отчеств из таблицы patronymic_exceptions.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT suffix FROM patronymic_exceptions")
            return [row[0] for row in cur.fetchall()]
    except Exception as e:
        print(f"Ошибка при получении исключений отчеств: {e}")
        return []
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    create_tables()
