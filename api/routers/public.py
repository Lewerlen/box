import os
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import FileResponse
from typing import Optional

from db.database import (
    get_db_connection,
    get_participant_by_id,
    get_participants_for_bracket,
    get_approved_statuses,
    get_custom_bracket_order,
)
from db.cache import (
    get_age_categories_from_cache,
    get_weight_categories_from_cache,
    get_classes_from_cache,
    get_ranks_from_cache,
    get_regions_from_cache,
    get_cities_from_cache,
    get_clubs_from_cache,
    get_coaches_from_cache,
    get_all_clubs_from_cache,
)
from utils.formatters import format_weight
from utils.draw_bracket import get_seeded_participants, draw_bracket_image

router = APIRouter()


@router.get("/participants")
def list_participants(
    page: int = Query(1, ge=1),
    search: Optional[str] = None,
    gender: Optional[str] = None,
    age_category_id: Optional[int] = None,
    weight_category_id: Optional[int] = None,
    class_id: Optional[int] = None,
    club_id: Optional[int] = None,
    region_id: Optional[int] = None,
    competition_id: Optional[int] = None,
):
    conn = get_db_connection()
    cur = conn.cursor()
    page_size = 20
    offset = (page - 1) * page_size

    where_clauses = []
    params = []

    if search:
        where_clauses.append("p.fio ILIKE %s")
        params.append(f"%{search}%")
    if gender:
        where_clauses.append("p.gender = %s")
        params.append(gender)
    if age_category_id:
        where_clauses.append("p.age_category_id = %s")
        params.append(age_category_id)
    if weight_category_id:
        where_clauses.append("p.weight_category_id = %s")
        params.append(weight_category_id)
    if class_id:
        where_clauses.append("p.class_id = %s")
        params.append(class_id)
    if club_id:
        where_clauses.append("p.club_id = %s")
        params.append(club_id)
    if region_id:
        where_clauses.append("p.region_id = %s")
        params.append(region_id)
    if competition_id:
        where_clauses.append("p.competition_id = %s")
        params.append(competition_id)

    where_sql = " AND ".join(where_clauses)
    if where_sql:
        where_sql = "WHERE " + where_sql

    count_sql = f"SELECT COUNT(*) FROM participant p {where_sql}"
    cur.execute(count_sql, tuple(params))
    total_records = cur.fetchone()[0]

    query = f"""
        SELECT
            p.id, p.fio, p.gender, p.dob,
            ac.name as age_category_name,
            wc.weight,
            c.name as class_name,
            r.name as region_name,
            ci.name as city_name,
            cl.name as club_name,
            co.name as coach_name,
            p.rank_title
        FROM participant p
        LEFT JOIN age_category ac ON p.age_category_id = ac.id
        LEFT JOIN weight_category wc ON p.weight_category_id = wc.id
        LEFT JOIN class c ON p.class_id = c.id
        LEFT JOIN region r ON p.region_id = r.id
        LEFT JOIN city ci ON p.city_id = ci.id
        LEFT JOIN club cl ON p.club_id = cl.id
        LEFT JOIN coach co ON p.coach_id = co.id
        {where_sql}
        ORDER BY p.fio
        LIMIT %s OFFSET %s
    """
    cur.execute(query, tuple(params) + (page_size, offset))

    columns = [
        "id", "fio", "gender", "dob", "age_category_name",
        "weight", "class_name", "region_name", "city_name",
        "club_name", "coach_name", "rank_title"
    ]
    participants = []
    for row in cur.fetchall():
        p = dict(zip(columns, row))
        if p.get("dob"):
            p["dob"] = p["dob"].isoformat()
        if p.get("weight"):
            p["weight"] = format_weight(p["weight"])
        participants.append(p)

    total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 1

    cur.close()
    conn.close()
    return {
        "participants": participants,
        "total": total_records,
        "page": page,
        "total_pages": total_pages,
    }


@router.get("/participants/{participant_id}")
def get_participant(participant_id: int):
    p = get_participant_by_id(participant_id)
    if not p:
        raise HTTPException(status_code=404, detail="Участник не найден")
    if p.get("dob"):
        p["dob"] = p["dob"].isoformat()
    return p


@router.get("/references/age-categories")
def get_age_categories():
    return get_age_categories_from_cache()


@router.get("/references/weight-categories")
def get_weight_categories(age_category_id: int):
    return get_weight_categories_from_cache(age_category_id)


@router.get("/references/classes")
def get_classes():
    return get_classes_from_cache()


@router.get("/references/ranks")
def get_ranks():
    return get_ranks_from_cache()


@router.get("/references/regions")
def get_regions():
    return get_regions_from_cache()


@router.get("/references/cities")
def get_cities(region_id: int):
    return get_cities_from_cache(region_id)


@router.get("/references/clubs")
def get_clubs(city_id: Optional[int] = None):
    if city_id:
        return get_clubs_from_cache(city_id)
    return get_all_clubs_from_cache()


@router.get("/references/coaches")
def get_coaches(club_id: int):
    return get_coaches_from_cache(club_id)


@router.get("/brackets/approved")
def get_approved_brackets(competition_id: Optional[int] = None):
    approved = get_approved_statuses(competition_id=competition_id)
    result = []
    for item in approved:
        result.append({
            "class_name": item[0],
            "gender": item[1],
            "age_category_name": item[2],
            "weight_name": item[3],
        })
    return result


@router.get("/brackets/image")
def get_bracket_image(
    class_name: str,
    gender: str,
    age_category_name: str,
    weight_name: str,
    competition_id: Optional[int] = None,
):
    category_key = (class_name, gender, age_category_name, weight_name)
    approved_set = get_approved_statuses(competition_id=competition_id)
    if category_key not in approved_set:
        raise HTTPException(status_code=403, detail="Эта сетка ещё не утверждена")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM age_category WHERE name = %s AND gender = %s", (age_category_name, gender))
    age_result = cur.fetchone()
    if not age_result:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Возрастная категория не найдена")
    age_cat_id = age_result[0]

    weight_value = weight_name.replace("+", "").replace("кг", "").replace(" ", "").strip()
    try:
        weight_float = float(weight_value)
    except ValueError:
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Неверный формат веса")

    cur.execute("SELECT id FROM weight_category WHERE age_category_id = %s AND weight = %s",
                (age_cat_id, weight_float))
    wc_result = cur.fetchone()
    if not wc_result:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Весовая категория не найдена")
    weight_cat_id = wc_result[0]

    cur.execute("SELECT id FROM class WHERE name = %s", (class_name,))
    class_result = cur.fetchone()
    if not class_result:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Класс не найден")
    cls_id = class_result[0]

    cur.close()
    conn.close()

    participants = get_participants_for_bracket(age_cat_id, weight_cat_id, cls_id, competition_id=competition_id)
    if not participants:
        raise HTTPException(status_code=404, detail="Нет участников в этой категории")

    category_key = (class_name, gender, age_category_name, weight_name)
    custom_order = get_custom_bracket_order(category_key, competition_id=competition_id)

    if custom_order:
        conn2 = get_db_connection()
        cur2 = conn2.cursor()
        ordered = []
        for pid in custom_order:
            if pid is None:
                ordered.append(None)
                continue
            cur2.execute("""
                SELECT p.fio, cl.name as club_name, ci.name as city_name, c.name as class_name
                FROM participant p
                LEFT JOIN club cl ON p.club_id = cl.id
                LEFT JOIN city ci ON p.city_id = ci.id
                LEFT JOIN class c ON p.class_id = c.id
                WHERE p.id = %s
            """, (pid,))
            row = cur2.fetchone()
            if row:
                ordered.append({"id": pid, "fio": row[0], "club_name": row[1], "city_name": row[2], "class_name": row[3]})
            else:
                ordered.append(None)
        cur2.close()
        conn2.close()
        seeded = ordered
    else:
        seeded = get_seeded_participants(participants)

    gender_text = "муж." if gender == "Мужской" else "жен."
    header_info = {
        "line1": "Чемпионат и Первенство\nреспублики Башкортостан по муайтай",
        "line2": f"Категория {class_name}",
        "line3": f"{gender_text}, {age_category_name} лет",
        "line4": f"{weight_name} кг",
    }

    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "temp_files")
    os.makedirs(temp_dir, exist_ok=True)
    safe_name = f"{class_name}_{gender}_{age_category_name}_{weight_name}".replace(" ", "_").replace("+", "plus")
    file_path = os.path.join(temp_dir, f"bracket_{safe_name}.png")

    draw_bracket_image(seeded, file_path, header_info=header_info)

    return FileResponse(file_path, media_type="image/png")


@router.get("/stats")
def get_stats():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM participant")
    total_participants = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT club_id) FROM participant WHERE club_id IS NOT NULL")
    total_clubs = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT region_id) FROM participant WHERE region_id IS NOT NULL")
    total_regions = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM participant WHERE gender = 'Мужской'")
    male_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM participant WHERE gender = 'Женский'")
    female_count = cur.fetchone()[0]

    cur.close()
    conn.close()

    return {
        "total_participants": total_participants,
        "total_clubs": total_clubs,
        "total_regions": total_regions,
        "male_count": male_count,
        "female_count": female_count,
    }
