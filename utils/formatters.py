from decimal import Decimal
import re

def format_weight(weight: float | Decimal | None) -> str:
    """
    Форматирует вес в строку.
    - Если вес None, возвращает "N/A".
    - Если дробная часть веса равна .9 (например, 91.9), форматирует в "91+ кг".
    - Если вес целый (например, 52.0), отбрасывает дробную часть ("52 кг").
    - В остальных случаях (например, 63.5) оставляет дробную часть.
    """
    if weight is None:
        return "N/A"

    weight_decimal = Decimal(str(weight))

    # Проверяем, равна ли дробная часть .9, используя int() для отсечения дробной части
    if weight_decimal - int(weight_decimal) == Decimal("0.9"):
        base_weight = int(weight_decimal)
        return f"{base_weight}+ кг"

    # Если число целое (например 52.0), выводим без точки
    if weight_decimal == int(weight_decimal):
        return f"{int(weight_decimal)} кг"
    else:
        # Иначе выводим с десятичной частью (например 63.5)
        return f"{weight_decimal.normalize()} кг"

def normalize_class_name(class_name: str) -> str:
    """
    Нормализует название класса, преобразуя все варианты:
    - "Фул", "Фулл", "фулл-контакт", "фул - контакт", "фулл - контакт", "фул-контакт" в "Фулл-контакт"
    - Заменяет латинские буквы на кириллические для классов A, B, C
    
    Примеры:
    - "Фул" -> "Фулл-контакт"
    - "Фулл" -> "Фулл-контакт"
    - "фулл-контакт" -> "Фулл-контакт"
    - "фул - контакт" -> "Фулл-контакт"
    - "фулл - контакт" -> "Фулл-контакт"
    - "фул-контакт" -> "Фулл-контакт"
    - "A (Опытный)" -> "А (Опытный)"
    - "B (Новичок)" -> "В (Новичок)"
    - "C (Дебютант)" -> "С (Дебютант)"
    """
    if not class_name:
        return ""
    
    original = class_name.strip()
    
    # Проверяем варианты "фул-контакт"
    # Убираем все пробелы и дефисы для проверки
    temp_check_full = original.replace(' ', '').replace('-', '').strip().lower()
    
    # Проверяем, является ли вся строка вариантом "фул" или "фулл-контакт"
    # Варианты: "фул", "фулл", "фуллконтакт", "фулконтакт" и т.д.
    if temp_check_full == 'фул' or temp_check_full == 'фулл':
        return 'Фулл-контакт'
    elif temp_check_full.startswith('фул') and 'контакт' in temp_check_full:
        return 'Фулл-контакт'
    
    # Применяем нормализацию к частям строки
    normalized = original
    
    # Сначала нормализуем варианты "фул-контакт" в строке (с "контакт")
    # Заменяем "фул"/"фулл" (с пробелами/дефисами) + "контакт" на "Фулл-контакт"
    normalized = re.sub(r'[Фф]улл?\s*[- ]*\s*[Кк]онтакт', 'Фулл-контакт', normalized, flags=re.IGNORECASE)
    
    # Затем обрабатываем случаи, когда "фул" или "фулл" стоят отдельно (без "контакт")
    # Заменяем "фул" (не "фулл") на "Фулл-контакт"
    # Используем отрицательный lookahead, чтобы не затронуть "фулл"
    normalized = re.sub(r'(?<![Фф]у)[Фф]ул(?!л)', 'Фулл-контакт', normalized, flags=re.IGNORECASE)
    # Заменяем "фулл" (не перед "контакт") на "Фулл-контакт"
    normalized = re.sub(r'[Фф]улл(?![- ]*[Кк]онтакт)', 'Фулл-контакт', normalized, flags=re.IGNORECASE)
    
    # Заменяем латинские буквы на кириллические для классов A, B, C
    normalized = normalized.replace('A', 'А').replace('B', 'В').replace('C', 'С')
    normalized = normalized.replace('a', 'А').replace('b', 'В').replace('c', 'С')
    
    return normalized

def format_fio_without_patronymic(fio: str) -> str:
    """
    Форматирует ФИО без отчества.
    Если ФИО заканчивается на суффикс из таблицы patronymic_exceptions (например, "оглы"),
    то удаляет последние 2 слова. В противном случае берет первые 2 слова.
    
    Примеры:
    - "Гусейнов Эмин Фуад оглы" -> "Гусейнов Эмин"
    - "Иванов Иван Петрович" -> "Иванов Иван"
    """
    if not fio:
        return ""
    
    fio_parts = fio.split()
    if len(fio_parts) <= 2:
        return fio
    
    # Ленивый импорт для избежания циклического импорта
    from db.database import get_patronymic_exceptions
    
    # Получаем список исключений из БД
    patronymic_exceptions = get_patronymic_exceptions()
    
    # Проверяем, заканчивается ли ФИО на один из суффиксов
    last_word = fio_parts[-1].lower()
    if last_word in [exc.lower() for exc in patronymic_exceptions]:
        # Если заканчивается на исключение, удаляем последние 2 слова
        return ' '.join(fio_parts[:-2])
    else:
        # Иначе берем первые 2 слова (Фамилия Имя)
        return ' '.join(fio_parts[:2])