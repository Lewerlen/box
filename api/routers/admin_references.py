from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from api.auth import get_current_admin
from db.database import get_db_connection
from db.cache import update_cache

router = APIRouter()


class RenameRequest(BaseModel):
    name: str


class CreateRequest(BaseModel):
    name: str
    parent_id: Optional[int] = None


class MergeRequest(BaseModel):
    target_id: int


def _close(cur, conn, invalidate_cache=False):
    cur.close()
    conn.close()
    if invalidate_cache:
        update_cache()


@router.get("/regions")
def list_regions(admin: str = Depends(get_current_admin)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT r.id, r.name, COUNT(p.id) as participant_count
        FROM region r
        LEFT JOIN participant p ON p.region_id = r.id
        GROUP BY r.id, r.name
        ORDER BY r.name
    """)
    rows = cur.fetchall()
    _close(cur, conn)
    return [{"id": r[0], "name": r[1], "count": r[2]} for r in rows]


@router.post("/regions")
def create_region(data: CreateRequest, admin: str = Depends(get_current_admin)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM region WHERE name = %s", (data.name.strip(),))
    if cur.fetchone():
        _close(cur, conn)
        raise HTTPException(status_code=400, detail="Регион с таким названием уже существует")
    cur.execute("INSERT INTO region (name) VALUES (%s) RETURNING id", (data.name.strip(),))
    new_id = cur.fetchone()[0]
    conn.commit()
    _close(cur, conn, invalidate_cache=True)
    return {"id": new_id, "name": data.name.strip()}


@router.put("/regions/{region_id}")
def rename_region(region_id: int, data: RenameRequest, admin: str = Depends(get_current_admin)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM region WHERE id = %s", (region_id,))
    if not cur.fetchone():
        _close(cur, conn)
        raise HTTPException(status_code=404, detail="Регион не найден")
    cur.execute("SELECT id FROM region WHERE name = %s AND id != %s", (data.name.strip(), region_id))
    if cur.fetchone():
        _close(cur, conn)
        raise HTTPException(status_code=400, detail="Регион с таким названием уже существует")
    cur.execute("UPDATE region SET name = %s WHERE id = %s", (data.name.strip(), region_id))
    conn.commit()
    _close(cur, conn, invalidate_cache=True)
    return {"status": "renamed"}


@router.delete("/regions/{region_id}")
def delete_region(region_id: int, admin: str = Depends(get_current_admin)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM region WHERE id = %s", (region_id,))
    if not cur.fetchone():
        _close(cur, conn)
        raise HTTPException(status_code=404, detail="Регион не найден")
    cur.execute("SELECT COUNT(*) FROM participant WHERE region_id = %s", (region_id,))
    count = cur.fetchone()[0]
    if count > 0:
        _close(cur, conn)
        raise HTTPException(status_code=400, detail=f"Нельзя удалить: {count} участник(ов) привязано. Сначала объедините.")
    cur.execute("DELETE FROM coach WHERE club_id IN (SELECT id FROM club WHERE city_id IN (SELECT id FROM city WHERE region_id = %s))", (region_id,))
    cur.execute("DELETE FROM club WHERE city_id IN (SELECT id FROM city WHERE region_id = %s)", (region_id,))
    cur.execute("DELETE FROM city WHERE region_id = %s", (region_id,))
    cur.execute("DELETE FROM region WHERE id = %s", (region_id,))
    conn.commit()
    _close(cur, conn, invalidate_cache=True)
    return {"status": "deleted"}


@router.post("/regions/{region_id}/merge")
def merge_region(region_id: int, data: MergeRequest, admin: str = Depends(get_current_admin)):
    if region_id == data.target_id:
        raise HTTPException(status_code=400, detail="Нельзя объединить с самим собой")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM region WHERE id = %s", (region_id,))
    if not cur.fetchone():
        _close(cur, conn)
        raise HTTPException(status_code=404, detail="Исходный регион не найден")
    cur.execute("SELECT id FROM region WHERE id = %s", (data.target_id,))
    if not cur.fetchone():
        _close(cur, conn)
        raise HTTPException(status_code=404, detail="Целевой регион не найден")
    cur.execute("SELECT COUNT(*) FROM participant WHERE region_id = %s", (region_id,))
    affected = cur.fetchone()[0]
    cur.execute("UPDATE participant SET region_id = %s WHERE region_id = %s", (data.target_id, region_id))
    cur.execute("UPDATE city SET region_id = %s WHERE region_id = %s", (data.target_id, region_id))
    cur.execute("DELETE FROM region WHERE id = %s", (region_id,))
    conn.commit()
    _close(cur, conn, invalidate_cache=True)
    return {"status": "merged", "affected": affected}


@router.get("/cities")
def list_cities(region_id: int = Query(...), admin: str = Depends(get_current_admin)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT c.id, c.name, COUNT(p.id) as participant_count
        FROM city c
        LEFT JOIN participant p ON p.city_id = c.id
        WHERE c.region_id = %s
        GROUP BY c.id, c.name
        ORDER BY c.name
    """, (region_id,))
    rows = cur.fetchall()
    _close(cur, conn)
    return [{"id": r[0], "name": r[1], "count": r[2]} for r in rows]


@router.post("/cities")
def create_city(data: CreateRequest, admin: str = Depends(get_current_admin)):
    if not data.parent_id:
        raise HTTPException(status_code=400, detail="Укажите region_id")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM city WHERE name = %s AND region_id = %s", (data.name.strip(), data.parent_id))
    if cur.fetchone():
        _close(cur, conn)
        raise HTTPException(status_code=400, detail="Город с таким названием уже существует в этом регионе")
    cur.execute("INSERT INTO city (name, region_id) VALUES (%s, %s) RETURNING id", (data.name.strip(), data.parent_id))
    new_id = cur.fetchone()[0]
    conn.commit()
    _close(cur, conn, invalidate_cache=True)
    return {"id": new_id, "name": data.name.strip()}


@router.put("/cities/{city_id}")
def rename_city(city_id: int, data: RenameRequest, admin: str = Depends(get_current_admin)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT region_id FROM city WHERE id = %s", (city_id,))
    row = cur.fetchone()
    if not row:
        _close(cur, conn)
        raise HTTPException(status_code=404, detail="Город не найден")
    cur.execute("SELECT id FROM city WHERE name = %s AND region_id = %s AND id != %s", (data.name.strip(), row[0], city_id))
    if cur.fetchone():
        _close(cur, conn)
        raise HTTPException(status_code=400, detail="Город с таким названием уже существует в этом регионе")
    cur.execute("UPDATE city SET name = %s WHERE id = %s", (data.name.strip(), city_id))
    conn.commit()
    _close(cur, conn, invalidate_cache=True)
    return {"status": "renamed"}


@router.delete("/cities/{city_id}")
def delete_city(city_id: int, admin: str = Depends(get_current_admin)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM city WHERE id = %s", (city_id,))
    if not cur.fetchone():
        _close(cur, conn)
        raise HTTPException(status_code=404, detail="Город не найден")
    cur.execute("SELECT COUNT(*) FROM participant WHERE city_id = %s", (city_id,))
    count = cur.fetchone()[0]
    if count > 0:
        _close(cur, conn)
        raise HTTPException(status_code=400, detail=f"Нельзя удалить: {count} участник(ов) привязано. Сначала объедините.")
    cur.execute("DELETE FROM coach WHERE club_id IN (SELECT id FROM club WHERE city_id = %s)", (city_id,))
    cur.execute("DELETE FROM club WHERE city_id = %s", (city_id,))
    cur.execute("DELETE FROM city WHERE id = %s", (city_id,))
    conn.commit()
    _close(cur, conn, invalidate_cache=True)
    return {"status": "deleted"}


@router.post("/cities/{city_id}/merge")
def merge_city(city_id: int, data: MergeRequest, admin: str = Depends(get_current_admin)):
    if city_id == data.target_id:
        raise HTTPException(status_code=400, detail="Нельзя объединить с самим собой")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT region_id FROM city WHERE id = %s", (city_id,))
    source_row = cur.fetchone()
    if not source_row:
        _close(cur, conn)
        raise HTTPException(status_code=404, detail="Исходный город не найден")
    cur.execute("SELECT region_id FROM city WHERE id = %s", (data.target_id,))
    target_row = cur.fetchone()
    if not target_row:
        _close(cur, conn)
        raise HTTPException(status_code=404, detail="Целевой город не найден")
    if source_row[0] != target_row[0]:
        _close(cur, conn)
        raise HTTPException(status_code=400, detail="Можно объединять только города одного региона")
    cur.execute("SELECT COUNT(*) FROM participant WHERE city_id = %s", (city_id,))
    affected = cur.fetchone()[0]
    cur.execute("UPDATE participant SET city_id = %s WHERE city_id = %s", (data.target_id, city_id))
    cur.execute("UPDATE club SET city_id = %s WHERE city_id = %s", (data.target_id, city_id))
    cur.execute("DELETE FROM city WHERE id = %s", (city_id,))
    conn.commit()
    _close(cur, conn, invalidate_cache=True)
    return {"status": "merged", "affected": affected}


@router.get("/clubs")
def list_clubs(city_id: int = Query(...), admin: str = Depends(get_current_admin)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT cl.id, cl.name, COUNT(p.id) as participant_count
        FROM club cl
        LEFT JOIN participant p ON p.club_id = cl.id
        WHERE cl.city_id = %s
        GROUP BY cl.id, cl.name
        ORDER BY cl.name
    """, (city_id,))
    rows = cur.fetchall()
    _close(cur, conn)
    return [{"id": r[0], "name": r[1], "count": r[2]} for r in rows]


@router.post("/clubs")
def create_club(data: CreateRequest, admin: str = Depends(get_current_admin)):
    if not data.parent_id:
        raise HTTPException(status_code=400, detail="Укажите city_id")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM club WHERE name = %s AND city_id = %s", (data.name.strip(), data.parent_id))
    if cur.fetchone():
        _close(cur, conn)
        raise HTTPException(status_code=400, detail="Клуб с таким названием уже существует в этом городе")
    cur.execute("INSERT INTO club (name, city_id) VALUES (%s, %s) RETURNING id", (data.name.strip(), data.parent_id))
    new_id = cur.fetchone()[0]
    conn.commit()
    _close(cur, conn, invalidate_cache=True)
    return {"id": new_id, "name": data.name.strip()}


@router.put("/clubs/{club_id}")
def rename_club(club_id: int, data: RenameRequest, admin: str = Depends(get_current_admin)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT city_id FROM club WHERE id = %s", (club_id,))
    row = cur.fetchone()
    if not row:
        _close(cur, conn)
        raise HTTPException(status_code=404, detail="Клуб не найден")
    cur.execute("SELECT id FROM club WHERE name = %s AND city_id = %s AND id != %s", (data.name.strip(), row[0], club_id))
    if cur.fetchone():
        _close(cur, conn)
        raise HTTPException(status_code=400, detail="Клуб с таким названием уже существует в этом городе")
    cur.execute("UPDATE club SET name = %s WHERE id = %s", (data.name.strip(), club_id))
    conn.commit()
    _close(cur, conn, invalidate_cache=True)
    return {"status": "renamed"}


@router.delete("/clubs/{club_id}")
def delete_club(club_id: int, admin: str = Depends(get_current_admin)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM club WHERE id = %s", (club_id,))
    if not cur.fetchone():
        _close(cur, conn)
        raise HTTPException(status_code=404, detail="Клуб не найден")
    cur.execute("SELECT COUNT(*) FROM participant WHERE club_id = %s", (club_id,))
    count = cur.fetchone()[0]
    if count > 0:
        _close(cur, conn)
        raise HTTPException(status_code=400, detail=f"Нельзя удалить: {count} участник(ов) привязано. Сначала объедините.")
    cur.execute("DELETE FROM coach WHERE club_id = %s", (club_id,))
    cur.execute("DELETE FROM club WHERE id = %s", (club_id,))
    conn.commit()
    _close(cur, conn, invalidate_cache=True)
    return {"status": "deleted"}


@router.post("/clubs/{club_id}/merge")
def merge_club(club_id: int, data: MergeRequest, admin: str = Depends(get_current_admin)):
    if club_id == data.target_id:
        raise HTTPException(status_code=400, detail="Нельзя объединить с самим собой")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT city_id FROM club WHERE id = %s", (club_id,))
    source_row = cur.fetchone()
    if not source_row:
        _close(cur, conn)
        raise HTTPException(status_code=404, detail="Исходный клуб не найден")
    cur.execute("SELECT city_id FROM club WHERE id = %s", (data.target_id,))
    target_row = cur.fetchone()
    if not target_row:
        _close(cur, conn)
        raise HTTPException(status_code=404, detail="Целевой клуб не найден")
    if source_row[0] != target_row[0]:
        _close(cur, conn)
        raise HTTPException(status_code=400, detail="Можно объединять только клубы одного города")
    cur.execute("SELECT COUNT(*) FROM participant WHERE club_id = %s", (club_id,))
    affected = cur.fetchone()[0]
    cur.execute("UPDATE participant SET club_id = %s WHERE club_id = %s", (data.target_id, club_id))
    cur.execute("UPDATE coach SET club_id = %s WHERE club_id = %s", (data.target_id, club_id))
    cur.execute("DELETE FROM club WHERE id = %s", (club_id,))
    conn.commit()
    _close(cur, conn, invalidate_cache=True)
    return {"status": "merged", "affected": affected}


@router.get("/coaches")
def list_coaches(club_id: int = Query(...), admin: str = Depends(get_current_admin)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT co.id, co.name, COUNT(p.id) as participant_count
        FROM coach co
        LEFT JOIN participant p ON p.coach_id = co.id
        WHERE co.club_id = %s
        GROUP BY co.id, co.name
        ORDER BY co.name
    """, (club_id,))
    rows = cur.fetchall()
    _close(cur, conn)
    return [{"id": r[0], "name": r[1], "count": r[2]} for r in rows]


@router.post("/coaches")
def create_coach(data: CreateRequest, admin: str = Depends(get_current_admin)):
    if not data.parent_id:
        raise HTTPException(status_code=400, detail="Укажите club_id")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM coach WHERE name = %s AND club_id = %s", (data.name.strip(), data.parent_id))
    if cur.fetchone():
        _close(cur, conn)
        raise HTTPException(status_code=400, detail="Тренер с таким именем уже существует в этом клубе")
    cur.execute("INSERT INTO coach (name, club_id) VALUES (%s, %s) RETURNING id", (data.name.strip(), data.parent_id))
    new_id = cur.fetchone()[0]
    conn.commit()
    _close(cur, conn, invalidate_cache=True)
    return {"id": new_id, "name": data.name.strip()}


@router.put("/coaches/{coach_id}")
def rename_coach(coach_id: int, data: RenameRequest, admin: str = Depends(get_current_admin)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT club_id FROM coach WHERE id = %s", (coach_id,))
    row = cur.fetchone()
    if not row:
        _close(cur, conn)
        raise HTTPException(status_code=404, detail="Тренер не найден")
    cur.execute("SELECT id FROM coach WHERE name = %s AND club_id = %s AND id != %s", (data.name.strip(), row[0], coach_id))
    if cur.fetchone():
        _close(cur, conn)
        raise HTTPException(status_code=400, detail="Тренер с таким именем уже существует в этом клубе")
    cur.execute("UPDATE coach SET name = %s WHERE id = %s", (data.name.strip(), coach_id))
    conn.commit()
    _close(cur, conn, invalidate_cache=True)
    return {"status": "renamed"}


@router.delete("/coaches/{coach_id}")
def delete_coach(coach_id: int, admin: str = Depends(get_current_admin)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM coach WHERE id = %s", (coach_id,))
    if not cur.fetchone():
        _close(cur, conn)
        raise HTTPException(status_code=404, detail="Тренер не найден")
    cur.execute("SELECT COUNT(*) FROM participant WHERE coach_id = %s", (coach_id,))
    count = cur.fetchone()[0]
    if count > 0:
        _close(cur, conn)
        raise HTTPException(status_code=400, detail=f"Нельзя удалить: {count} участник(ов) привязано. Сначала объедините.")
    cur.execute("DELETE FROM coach WHERE id = %s", (coach_id,))
    conn.commit()
    _close(cur, conn, invalidate_cache=True)
    return {"status": "deleted"}


@router.post("/coaches/{coach_id}/merge")
def merge_coach(coach_id: int, data: MergeRequest, admin: str = Depends(get_current_admin)):
    if coach_id == data.target_id:
        raise HTTPException(status_code=400, detail="Нельзя объединить с самим собой")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT club_id FROM coach WHERE id = %s", (coach_id,))
    source_row = cur.fetchone()
    if not source_row:
        _close(cur, conn)
        raise HTTPException(status_code=404, detail="Исходный тренер не найден")
    cur.execute("SELECT club_id FROM coach WHERE id = %s", (data.target_id,))
    target_row = cur.fetchone()
    if not target_row:
        _close(cur, conn)
        raise HTTPException(status_code=404, detail="Целевой тренер не найден")
    if source_row[0] != target_row[0]:
        _close(cur, conn)
        raise HTTPException(status_code=400, detail="Можно объединять только тренеров одного клуба")
    cur.execute("SELECT COUNT(*) FROM participant WHERE coach_id = %s", (coach_id,))
    affected = cur.fetchone()[0]
    cur.execute("UPDATE participant SET coach_id = %s WHERE coach_id = %s", (data.target_id, coach_id))
    cur.execute("DELETE FROM coach WHERE id = %s", (coach_id,))
    conn.commit()
    _close(cur, conn, invalidate_cache=True)
    return {"status": "merged", "affected": affected}
