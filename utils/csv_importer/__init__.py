import csv
from datetime import datetime
from db.database import save_participant_data
from db.cache import get_age_categories_from_cache, update_cache
from utils.formatters import normalize_class_name        

def _parse_date(date_str: str):
    if not date_str:
        return None
    date_str = date_str.split(' ')[0]
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d.%m.%Y", "%d/%m/%Y", "%Y.%m.%d"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None

def _normalize_age_category(age_cat_str: str) -> str:
    """
    Нормализует название возрастной категории из CSV для сопоставления с базой данных.
    Преобразует различные варианты написания в стандартный формат базы данных.
    """
    if not age_cat_str:
        return ""
    
    age_cat_str = age_cat_str.strip().lower().replace("ё", "е")
    
    # Маппинг вариантов написания на стандартные форматы базы данных
    # В базе используются: "2010-2011", "2008-2009", "2007 и старше"
    mapping = {
        # Форматы "18 и старше" -> "2007 и старше" (для 2025 года)
        "18 и старше": "2007 и старше",
        "18 и старше.": "2007 и старше",
        "18+": "2007 и старше",
        "взрослые": "2007 и старше",
        "старше 18": "2007 и старше",
        # Форматы с годами рождения
        "2010-11": "2010-2011",
        "2008-09": "2008-2009",
        "2007 и старше": "2007 и старше",
        # Уже нормализованные форматы
        "2010-2011": "2010-2011",
        "2008-2009": "2008-2009",
    }
    
    # Проверяем точное совпадение
    if age_cat_str in mapping:
        return mapping[age_cat_str]
    
    # Если формат "XX и старше" где XX - возраст (например, "18 и старше")
    if " и старше" in age_cat_str or "и старше" in age_cat_str:
        parts = age_cat_str.split()
        if len(parts) >= 2:
            try:
                age = int(parts[0])
                # Вычисляем год рождения: текущий год - возраст
                current_year = datetime.now().year
                birth_year = current_year - age
                return f"{birth_year} и старше"
            except (ValueError, IndexError):
                pass
    
    # Если формат "XX-YY" где XX и YY - годы рождения (например, "2010-2011")
    if "-" in age_cat_str and len(age_cat_str.split("-")) == 2:
        parts = age_cat_str.split("-")
        if len(parts) == 2:
            try:
                # Проверяем, что это годы (4 цифры)
                if len(parts[0].strip()) == 4 and len(parts[1].strip()) == 2:
                    # Формат "2010-11" -> "2010-2011"
                    year1 = parts[0].strip()
                    year2 = "20" + parts[1].strip()
                    return f"{year1}-{year2}"
                elif len(parts[0].strip()) == 4 and len(parts[1].strip()) == 4:
                    # Формат "2010-2011" уже правильный
                    return f"{parts[0].strip()}-{parts[1].strip()}"
            except (ValueError, IndexError):
                pass
    
    # Если ничего не подошло, возвращаем исходное значение
    return age_cat_str
                
async def process_csv_import(file_path: str, tgid_who_added: int, competition_id: int | None = None) -> dict:
    stats = {"created": 0, "updated": 0, "errors": 0, "error_details": []}
    age_categories_cache = get_age_categories_from_cache()
    if not age_categories_cache:
        update_cache()
        age_categories_cache = get_age_categories_from_cache()

    try:
        with open(file_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            try:
                header = [h.strip() for h in next(reader)]
            except StopIteration:
                stats['error_details'].append("CSV-файл пуст.")
                stats['errors'] = -1
                return stats

            # Определяем название колонки для класса (поддерживаем оба варианта)
            class_col_name = None
            if "Категория участника" in header:
                class_col_name = "Категория участника"
            elif "Класс участника" in header:
                class_col_name = "Класс участника"
            
            header_map = {
                'fio': header.index("ФИО") if "ФИО" in header else -1,
                'gender': header.index("Пол") if "Пол" in header else -1,
                'dob': header.index("Дата рождения") if "Дата рождения" in header else -1,
                'age_cat': header.index("Возрастная категория") if "Возрастная категория" in header else -1,
                'class': header.index(class_col_name) if class_col_name else -1,
                'rank': header.index("Разряд (если есть)") if "Разряд (если есть)" in header else -1,
                'rank_date': header.index("Дата присвоения разряда") if "Дата присвоения разряда" in header else -1,
                'order_num': header.index("Номер приказа") if "Номер приказа" in header else -1,
                'region': header.index("Регион") if "Регион" in header else -1,
                'coach': header.index("Укажите ФИО тренера") if "Укажите ФИО тренера" in header else -1,
                'weight': header.index("Весовая категория") if "Весовая категория" in header else -1,
                'city': header.index("Город/населённый пункт") if "Город/населённый пункт" in header else -1,
                'club': header.index("Выберите клуб") if "Выберите клуб" in header else -1,
            }

            required_fields = ['fio', 'gender', 'dob', 'weight', 'class', 'region', 'city', 'club']
            missing_headers = [key for key in required_fields if header_map[key] == -1]
            if missing_headers:
                 stats['error_details'].append(f"Отсутствуют обязательные колонки в CSV файле: {', '.join(missing_headers)}")
                 stats['errors'] = -1
                 return stats

            for i, row in enumerate(reader):
                try:
                    def get_col_by_name(key, default=''):
                        idx = header_map.get(key, -1)
                        return row[idx].strip() if idx != -1 and len(row) > idx else default

                    fio = get_col_by_name('fio')
                    if not fio:
                        continue

                    gender_raw = get_col_by_name('gender').strip().lower()
                    if gender_raw in ("муж", "м", "мужской"):
                        gender = "Мужской"
                    elif gender_raw in ("жен", "ж", "женский"):
                        gender = "Женский"
                    else: 
                        # По умолчанию пытаемся распознать по первой букве
                        gender = "Мужской" if gender_raw.startswith("м") else "Женский"

                    dob_str = get_col_by_name('dob')
                    dob_parsed = _parse_date(dob_str)
                    if not dob_parsed:
                         stats["errors"] += 1
                         if len(stats["error_details"]) < 5:
                             stats["error_details"].append(f"Строка {i + 2}: Неверный формат даты '{dob_str}'")
                         continue

                    age_category_name_from_csv = get_col_by_name('age_cat')
                    weight_category_name = get_col_by_name('weight')
                    class_name_raw = get_col_by_name('class') or None
                    rank_name = get_col_by_name('rank') or None
                    rank_date_str = get_col_by_name('rank_date')
                    rank_assigned_on = _parse_date(rank_date_str)
                    order_number = get_col_by_name('order_num') or None
                    region_name = get_col_by_name('region')
                    city_name_raw = get_col_by_name('city')
                    club_name = get_col_by_name('club')
                    coach_full_str = get_col_by_name('coach').strip('"')
                    coach_name = coach_full_str.split(',')[0].strip() if coach_full_str else None

                    city_name = city_name_raw
                    if city_name_raw == "Чишмы":
                        city_name = "пгт. Чишмы"

                    class_name_normalized = None
                    if class_name_raw:
                        # Применяем нормализацию названия класса
                        class_name_normalized = normalize_class_name(class_name_raw.strip())
                        
                        # Обрабатываем скобки
                        if "(" in class_name_normalized:
                            parts = class_name_normalized.split('(')
                            if len(parts) > 1:
                                inside_parens = parts[1].split(')')[0]
                                class_name_normalized = f"{parts[0].strip()} ({inside_parens.capitalize()})"

                    determined_age_category_id = None
                    determined_age_category_name = None
                    birth_year = datetime.fromisoformat(dob_parsed).year
                    
                    # Сначала пытаемся найти категорию по имени из CSV (если указано)
                    if age_category_name_from_csv:
                        normalized_age_cat = _normalize_age_category(age_category_name_from_csv)
                        for category in age_categories_cache:
                            if category['gender'] != gender:
                                continue
                            # Сравниваем нормализованное имя из CSV с именем категории в базе
                            if category['name'].lower() == normalized_age_cat.lower():
                                determined_age_category_id = category['id']
                                determined_age_category_name = category['name']
                                break
                    
                    # Если не нашли по имени из CSV, используем логику по году рождения
                    if not determined_age_category_id:
                        for category in age_categories_cache:
                            if category['gender'] != gender:
                                continue
                            min_year = category.get('min_year')
                            max_year = category.get('max_year')

                            if min_year is None and max_year is not None and birth_year <= max_year:
                                determined_age_category_id = category['id']
                                determined_age_category_name = category['name']
                                break
                            elif min_year is not None and max_year is not None and min_year <= birth_year <= max_year:
                                determined_age_category_id = category['id']
                                determined_age_category_name = category['name']
                                break

                    if not determined_age_category_id:
                         stats["errors"] += 1
                         if len(stats["error_details"]) < 5:
                             csv_age_info = f" (возрастная категория из CSV: '{age_category_name_from_csv}')" if age_category_name_from_csv else ""
                             stats["error_details"].append(f"Строка {i + 2}: Не удалось определить возрастную категорию для года {birth_year} и пола {gender}{csv_age_info}")
                         continue

                    participant_data = {
                        "fio": fio,
                        "gender": gender,
                        "dob": dob_parsed,
                        "age_category_id": determined_age_category_id,
                        "age_category_name": determined_age_category_name,
                        "weight_category_name": weight_category_name,
                        "class_name": class_name_normalized,
                        "rank_name": rank_name,
                        "rank_assigned_on": rank_assigned_on,
                        "order_number": order_number,
                        "region_name": region_name,
                        "city_name": city_name,
                        "club_name": club_name,
                        "coach_name": coach_name,
                        "competition_id": competition_id,
                    }


                    status = save_participant_data(participant_data, tgid_who_added)
                    if status == "created":
                        stats["created"] += 1
                    elif status == "updated":
                        stats["updated"] += 1

                except IndexError as e:
                     stats["errors"] += 1
                     if len(stats["error_details"]) < 5:
                         stats["error_details"].append(f"Строка {i + 2}: Ошибка индекса, возможно, не хватает данных в строке | {e}")
                except Exception as e:
                    stats["errors"] += 1
                    if len(stats["error_details"]) < 5:
                        stats["error_details"].append(f"Строка {i + 2}: {e} | Данные: {row}")

    except FileNotFoundError:
        stats["errors"] = -1
        stats["error_details"].append(f"Файл не найден по пути: {file_path}")
    except Exception as e:
        stats["errors"] = -1
        stats["error_details"].append(f"Критическая ошибка при чтении файла: {e}")

    return stats
