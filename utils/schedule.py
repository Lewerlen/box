"""
Сервис для расписания боёв: извлечение пар первого круга из одобренных сеток.
"""
from collections import defaultdict
from db.database import (
    get_db_connection,
    get_participants_for_approval,
    get_approved_statuses,
    get_custom_bracket_order,
    get_participants_for_bracket,
)
from utils.formatters import format_weight
from utils.draw_bracket import get_seeded_participants


ROUND_LABELS = {
    2: "Финал",
    4: "1/2",
    8: "1/4",
    16: "1/8",
    32: "1/16",
    64: "1/32",
}


def _round_label_for_size(bracket_size: int) -> str:
    return ROUND_LABELS.get(bracket_size, f"1/{bracket_size // 2}")


def _bracket_size(n: int) -> int:
    if n <= 1:
        return 2
    s = 1
    while s < n:
        s *= 2
    return s


def _resolve_category_ids(cur, class_name, gender, age_category_name, weight_name):
    cur.execute("SELECT id FROM age_category WHERE name = %s AND gender = %s",
                (age_category_name, gender))
    r = cur.fetchone()
    if not r:
        return None
    age_id = r[0]
    weight_value = weight_name.replace("+", "").replace("кг", "").replace(" ", "").strip()
    try:
        weight_float = float(weight_value)
    except ValueError:
        return None
    cur.execute("SELECT id FROM weight_category WHERE age_category_id = %s AND weight = %s",
                (age_id, weight_float))
    r = cur.fetchone()
    if not r:
        return None
    weight_id = r[0]
    cur.execute("SELECT id FROM class WHERE name = %s", (class_name,))
    r = cur.fetchone()
    if not r:
        return None
    return age_id, weight_id, r[0]


def _hydrate_participants(cur, ids: list[int]) -> dict:
    if not ids:
        return {}
    cur.execute("""
        SELECT p.id, p.fio, cl.name as club_name, ci.name as city_name,
               r.name as region_name, c.name as class_name
        FROM participant p
        LEFT JOIN club cl ON p.club_id = cl.id
        LEFT JOIN city ci ON p.city_id = ci.id
        LEFT JOIN region r ON p.region_id = r.id
        LEFT JOIN class c ON p.class_id = c.id
        WHERE p.id = ANY(%s)
    """, (list(ids),))
    rows = cur.fetchall()
    out = {}
    for row in rows:
        out[row[0]] = {
            "id": row[0],
            "fio": row[1],
            "club_name": row[2],
            "city_name": row[3],
            "region_name": row[4],
            "class_name": row[5],
        }
    return out


def get_first_round_pairs(competition_id: int) -> list[dict]:
    """
    Возвращает список пар первого круга по всем одобренным сеткам соревнования.
    Пары с BYE (без обоих бойцов) пропускаются.
    """
    participants = get_participants_for_approval(competition_id=competition_id)
    approved = get_approved_statuses(competition_id=competition_id)
    if not approved:
        return []

    grouped = defaultdict(list)
    for p in participants:
        key = (
            p.get("class_name", ""),
            p.get("gender", ""),
            p.get("age_category_name", ""),
            format_weight(p.get("weight")),
        )
        grouped[key].append(p)

    conn = get_db_connection()
    cur = conn.cursor()

    pairs: list[dict] = []
    try:
        for category_key, parts in grouped.items():
            if category_key not in approved:
                continue
            class_name, gender, age_cat_name, weight_name = category_key

            ids = _resolve_category_ids(cur, class_name, gender, age_cat_name, weight_name)
            if not ids:
                continue
            age_id, weight_id, class_id = ids

            full_parts = get_participants_for_bracket(age_id, weight_id, class_id, competition_id=competition_id)
            custom_order = get_custom_bracket_order(category_key, competition_id=competition_id)

            if custom_order:
                by_id = {p["id"]: p for p in full_parts}
                seeded = []
                for pid in custom_order:
                    if pid is None:
                        seeded.append(None)
                    else:
                        seeded.append(by_id.get(pid))
            else:
                seeded = get_seeded_participants(full_parts)

            bracket_size = len(seeded) if seeded else _bracket_size(len(full_parts))
            round_label = _round_label_for_size(bracket_size)

            for i in range(0, len(seeded), 2):
                a = seeded[i] if i < len(seeded) else None
                b = seeded[i + 1] if i + 1 < len(seeded) else None
                if not a or not b:
                    continue
                slot_index = i // 2
                pair_key = f"{class_name}|{gender}|{age_cat_name}|{weight_name}|{slot_index}"
                pairs.append({
                    "pair_key": pair_key,
                    "class_name": class_name,
                    "gender": gender,
                    "age_category_name": age_cat_name,
                    "weight_name": weight_name,
                    "round_label": round_label,
                    "slot_index": slot_index,
                    "fighter1_id": a["id"],
                    "fighter2_id": b["id"],
                    "fighter1": {
                        "id": a["id"],
                        "fio": a.get("fio"),
                        "club_name": a.get("club_name"),
                        "city_name": a.get("city_name"),
                    },
                    "fighter2": {
                        "id": b["id"],
                        "fio": b.get("fio"),
                        "club_name": b.get("club_name"),
                        "city_name": b.get("city_name"),
                    },
                })
    finally:
        cur.close()
        conn.close()

    return pairs


def get_scheduled_pair_keys(competition_id: int) -> set:
    """Возвращает множество ключей пар (без учёта порядка бойцов), которые уже распределены."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT class_name, gender, age_category_name, weight_name, fighter1_id, fighter2_id
            FROM fight_schedule
            WHERE competition_id = %s
        """, (competition_id,))
        out = set()
        for row in cur.fetchall():
            f1, f2 = row[4], row[5]
            lo, hi = min(f1, f2), max(f1, f2)
            out.add((row[0], row[1], row[2], row[3], lo, hi))
        return out
    finally:
        cur.close()
        conn.close()


def pair_key_for_fight(class_name, gender, age_category_name, weight_name, fighter1_id, fighter2_id):
    lo, hi = min(fighter1_id, fighter2_id), max(fighter1_id, fighter2_id)
    return (class_name, gender, age_category_name, weight_name, lo, hi)


def get_full_schedule(competition_id: int) -> dict:
    """Полное расписание соревнования: рингам + дни + бои с деталями участников."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, name, sort_order
            FROM competition_rings
            WHERE competition_id = %s
            ORDER BY sort_order, id
        """, (competition_id,))
        rings = [{"id": r[0], "name": r[1], "sort_order": r[2]} for r in cur.fetchall()]

        cur.execute("""
            SELECT id, ring_id, day_number, fight_order, fighter1_id, fighter2_id,
                   class_name, gender, age_category_name, weight_name, round_label
            FROM fight_schedule
            WHERE competition_id = %s
            ORDER BY day_number, ring_id, fight_order, id
        """, (competition_id,))
        rows = cur.fetchall()

        all_ids = set()
        for row in rows:
            all_ids.add(row[4]); all_ids.add(row[5])
        people = _hydrate_participants(cur, list(all_ids))

        fights = []
        for row in rows:
            f1 = people.get(row[4])
            f2 = people.get(row[5])
            fights.append({
                "id": row[0],
                "ring_id": row[1],
                "day_number": row[2],
                "fight_order": row[3],
                "fighter1_id": row[4],
                "fighter2_id": row[5],
                "class_name": row[6],
                "gender": row[7],
                "age_category_name": row[8],
                "weight_name": row[9],
                "round_label": row[10],
                "fighter1": f1,
                "fighter2": f2,
            })

        return {"rings": rings, "fights": fights}
    finally:
        cur.close()
        conn.close()
