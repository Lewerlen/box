from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date

from db.database import save_participant_data, get_db_connection
from db.cache import (
    get_age_categories_from_cache,
    get_weight_categories_from_cache,
    get_classes_from_cache,
    get_ranks_from_cache,
    get_regions_from_cache,
    get_cities_from_cache,
    get_clubs_from_cache,
    get_coaches_from_cache,
    update_cache,
)

router = APIRouter()


class RegistrationData(BaseModel):
    fio: str
    gender: str
    dob: str
    age_category_id: int
    weight_category_id: int
    class_name: str
    rank_name: Optional[str] = None
    rank_assigned_on: Optional[str] = None
    order_number: Optional[str] = None
    region_name: str
    city_name: str
    club_name: str
    coach_name: str
    competition_id: Optional[int] = None


@router.get("/age-categories")
def get_age_categories_for_gender(gender: str):
    all_categories = get_age_categories_from_cache()
    return [cat for cat in all_categories if cat.get("gender") == gender]


@router.get("/determine-age-category")
def determine_age_category(dob: str, gender: str):
    try:
        birth_date = datetime.strptime(dob, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте YYYY-MM-DD")

    birth_year = birth_date.year
    all_categories = get_age_categories_from_cache()
    filtered = [cat for cat in all_categories if cat.get("gender") == gender]

    for category in filtered:
        min_year = category.get("min_year")
        max_year = category.get("max_year")

        if min_year is None and max_year is not None and birth_year <= max_year:
            return {"age_category": category}
        elif min_year is not None and max_year is not None and min_year <= birth_year <= max_year:
            return {"age_category": category}

    raise HTTPException(status_code=404, detail="Не удалось определить возрастную категорию")


@router.get("/weight-categories")
def get_weight_cats(age_category_id: int):
    return get_weight_categories_from_cache(age_category_id)


@router.get("/classes")
def get_class_list():
    return get_classes_from_cache()


@router.get("/ranks")
def get_rank_list():
    return get_ranks_from_cache()


@router.get("/regions")
def get_region_list():
    return get_regions_from_cache()


@router.get("/cities")
def get_city_list(region_id: int):
    return get_cities_from_cache(region_id)


@router.get("/clubs")
def get_club_list(city_id: int):
    return get_clubs_from_cache(city_id)


@router.get("/coaches")
def get_coach_list(club_id: int):
    return get_coaches_from_cache(club_id)


def _check_registration_open(competition_id: int):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT status, registration_closed, registration_deadline, registration_open_at FROM competitions WHERE id = %s",
            (competition_id,)
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Соревнование не найдено")
        status, reg_closed, reg_deadline, reg_open_at = row
        if status != "active":
            raise HTTPException(status_code=403, detail="Регистрация недоступна: соревнование не активно")
        if reg_closed:
            raise HTTPException(status_code=403, detail="Регистрация закрыта организатором")
        if reg_open_at and datetime.now(reg_open_at.tzinfo) < reg_open_at:
            raise HTTPException(status_code=403, detail=f"Регистрация ещё не открыта (откроется {reg_open_at.strftime('%d.%m.%Y %H:%M')})")
        if reg_deadline and datetime.now(reg_deadline.tzinfo) > reg_deadline:
            raise HTTPException(status_code=403, detail=f"Срок регистрации истёк ({reg_deadline.strftime('%d.%m.%Y %H:%M')})")
    finally:
        conn.close()


@router.post("/submit")
def submit_registration(data: RegistrationData):
    if data.competition_id:
        _check_registration_open(data.competition_id)
    try:
        participant_data = {
            "fio": data.fio.strip(),
            "gender": data.gender,
            "dob": data.dob,
            "age_category_id": data.age_category_id,
            "weight_category_name": None,
            "class_name": data.class_name,
            "rank_name": data.rank_name,
            "rank_assigned_on": data.rank_assigned_on,
            "order_number": data.order_number,
            "region_name": data.region_name,
            "city_name": data.city_name,
            "club_name": data.club_name,
            "coach_name": data.coach_name,
            "weight_category_id": data.weight_category_id,
            "competition_id": data.competition_id,
        }

        status = save_participant_data(participant_data, tgid_who_added=0)
        update_cache()
        return {"status": status, "message": "Участник успешно зарегистрирован" if status == "created" else "Данные участника обновлены"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
