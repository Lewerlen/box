from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime

from api.auth import get_current_admin
from db.database import get_db_connection

router = APIRouter()
admin_router = APIRouter()


class CompetitionCreate(BaseModel):
    name: str
    discipline: str
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    location: Optional[str] = None
    status: str = "upcoming"
    registration_deadline: Optional[datetime] = None
    registration_open_at: Optional[datetime] = None
    registration_closed: bool = False


class CompetitionUpdate(BaseModel):
    name: Optional[str] = None
    discipline: Optional[str] = None
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    registration_deadline: Optional[datetime] = None
    registration_open_at: Optional[datetime] = None
    registration_closed: Optional[bool] = None


def _row_to_dict(row):
    return {
        "id": row[0],
        "name": row[1],
        "discipline": row[2],
        "date_start": row[3].isoformat() if row[3] else None,
        "date_end": row[4].isoformat() if row[4] else None,
        "location": row[5],
        "status": row[6],
        "created_at": row[7].isoformat() if row[7] else None,
        "participants_count": row[8] if len(row) > 8 else 0,
        "registration_deadline": row[9].isoformat() if len(row) > 9 and row[9] else None,
        "registration_closed": row[10] if len(row) > 10 else False,
        "registration_open_at": row[11].isoformat() if len(row) > 11 and row[11] else None,
    }


@router.get("")
def list_competitions():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.id, c.name, c.discipline, c.date_start, c.date_end,
                   c.location, c.status, c.created_at,
                   COUNT(p.id) AS participants_count,
                   c.registration_deadline, c.registration_closed, c.registration_open_at
            FROM competitions c
            LEFT JOIN participant p ON p.competition_id = c.id
            GROUP BY c.id, c.name, c.discipline, c.date_start, c.date_end,
                     c.location, c.status, c.created_at,
                     c.registration_deadline, c.registration_closed, c.registration_open_at
            ORDER BY
                CASE c.status
                    WHEN 'active' THEN 1
                    WHEN 'upcoming' THEN 2
                    WHEN 'finished' THEN 3
                    ELSE 4
                END,
                c.date_start DESC
        """)
        rows = cur.fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/{competition_id}")
def get_competition(competition_id: int):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.id, c.name, c.discipline, c.date_start, c.date_end,
                   c.location, c.status, c.created_at,
                   COUNT(p.id) AS participants_count,
                   c.registration_deadline, c.registration_closed, c.registration_open_at
            FROM competitions c
            LEFT JOIN participant p ON p.competition_id = c.id
            WHERE c.id = %s
            GROUP BY c.id, c.name, c.discipline, c.date_start, c.date_end,
                     c.location, c.status, c.created_at,
                     c.registration_deadline, c.registration_closed, c.registration_open_at
        """, (competition_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Соревнование не найдено")
        return _row_to_dict(row)
    finally:
        conn.close()


@admin_router.post("", dependencies=[Depends(get_current_admin)])
def create_competition(data: CompetitionCreate):
    valid_disciplines = {"muay_thai", "kickboxing"}
    valid_statuses = {"upcoming", "active", "finished"}
    if data.discipline not in valid_disciplines:
        raise HTTPException(status_code=400, detail="Недопустимая дисциплина")
    if data.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Недопустимый статус")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO competitions
                (name, discipline, date_start, date_end, location, status,
                 registration_deadline, registration_open_at, registration_closed)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (
            data.name, data.discipline, data.date_start, data.date_end,
            data.location, data.status,
            data.registration_deadline, data.registration_open_at, data.registration_closed,
        ))
        new_id = cur.fetchone()[0]
        conn.commit()
        return {"id": new_id, "message": "Соревнование создано"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@admin_router.put("/{competition_id}", dependencies=[Depends(get_current_admin)])
def update_competition(competition_id: int, data: CompetitionUpdate):
    fields = {}
    if data.name is not None:
        fields["name"] = data.name
    if data.discipline is not None:
        valid_disciplines = {"muay_thai", "kickboxing"}
        if data.discipline not in valid_disciplines:
            raise HTTPException(status_code=400, detail="Недопустимая дисциплина")
        fields["discipline"] = data.discipline
    if data.date_start is not None:
        fields["date_start"] = data.date_start
    if data.date_end is not None:
        fields["date_end"] = data.date_end
    if data.location is not None:
        fields["location"] = data.location
    if data.status is not None:
        valid_statuses = {"upcoming", "active", "finished"}
        if data.status not in valid_statuses:
            raise HTTPException(status_code=400, detail="Недопустимый статус")
        fields["status"] = data.status
    if "registration_deadline" in data.model_fields_set:
        fields["registration_deadline"] = data.registration_deadline
    if "registration_open_at" in data.model_fields_set:
        fields["registration_open_at"] = data.registration_open_at
    if data.registration_closed is not None:
        fields["registration_closed"] = data.registration_closed

    if not fields:
        raise HTTPException(status_code=400, detail="Нет полей для обновления")

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        set_clause = ", ".join(f"{k} = %s" for k in fields)
        cur.execute(
            f"UPDATE competitions SET {set_clause} WHERE id = %s",
            (*fields.values(), competition_id)
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Соревнование не найдено")
        conn.commit()
        return {"message": "Соревнование обновлено"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@admin_router.delete("/{competition_id}", dependencies=[Depends(get_current_admin)])
def delete_competition(competition_id: int):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM competitions WHERE id = %s", (competition_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Соревнование не найдено")
        conn.commit()
        return {"message": "Соревнование удалено"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@admin_router.get("", dependencies=[Depends(get_current_admin)])
def admin_list_competitions():
    return list_competitions()
