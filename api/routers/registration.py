from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from db.database import save_participant_data
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
    region_name: str
    city_name: str
    club_name: str
    coach_name: str


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


@router.post("/submit")
def submit_registration(data: RegistrationData):
    try:
        participant_data = {
            "fio": data.fio.strip(),
            "gender": data.gender,
            "dob": data.dob,
            "age_category_id": data.age_category_id,
            "weight_category_name": None,
            "class_name": data.class_name,
            "rank_name": data.rank_name,
            "region_name": data.region_name,
            "city_name": data.city_name,
            "club_name": data.club_name,
            "coach_name": data.coach_name,
            "weight_category_id": data.weight_category_id,
        }

        status = save_participant_data(participant_data, tgid_who_added=0)
        update_cache()
        return {"status": status, "message": "Участник успешно зарегистрирован" if status == "created" else "Данные участника обновлены"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
