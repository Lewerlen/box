"""
API маршруты для управления рингами и расписанием боёв.
"""
from typing import Optional, List
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth import get_current_admin
from db.database import get_db_connection
from utils.schedule import (
    get_first_round_pairs,
    get_scheduled_pair_keys,
    pair_key_for_fight,
    get_full_schedule,
)


admin_router = APIRouter()
public_router = APIRouter()


# ---------- Pydantic ----------

class RingCreate(BaseModel):
    name: str


class RingUpdate(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None


class RingsReorder(BaseModel):
    ring_ids: List[int]


class FightCreate(BaseModel):
    ring_id: int
    day_number: int
    fighter1_id: int
    fighter2_id: int
    class_name: str
    gender: str
    age_category_name: str
    weight_name: str
    round_label: str = ""


class FightUpdate(BaseModel):
    ring_id: Optional[int] = None
    day_number: Optional[int] = None
    fight_order: Optional[int] = None


class BulkMove(BaseModel):
    fight_ids: List[int]
    ring_id: int
    day_number: int


class ReorderInCell(BaseModel):
    ring_id: int
    day_number: int
    fight_ids: List[int]


class MoveRingToNextDay(BaseModel):
    ring_id: int
    day_number: int


# ---------- Helpers ----------

def _ensure_competition(cur, competition_id: int):
    cur.execute("SELECT id, date_start, date_end FROM competitions WHERE id = %s", (competition_id,))
    r = cur.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Соревнование не найдено")
    return r


def _ensure_ring(cur, ring_id: int, competition_id: int):
    cur.execute("SELECT id FROM competition_rings WHERE id = %s AND competition_id = %s",
                (ring_id, competition_id))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Ринг не найден")


def _max_fight_order(cur, competition_id: int, ring_id: int, day_number: int) -> int:
    cur.execute("""
        SELECT COALESCE(MAX(fight_order), -1) FROM fight_schedule
        WHERE competition_id = %s AND ring_id = %s AND day_number = %s
    """, (competition_id, ring_id, day_number))
    return cur.fetchone()[0]


def _normalize_fight_orders(cur, competition_id: int, ring_id: int, day_number: int):
    cur.execute("""
        SELECT id FROM fight_schedule
        WHERE competition_id = %s AND ring_id = %s AND day_number = %s
        ORDER BY fight_order, id
    """, (competition_id, ring_id, day_number))
    ids = [row[0] for row in cur.fetchall()]
    for i, fid in enumerate(ids):
        cur.execute("UPDATE fight_schedule SET fight_order = %s WHERE id = %s", (i, fid))


def _competition_days(date_start: Optional[date], date_end: Optional[date]) -> list[dict]:
    if not date_start:
        return []
    if not date_end or date_end < date_start:
        date_end = date_start
    out = []
    d = date_start
    n = 1
    while d <= date_end:
        out.append({"day_number": n, "date": d.isoformat()})
        d += timedelta(days=1)
        n += 1
    return out


# ---------- Admin: rings ----------

@admin_router.get("/competitions/{competition_id}/rings")
def list_rings(competition_id: int, admin: str = Depends(get_current_admin)):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        _ensure_competition(cur, competition_id)
        cur.execute("""
            SELECT id, name, sort_order FROM competition_rings
            WHERE competition_id = %s ORDER BY sort_order, id
        """, (competition_id,))
        return [{"id": r[0], "name": r[1], "sort_order": r[2]} for r in cur.fetchall()]
    finally:
        conn.close()


@admin_router.post("/competitions/{competition_id}/rings")
def create_ring(competition_id: int, data: RingCreate, admin: str = Depends(get_current_admin)):
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Имя ринга обязательно")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        _ensure_competition(cur, competition_id)
        cur.execute("""
            SELECT COALESCE(MAX(sort_order), -1) + 1 FROM competition_rings
            WHERE competition_id = %s
        """, (competition_id,))
        next_order = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO competition_rings (competition_id, name, sort_order)
            VALUES (%s, %s, %s) RETURNING id
        """, (competition_id, name, next_order))
        new_id = cur.fetchone()[0]
        conn.commit()
        return {"id": new_id, "name": name, "sort_order": next_order}
    finally:
        conn.close()


@admin_router.put("/rings/{ring_id}")
def update_ring(ring_id: int, data: RingUpdate, admin: str = Depends(get_current_admin)):
    fields = {}
    if data.name is not None:
        n = data.name.strip()
        if not n:
            raise HTTPException(status_code=400, detail="Имя ринга обязательно")
        fields["name"] = n
    if data.sort_order is not None:
        fields["sort_order"] = data.sort_order
    if not fields:
        raise HTTPException(status_code=400, detail="Нет полей для обновления")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM competition_rings WHERE id = %s", (ring_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Ринг не найден")
        set_clause = ", ".join(f"{k} = %s" for k in fields)
        cur.execute(f"UPDATE competition_rings SET {set_clause} WHERE id = %s",
                    (*fields.values(), ring_id))
        conn.commit()
        return {"status": "updated"}
    finally:
        conn.close()


@admin_router.delete("/rings/{ring_id}")
def delete_ring(ring_id: int, admin: str = Depends(get_current_admin)):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM competition_rings WHERE id = %s", (ring_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Ринг не найден")
        conn.commit()
        return {"status": "deleted"}
    finally:
        conn.close()


@admin_router.post("/competitions/{competition_id}/rings/reorder")
def reorder_rings(competition_id: int, data: RingsReorder, admin: str = Depends(get_current_admin)):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        _ensure_competition(cur, competition_id)
        for i, rid in enumerate(data.ring_ids):
            cur.execute("""
                UPDATE competition_rings SET sort_order = %s
                WHERE id = %s AND competition_id = %s
            """, (i, rid, competition_id))
        conn.commit()
        return {"status": "reordered"}
    finally:
        conn.close()


# ---------- Admin: pairs pool & schedule ----------

@admin_router.get("/competitions/{competition_id}/schedule/pairs")
def list_pairs_pool(competition_id: int, admin: str = Depends(get_current_admin)):
    """Все пары первого круга + признак, распределена ли каждая."""
    pairs = get_first_round_pairs(competition_id)
    scheduled = get_scheduled_pair_keys(competition_id)
    out = []
    for p in pairs:
        key = pair_key_for_fight(
            p["class_name"], p["gender"], p["age_category_name"],
            p["weight_name"], p["fighter1_id"], p["fighter2_id"]
        )
        p["scheduled"] = key in scheduled
        out.append(p)
    return out


def _extend_days_to_cover(days_meta: list[dict], used_days: list[int]) -> list[dict]:
    if not used_days:
        return days_meta
    max_used = max(used_days)
    if days_meta:
        from datetime import datetime as _dt
        while len(days_meta) < max_used:
            last = days_meta[-1]
            if last.get("date"):
                d = _dt.fromisoformat(last["date"]).date() + timedelta(days=1)
                days_meta.append({"day_number": len(days_meta) + 1, "date": d.isoformat()})
            else:
                days_meta.append({"day_number": len(days_meta) + 1, "date": None})
    else:
        days_meta = [{"day_number": d, "date": None} for d in sorted(set(used_days))]
    return days_meta


@admin_router.get("/competitions/{competition_id}/schedule")
def admin_get_schedule(competition_id: int, admin: str = Depends(get_current_admin)):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        comp = _ensure_competition(cur, competition_id)
    finally:
        conn.close()
    days = _competition_days(comp[1], comp[2])
    data = get_full_schedule(competition_id)
    used_days = [f["day_number"] for f in data["fights"]]
    days = _extend_days_to_cover(days, used_days)
    return {"days": days, "rings": data["rings"], "fights": data["fights"]}


@admin_router.post("/competitions/{competition_id}/schedule")
def create_fight(competition_id: int, data: FightCreate, admin: str = Depends(get_current_admin)):
    if data.fighter1_id == data.fighter2_id:
        raise HTTPException(status_code=400, detail="Бойцы должны быть разными")
    if data.day_number < 1:
        raise HTTPException(status_code=400, detail="Некорректный номер дня")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        _ensure_competition(cur, competition_id)
        _ensure_ring(cur, data.ring_id, competition_id)

        cur.execute("""
            SELECT id FROM fight_schedule
            WHERE competition_id = %s
              AND ((fighter1_id = %s AND fighter2_id = %s) OR
                   (fighter1_id = %s AND fighter2_id = %s))
        """, (competition_id, data.fighter1_id, data.fighter2_id,
              data.fighter2_id, data.fighter1_id))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="Эта пара уже распределена")

        next_order = _max_fight_order(cur, competition_id, data.ring_id, data.day_number) + 1
        cur.execute("""
            INSERT INTO fight_schedule
                (competition_id, ring_id, day_number, fight_order,
                 fighter1_id, fighter2_id, class_name, gender,
                 age_category_name, weight_name, round_label)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (competition_id, data.ring_id, data.day_number, next_order,
              data.fighter1_id, data.fighter2_id,
              data.class_name, data.gender, data.age_category_name,
              data.weight_name, data.round_label))
        new_id = cur.fetchone()[0]
        conn.commit()
        return {"id": new_id, "fight_order": next_order}
    finally:
        conn.close()


@admin_router.put("/schedule/{fight_id}")
def update_fight(fight_id: int, data: FightUpdate, admin: str = Depends(get_current_admin)):
    if data.ring_id is None and data.day_number is None and data.fight_order is None:
        raise HTTPException(status_code=400, detail="Нет полей для обновления")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT competition_id, ring_id, day_number FROM fight_schedule WHERE id = %s
        """, (fight_id,))
        r = cur.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Бой не найден")
        comp_id, old_ring, old_day = r

        new_ring = data.ring_id if data.ring_id is not None else old_ring
        new_day = data.day_number if data.day_number is not None else old_day

        if data.ring_id is not None:
            _ensure_ring(cur, new_ring, comp_id)
        if data.day_number is not None and data.day_number < 1:
            raise HTTPException(status_code=400, detail="Некорректный номер дня")

        if (new_ring != old_ring) or (new_day != old_day):
            new_order = _max_fight_order(cur, comp_id, new_ring, new_day) + 1
            cur.execute("""
                UPDATE fight_schedule SET ring_id = %s, day_number = %s, fight_order = %s
                WHERE id = %s
            """, (new_ring, new_day, new_order, fight_id))
            _normalize_fight_orders(cur, comp_id, old_ring, old_day)
        elif data.fight_order is not None:
            cur.execute("UPDATE fight_schedule SET fight_order = %s WHERE id = %s",
                        (data.fight_order, fight_id))
            _normalize_fight_orders(cur, comp_id, new_ring, new_day)

        conn.commit()
        return {"status": "updated"}
    finally:
        conn.close()


@admin_router.delete("/schedule/{fight_id}")
def delete_fight(fight_id: int, admin: str = Depends(get_current_admin)):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT competition_id, ring_id, day_number FROM fight_schedule WHERE id = %s
        """, (fight_id,))
        r = cur.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Бой не найден")
        comp_id, ring_id, day_number = r
        cur.execute("DELETE FROM fight_schedule WHERE id = %s", (fight_id,))
        _normalize_fight_orders(cur, comp_id, ring_id, day_number)
        conn.commit()
        return {"status": "deleted"}
    finally:
        conn.close()


@admin_router.post("/competitions/{competition_id}/schedule/bulk-move")
def bulk_move(competition_id: int, data: BulkMove, admin: str = Depends(get_current_admin)):
    if not data.fight_ids:
        return {"moved": 0}
    if data.day_number < 1:
        raise HTTPException(status_code=400, detail="Некорректный номер дня")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        _ensure_competition(cur, competition_id)
        _ensure_ring(cur, data.ring_id, competition_id)

        cur.execute("""
            SELECT id, ring_id, day_number FROM fight_schedule
            WHERE id = ANY(%s) AND competition_id = %s
        """, (list(data.fight_ids), competition_id))
        rows = cur.fetchall()
        if len(rows) != len(set(data.fight_ids)):
            raise HTTPException(status_code=404, detail="Некоторые бои не найдены")

        sources = {(row[1], row[2]) for row in rows}
        next_order = _max_fight_order(cur, competition_id, data.ring_id, data.day_number) + 1
        for fid in data.fight_ids:
            cur.execute("""
                UPDATE fight_schedule SET ring_id = %s, day_number = %s, fight_order = %s
                WHERE id = %s
            """, (data.ring_id, data.day_number, next_order, fid))
            next_order += 1
        for ring_id, day_number in sources:
            _normalize_fight_orders(cur, competition_id, ring_id, day_number)
        _normalize_fight_orders(cur, competition_id, data.ring_id, data.day_number)
        conn.commit()
        return {"moved": len(data.fight_ids)}
    finally:
        conn.close()


@admin_router.post("/competitions/{competition_id}/schedule/reorder")
def reorder_in_cell(competition_id: int, data: ReorderInCell, admin: str = Depends(get_current_admin)):
    if data.day_number < 1:
        raise HTTPException(status_code=400, detail="Некорректный номер дня")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        _ensure_competition(cur, competition_id)
        _ensure_ring(cur, data.ring_id, competition_id)
        for i, fid in enumerate(data.fight_ids):
            cur.execute("""
                UPDATE fight_schedule SET fight_order = %s
                WHERE id = %s AND competition_id = %s AND ring_id = %s AND day_number = %s
            """, (i, fid, competition_id, data.ring_id, data.day_number))
        conn.commit()
        return {"status": "reordered"}
    finally:
        conn.close()


@admin_router.post("/competitions/{competition_id}/schedule/move-ring-to-next-day")
def move_ring_to_next_day(competition_id: int, data: MoveRingToNextDay,
                          admin: str = Depends(get_current_admin)):
    if data.day_number < 1:
        raise HTTPException(status_code=400, detail="Некорректный номер дня")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        _ensure_competition(cur, competition_id)
        _ensure_ring(cur, data.ring_id, competition_id)

        next_day = data.day_number + 1
        next_order_start = _max_fight_order(cur, competition_id, data.ring_id, next_day) + 1

        cur.execute("""
            SELECT id FROM fight_schedule
            WHERE competition_id = %s AND ring_id = %s AND day_number = %s
            ORDER BY fight_order, id
        """, (competition_id, data.ring_id, data.day_number))
        ids = [row[0] for row in cur.fetchall()]

        for i, fid in enumerate(ids):
            cur.execute("""
                UPDATE fight_schedule SET day_number = %s, fight_order = %s
                WHERE id = %s
            """, (next_day, next_order_start + i, fid))

        conn.commit()
        return {"moved": len(ids), "to_day": next_day}
    finally:
        conn.close()


# ---------- Public ----------

@public_router.get("/competitions/{competition_id}/schedule")
def public_get_schedule(competition_id: int):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, date_start, date_end FROM competitions WHERE id = %s",
                    (competition_id,))
        r = cur.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Соревнование не найдено")
        days_meta = _competition_days(r[1], r[2])
    finally:
        conn.close()
    data = get_full_schedule(competition_id)

    used_days = [f["day_number"] for f in data["fights"]]
    days_meta = _extend_days_to_cover(days_meta, used_days)
    return {"days": days_meta, "rings": data["rings"], "fights": data["fights"]}
