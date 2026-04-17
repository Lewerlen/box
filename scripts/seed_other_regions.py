"""Idempotently add clubs and coaches for cities outside Bashkortostan,
so test participants can come from various regions.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import get_db_connection

# city_name -> [(club_name, [coach1, coach2, ...]), ...]
DATA = {
    "Ижевск": [
        ("Ижсталь", ["Соловьёв А.В.", "Петров Р.Н."]),
        ("Молот", ["Захаров И.С."]),
    ],
    "Оренбург": [
        ("Оренбург-Файт", ["Тимофеев К.А.", "Шакиров Р.М."]),
        ("Кочевник", ["Быков А.Ю."]),
    ],
    "Сорочинск": [
        ("Сорочинск Спорт", ["Орлов В.П."]),
    ],
    "Самара": [
        ("Самара Муай Тай", ["Климов Д.А.", "Никитин С.В."]),
        ("Волга-Файт", ["Семёнов А.К."]),
    ],
    "Ульяновск": [
        ("Ульяновск Бойцы", ["Ларионов М.С.", "Воронин П.Е."]),
    ],
}

def main():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM city")
    city_id_by_name = {r[1]: r[0] for r in cur.fetchall()}

    added_clubs = 0
    added_coaches = 0
    for city_name, clubs in DATA.items():
        cid = city_id_by_name.get(city_name)
        if not cid:
            print(f"⚠ город не найден: {city_name}")
            continue
        for club_name, coaches in clubs:
            cur.execute("SELECT id FROM club WHERE name=%s AND city_id=%s", (club_name, cid))
            row = cur.fetchone()
            if row:
                club_id = row[0]
            else:
                cur.execute(
                    "INSERT INTO club (name, city_id, tgid_who_added) VALUES (%s,%s,%s) RETURNING id",
                    (club_name, cid, 0),
                )
                club_id = cur.fetchone()[0]
                added_clubs += 1
            for coach_name in coaches:
                cur.execute("SELECT id FROM coach WHERE name=%s AND club_id=%s", (coach_name, club_id))
                if not cur.fetchone():
                    cur.execute(
                        "INSERT INTO coach (name, club_id, tgid_who_added) VALUES (%s,%s,%s)",
                        (coach_name, club_id, 0),
                    )
                    added_coaches += 1
    conn.commit()
    print(f"Добавлено клубов: {added_clubs}, тренеров: {added_coaches}")
    cur.close(); conn.close()

if __name__ == "__main__":
    main()
