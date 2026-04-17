"""Seed ~110 test participants for competition #1 (Чемпионат и Первенство РБ по муайтай 2026).
Only classes А (id=1) and В (id=2). Uses existing cities/clubs/coaches/regions/ranks.
"""
import sys
import os
import random
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import get_db_connection
from db.cache import update_cache

random.seed(42)

COMP_ID = 1

MALE_FIRST = [
    "Артём", "Данил", "Тимур", "Ринат", "Ильдар", "Айдар", "Руслан", "Михаил",
    "Алексей", "Дмитрий", "Кирилл", "Никита", "Андрей", "Иван", "Максим",
    "Роберт", "Эмиль", "Радмир", "Азат", "Булат", "Ильнур", "Денис", "Глеб",
    "Артур", "Марсель", "Ринат", "Салават", "Камиль", "Рамиль", "Юрий",
]
FEMALE_FIRST = [
    "Алина", "Камилла", "Алсу", "Айгуль", "Эльвира", "Регина", "Лиана",
    "Карина", "Дарья", "Полина", "Анастасия", "Юлия", "Виктория", "Мария",
    "Софья", "Ксения", "Лилия", "Гульназ", "Аделина", "Ангелина",
]
LAST_M = [
    "Иванов", "Петров", "Хасанов", "Гимадиев", "Мухаметов", "Сафин",
    "Зарипов", "Юсупов", "Ахметов", "Мусин", "Кадыров", "Нургалиев",
    "Габдуллин", "Шарипов", "Гайфуллин", "Сулейманов", "Ибрагимов",
    "Тагиров", "Калимуллин", "Гайсин", "Каримов", "Шакиров", "Валиев",
    "Гарипов", "Закиров", "Зиннатуллин", "Рахимов", "Сабиров", "Хайруллин",
    "Файзуллин", "Бакиров", "Аминов", "Бикбаев",
]
PATR_M = [
    "Айратович", "Ринатович", "Рустемович", "Денисович", "Алексеевич",
    "Михайлович", "Ильдарович", "Артурович", "Маратович", "Робертович",
    "Раильевич", "Радикович", "Тагирович", "Камильевич", "Эмильевич",
    "Фаритович", "Салаватович", "Ильнурович",
]
PATR_F = [
    "Айратовна", "Ринатовна", "Рустемовна", "Денисовна", "Алексеевна",
    "Михайловна", "Ильдаровна", "Артуровна", "Маратовна", "Робертовна",
    "Раильевна", "Радиковна", "Тагировна", "Камильевна", "Эмильевна",
    "Фаритовна", "Салаватовна", "Ильнуровна",
]


def age_range(age_cat_name: str) -> tuple[int, int]:
    if age_cat_name == "8-9": return (8, 9)
    if age_cat_name == "10-11": return (10, 11)
    if age_cat_name == "12-13": return (12, 13)
    if age_cat_name == "14-15": return (14, 15)
    if age_cat_name == "16-17": return (16, 17)
    if age_cat_name == "старше 18": return (18, 25)
    return (10, 12)


def random_dob(age_min: int, age_max: int) -> date:
    today = date(2026, 4, 17)
    age = random.randint(age_min, age_max)
    year = today.year - age
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    # ensure birthday already happened
    return date(year, month, day)


def gen_fio(gender: str) -> str:
    if gender == "Мужской":
        return f"{random.choice(LAST_M)} {random.choice(MALE_FIRST)} {random.choice(PATR_M)}"
    else:
        last = random.choice(LAST_M) + "а"
        return f"{last} {random.choice(FEMALE_FIRST)} {random.choice(PATR_F)}"


def pick_rank(class_id: int) -> str:
    # А-класс — более высокие разряды; В — юношеские/3-2 спортивный
    if class_id == 1:
        pool = ["I юношеский", "III спортивный", "II спортивный", "I спортивный", "КМС", "КМС"]
    else:
        pool = ["III юношеский", "II юношеский", "I юношеский", "III спортивный"]
    return random.choice(pool)


# (class_id, age_cat_id, weight_cat_id, count)
GROUPS = [
    # Класс А (id=1) — 50 чел
    (1, 3, 32, 6),    # 12-13 М, 36
    (1, 3, 34, 8),    # 12-13 М, 40
    (1, 4, 71, 8),    # 14-15 М, 48
    (1, 4, 73, 6),    # 14-15 М, 54
    (1, 5, 87, 8),    # 16-17 М, 60
    (1, 6, 103, 6),   # 18+ М, 71
    (1, 9, 158, 4),   # 12-13 Ж, 40
    (1, 11, 190, 4),  # 16-17 Ж, 54
    # Класс В (id=2) — 60 чел
    (2, 2, 29, 8),    # 10-11 М, 30
    (2, 3, 33, 6),    # 12-13 М, 38
    (2, 4, 72, 8),    # 14-15 М, 51
    (2, 4, 74, 8),    # 14-15 М, 57
    (2, 5, 89, 6),    # 16-17 М, 67
    (2, 5, 91, 4),    # 16-17 М, 75
    (2, 6, 105, 6),   # 18+ М, 81
    (2, 8, 136, 4),   # 10-11 Ж, 30
    (2, 10, 177, 6),  # 14-15 Ж, 48
    (2, 11, 189, 4),  # 16-17 Ж, 51
]


def main():
    conn = get_db_connection()
    cur = conn.cursor()

    # check existing
    cur.execute("SELECT COUNT(*) FROM participant WHERE competition_id=%s", (COMP_ID,))
    existing = cur.fetchone()[0]
    if existing > 0:
        print(f"ВНИМАНИЕ: в соревновании уже есть {existing} участников. Прерывание.")
        conn.close()
        return

    # gender by age_cat_id
    cur.execute("SELECT id, gender FROM age_category")
    age_gender = {row[0]: row[1] for row in cur.fetchall()}

    # references
    cur.execute("SELECT id, region_id FROM city")
    cities = cur.fetchall()
    cur.execute("SELECT id, city_id FROM club")
    clubs = cur.fetchall()
    cur.execute("SELECT id, club_id FROM coach")
    coaches = cur.fetchall()

    city_by_id = {c[0]: c[1] for c in cities}
    clubs_by_city = {}
    for cl in clubs:
        clubs_by_city.setdefault(cl[1], []).append(cl[0])
    coaches_by_club = {}
    for co in coaches:
        coaches_by_club.setdefault(co[1], []).append(co[0])

    valid_cities = [c[0] for c in cities if clubs_by_city.get(c[0]) and any(coaches_by_club.get(cl) for cl in clubs_by_city[c[0]])]
    if not valid_cities:
        # fallback
        valid_cities = [c[0] for c in cities]

    # age category names for DOB
    cur.execute("SELECT id, name FROM age_category")
    age_name_by_id = {row[0]: row[1] for row in cur.fetchall()}

    inserted = 0
    for class_id, age_cat_id, weight_cat_id, count in GROUPS:
        gender = age_gender[age_cat_id]
        amin, amax = age_range(age_name_by_id[age_cat_id])
        for _ in range(count):
            fio = gen_fio(gender)
            dob = random_dob(amin, amax)

            # pick city -> club -> coach
            city_id = random.choice(valid_cities)
            region_id = city_by_id[city_id]
            club_pool = [cl for cl in clubs_by_city.get(city_id, []) if coaches_by_club.get(cl)]
            if not club_pool:
                club_pool = clubs_by_city.get(city_id, [None])
            club_id = random.choice(club_pool) if club_pool else None
            coach_id = random.choice(coaches_by_club.get(club_id, [None])) if club_id else None

            rank_title = pick_rank(class_id)

            cur.execute(
                """
                INSERT INTO participant (
                    fio, gender, dob, age_category_id, weight_category_id,
                    region_id, city_id, club_id, coach_id, class_id,
                    rank_title, competition_id, added_at, added_by
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, NOW(), 0)
                """,
                (
                    fio, gender, dob, age_cat_id, weight_cat_id,
                    region_id, city_id, club_id, coach_id, class_id,
                    rank_title, COMP_ID,
                ),
            )
            inserted += 1

    conn.commit()
    print(f"Создано участников: {inserted}")
    cur.close()
    conn.close()
    update_cache()
    print("Кэш обновлён.")


if __name__ == "__main__":
    main()
