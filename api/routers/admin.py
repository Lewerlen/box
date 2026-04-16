import os
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from api.auth import get_current_admin
from db.database import (
    get_db_connection,
    get_participant_by_id,
    save_participant_data,
    update_participant_by_id,
    delete_participant_by_id,
    get_all_participants_for_report,
    get_participants_for_approval,
    get_approved_statuses,
    update_approval_status,
    save_custom_bracket_order,
    get_custom_bracket_order,
    delete_custom_bracket_order,
    get_participants_for_bracket,
)
from db.cache import update_cache
from utils.formatters import format_weight
from utils.draw_bracket import get_seeded_participants, draw_bracket_image
from utils.excel_generator import (
    generate_preliminary_list_excel,
    generate_weigh_in_list_excel,
    generate_all_brackets_excel,
    generate_protocol_excel,
)
from utils.csv_importer import process_csv_import

router = APIRouter()


TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "temp_files")
os.makedirs(TEMP_DIR, exist_ok=True)


class ParticipantCreate(BaseModel):
    fio: str
    gender: str
    dob: str
    age_category_id: int
    weight_category_id: int
    class_name: str
    rank_name: Optional[str] = None
    region_name: str
    city_name: str
    club_name: str
    coach_name: str
    competition_id: Optional[int] = None


class ParticipantUpdate(BaseModel):
    fio: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[str] = None
    age_category_id: Optional[int] = None
    weight_category_id: Optional[int] = None
    class_name: Optional[str] = None
    rank_name: Optional[str] = None
    region_name: Optional[str] = None
    city_name: Optional[str] = None
    club_name: Optional[str] = None
    coach_name: Optional[str] = None


@router.get("/participants")
def admin_list_participants(
    page: int = Query(1, ge=1),
    search: Optional[str] = None,
    gender: Optional[str] = None,
    age_category_id: Optional[int] = None,
    class_id: Optional[int] = None,
    competition_id: Optional[int] = None,
    admin: str = Depends(get_current_admin),
):
    conn = get_db_connection()
    cur = conn.cursor()
    page_size = 50
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
    if class_id:
        where_clauses.append("p.class_id = %s")
        params.append(class_id)
    if competition_id:
        where_clauses.append("p.competition_id = %s")
        params.append(competition_id)

    where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    cur.execute(f"SELECT COUNT(*) FROM participant p {where_sql}", tuple(params))
    total = cur.fetchone()[0]

    cur.execute(f"""
        SELECT
            p.id, p.fio, p.gender, p.dob,
            ac.name as age_category_name,
            wc.weight,
            c.name as class_name,
            r.name as region_name,
            ci.name as city_name,
            cl.name as club_name,
            co.name as coach_name,
            p.rank_title,
            p.weight_category_id,
            p.age_category_id,
            p.class_id,
            p.competition_id,
            comp.name as competition_name
        FROM participant p
        LEFT JOIN age_category ac ON p.age_category_id = ac.id
        LEFT JOIN weight_category wc ON p.weight_category_id = wc.id
        LEFT JOIN class c ON p.class_id = c.id
        LEFT JOIN region r ON p.region_id = r.id
        LEFT JOIN city ci ON p.city_id = ci.id
        LEFT JOIN club cl ON p.club_id = cl.id
        LEFT JOIN coach co ON p.coach_id = co.id
        LEFT JOIN competitions comp ON p.competition_id = comp.id
        {where_sql}
        ORDER BY p.id DESC
        LIMIT %s OFFSET %s
    """, tuple(params) + (page_size, offset))

    columns = [
        "id", "fio", "gender", "dob", "age_category_name",
        "weight", "class_name", "region_name", "city_name",
        "club_name", "coach_name", "rank_title",
        "weight_category_id", "age_category_id", "class_id",
        "competition_id", "competition_name"
    ]
    participants = []
    for row in cur.fetchall():
        p = dict(zip(columns, row))
        if p.get("dob"):
            p["dob"] = p["dob"].isoformat()
        if p.get("weight"):
            p["weight"] = format_weight(p["weight"])
        participants.append(p)

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    cur.close()
    conn.close()
    return {"participants": participants, "total": total, "page": page, "total_pages": total_pages}


@router.post("/participants")
def admin_create_participant(data: ParticipantCreate, admin: str = Depends(get_current_admin)):
    try:
        participant_data = {
            "fio": data.fio.strip(),
            "gender": data.gender,
            "dob": data.dob,
            "age_category_id": data.age_category_id,
            "weight_category_id": data.weight_category_id,
            "weight_category_name": None,
            "class_name": data.class_name,
            "rank_name": data.rank_name,
            "region_name": data.region_name,
            "city_name": data.city_name,
            "club_name": data.club_name,
            "coach_name": data.coach_name,
            "competition_id": data.competition_id,
        }
        status = save_participant_data(participant_data, tgid_who_added=0)
        update_cache()
        return {"status": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/participants/{participant_id}")
def admin_get_participant(participant_id: int, admin: str = Depends(get_current_admin)):
    p = get_participant_by_id(participant_id)
    if not p:
        raise HTTPException(status_code=404, detail="Участник не найден")
    if p.get("dob"):
        p["dob"] = p["dob"].isoformat()
    return p


@router.put("/participants/{participant_id}")
def admin_update_participant(participant_id: int, data: ParticipantUpdate, admin: str = Depends(get_current_admin)):
    update_data = data.dict(exclude_none=True)
    if "rank_name" in update_data:
        update_data["rank_title"] = update_data.pop("rank_name")
    if not update_data:
        raise HTTPException(status_code=400, detail="Нет данных для обновления")
    try:
        update_participant_by_id(participant_id, update_data, tgid_who_updated=0)
        update_cache()
        return {"status": "updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/participants/{participant_id}")
def admin_delete_participant(participant_id: int, admin: str = Depends(get_current_admin)):
    try:
        delete_participant_by_id(participant_id)
        update_cache()
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import-csv")
async def import_csv(file: UploadFile = File(...), admin: str = Depends(get_current_admin)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Только CSV файлы")

    temp_path = os.path.join(TEMP_DIR, f"import_{file.filename}")

    contents = await file.read()
    with open(temp_path, "wb") as f:
        f.write(contents)

    try:
        stats = await process_csv_import(temp_path, tgid_who_added=0)
        update_cache()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.get("/brackets/categories")
def get_bracket_categories(
    competition_id: Optional[int] = None,
    admin: str = Depends(get_current_admin),
):
    participants = get_participants_for_approval(competition_id=competition_id)
    approved_statuses = get_approved_statuses(competition_id=competition_id)

    grouped = defaultdict(list)
    for p in participants:
        key = (
            p.get("class_name", ""),
            p.get("gender", ""),
            p.get("age_category_name", ""),
            format_weight(p.get("weight")),
        )
        grouped[key].append(p)

    categories = []
    for key, parts in grouped.items():
        class_name, gender, age_cat_name, weight_name = key
        is_approved = key in approved_statuses
        categories.append({
            "class_name": class_name,
            "gender": gender,
            "age_category_name": age_cat_name,
            "weight_name": weight_name,
            "participant_count": len(parts),
            "approved": is_approved,
        })

    return categories


@router.get("/brackets/detail")
def get_bracket_detail(
    class_name: str,
    gender: str,
    age_category_name: str,
    weight_name: str,
    competition_id: Optional[int] = None,
    admin: str = Depends(get_current_admin),
):
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
    category_key = (class_name, gender, age_category_name, weight_name)
    custom_order = get_custom_bracket_order(category_key, competition_id=competition_id)
    is_approved = category_key in get_approved_statuses(competition_id=competition_id)

    if custom_order:
        conn2 = get_db_connection()
        cur2 = conn2.cursor()
        ordered = []
        for pid in custom_order:
            if pid is None:
                ordered.append(None)
                continue
            cur2.execute("""
                SELECT p.id, p.fio, cl.name as club_name, ci.name as city_name, c.name as class_name
                FROM participant p
                LEFT JOIN club cl ON p.club_id = cl.id
                LEFT JOIN city ci ON p.city_id = ci.id
                LEFT JOIN class c ON p.class_id = c.id
                WHERE p.id = %s
            """, (pid,))
            row = cur2.fetchone()
            if row:
                ordered.append({"id": row[0], "fio": row[1], "club_name": row[2], "city_name": row[3], "class_name": row[4]})
            else:
                ordered.append(None)
        cur2.close()
        conn2.close()
        seeded = ordered
    else:
        seeded = get_seeded_participants(participants)

    return {
        "participants": seeded,
        "approved": is_approved,
        "category_key": {
            "class_name": class_name,
            "gender": gender,
            "age_category_name": age_category_name,
            "weight_name": weight_name,
        }
    }


@router.post("/brackets/swap")
def swap_participants(
    class_name: str,
    gender: str,
    age_category_name: str,
    weight_name: str,
    index_a: int,
    index_b: int,
    competition_id: Optional[int] = None,
    admin: str = Depends(get_current_admin),
):
    category_key = (class_name, gender, age_category_name, weight_name)

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM age_category WHERE name = %s AND gender = %s", (age_category_name, gender))
    age_result = cur.fetchone()
    if not age_result:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404)
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
    custom_order = get_custom_bracket_order(category_key, competition_id=competition_id)

    if custom_order:
        ids_list = custom_order
    else:
        seeded = get_seeded_participants(participants)
        ids_list = [p["id"] if p else None for p in seeded]

    if 0 <= index_a < len(ids_list) and 0 <= index_b < len(ids_list):
        ids_list[index_a], ids_list[index_b] = ids_list[index_b], ids_list[index_a]

    save_custom_bracket_order(category_key, ids_list, competition_id=competition_id)
    return {"status": "swapped"}


@router.post("/brackets/approve")
def toggle_approval(
    class_name: str,
    gender: str,
    age_category_name: str,
    weight_name: str,
    competition_id: Optional[int] = None,
    admin: str = Depends(get_current_admin),
):
    category_key = (class_name, gender, age_category_name, weight_name)
    current_approved = get_approved_statuses(competition_id=competition_id)
    is_currently_approved = category_key in current_approved
    update_approval_status(category_key, not is_currently_approved, competition_id=competition_id)
    return {"approved": not is_currently_approved}


@router.post("/brackets/regenerate")
def regenerate_bracket(
    class_name: str,
    gender: str,
    age_category_name: str,
    weight_name: str,
    competition_id: Optional[int] = None,
    admin: str = Depends(get_current_admin),
):
    category_key = (class_name, gender, age_category_name, weight_name)
    delete_custom_bracket_order(category_key, competition_id=competition_id)
    return {"status": "regenerated"}


@router.get("/excel/preliminary")
def download_preliminary_excel(
    competition_id: Optional[int] = None,
    admin: str = Depends(get_current_admin),
):
    participants = get_all_participants_for_report(competition_id=competition_id)
    file_path = os.path.join(TEMP_DIR, "preliminary_list.xlsx")
    generate_preliminary_list_excel(participants, file_path)
    return FileResponse(file_path, filename="preliminary_list.xlsx",
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@router.get("/excel/weigh-in")
def download_weigh_in_excel(
    competition_id: Optional[int] = None,
    admin: str = Depends(get_current_admin),
):
    participants = get_all_participants_for_report(competition_id=competition_id)
    file_path = os.path.join(TEMP_DIR, "weigh_in_list.xlsx")
    generate_weigh_in_list_excel(participants, file_path)
    return FileResponse(file_path, filename="weigh_in_list.xlsx",
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@router.get("/excel/brackets")
def download_brackets_excel(
    competition_id: Optional[int] = None,
    admin: str = Depends(get_current_admin),
):
    participants = get_participants_for_approval(competition_id=competition_id)
    approved_statuses = get_approved_statuses(competition_id=competition_id)

    grouped = defaultdict(list)
    for p in participants:
        key = (
            p.get("class_name", ""),
            p.get("gender", ""),
            p.get("age_category_name", ""),
            format_weight(p.get("weight")),
        )
        grouped[key].append(p)

    bracket_data = {}
    for category_key, parts in grouped.items():
        custom_order = get_custom_bracket_order(category_key, competition_id=competition_id)
        if custom_order:
            conn = get_db_connection()
            cur = conn.cursor()
            ordered = []
            for pid in custom_order:
                if pid is None:
                    ordered.append(None)
                    continue
                cur.execute("""
                    SELECT p.id, p.fio, cl.name as club_name, ci.name as city_name,
                           c.name as class_name, p.rank_title
                    FROM participant p
                    LEFT JOIN club cl ON p.club_id = cl.id
                    LEFT JOIN city ci ON p.city_id = ci.id
                    LEFT JOIN class c ON p.class_id = c.id
                    WHERE p.id = %s
                """, (pid,))
                row = cur.fetchone()
                if row:
                    ordered.append({"id": row[0], "fio": row[1], "club_name": row[2],
                                    "city_name": row[3], "class_name": row[4], "rank_title": row[5]})
                else:
                    ordered.append(None)
            cur.close()
            conn.close()
            bracket_data[category_key] = ordered
        else:
            bracket_data[category_key] = get_seeded_participants(parts)

    file_path = os.path.join(TEMP_DIR, "all_brackets.xlsx")
    generate_all_brackets_excel(bracket_data, file_path)
    return FileResponse(file_path, filename="all_brackets.xlsx",
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@router.get("/excel/protocol")
def download_protocol_excel(
    competition_id: Optional[int] = None,
    admin: str = Depends(get_current_admin),
):
    participants = get_all_participants_for_report(competition_id=competition_id)
    file_path = os.path.join(TEMP_DIR, "protocol.xlsx")
    generate_protocol_excel(participants, file_path)
    return FileResponse(file_path, filename="protocol.xlsx",
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@router.get("/brackets/image")
def admin_get_bracket_image(
    class_name: str,
    gender: str,
    age_category_name: str,
    weight_name: str,
    competition_id: Optional[int] = None,
    admin: str = Depends(get_current_admin),
):
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

    safe_name = f"{competition_id}_{class_name}_{gender}_{age_category_name}_{weight_name}".replace(" ", "_").replace("+", "plus")
    file_path = os.path.join(TEMP_DIR, f"bracket_{safe_name}.png")
    draw_bracket_image(seeded, file_path, header_info=header_info)

    return FileResponse(file_path, media_type="image/png",
                        filename=f"bracket_{safe_name}.png")
