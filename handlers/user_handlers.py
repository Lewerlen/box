# --- Стандартные библиотеки ---
import os
import html
from collections import defaultdict
from datetime import datetime
from typing import Union
# --- Сторонние библиотеки (aiogram) ---
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import BaseFilter, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, FSInputFile, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- Импорты проекта ---
from keyboards import get_main_user_keyboard, get_main_admin_keyboard, get_edit_keyboard
from utils.excel_generator import generate_preliminary_list_excel
from utils.formatters import format_weight
from utils.draw_bracket import get_seeded_participants


# --- Кэш ---
from db.cache import (get_age_categories_from_cache, get_weight_categories_from_cache,
                      get_classes_from_cache, get_ranks_from_cache, get_regions_from_cache,
                      get_cities_from_cache, get_clubs_from_cache, get_coaches_from_cache,
                      get_all_clubs_from_cache, update_cache)
# --- База данных ---
from db.database import (save_participant_data, get_participants, get_participant_by_id,
                         get_clubs, get_participants_by_club, get_all_participants_for_report,
                         get_age_categories_with_participants,
                         get_weight_categories_with_participants,
                         get_weight_categories_with_participants_by_class,
                         get_classes_with_participants, get_participants_for_approval,
                         get_participants_for_bracket)


async def show_edit_menu(message: Union[Message, CallbackQuery], state: FSMContext):
    data = await state.get_data()

    summary_parts = ["────────────\nРедактирование участника:"]
    if p_data := data.get('fio'): summary_parts.append(f"• ФИО: {p_data}")
    if p_data := data.get('gender'): summary_parts.append(f"• Пол: {p_data}")
    if p_data := data.get('dob'):
        try:
            summary_parts.append(f"• Дата рождения: {datetime.fromisoformat(p_data).strftime('%d.%m.%Y')}")
        except (TypeError, ValueError):
             summary_parts.append(f"• Дата рождения: {p_data}")
    if p_data := data.get('age_category_name'): summary_parts.append(f"• Возрастная категория: {p_data}")
    if p_data := data.get('weight_category_name'): summary_parts.append(f"• Весовая категория: {str(p_data).replace(' кг', '')}")
    if p_data := data.get('class_name'): summary_parts.append(f"• Категория: {p_data.split(' ')[0]}")
    if p_data := data.get('rank_name'): summary_parts.append(f"• Разряд: {p_data}")
    if p_data := data.get('region_name'): summary_parts.append(f"• Регион: {p_data}")
    if p_data := data.get('city_name'): summary_parts.append(f"• Город/населённый пункт: {p_data}")
    if p_data := data.get('club_name'): summary_parts.append(f"• Клуб: {p_data}")
    if p_data := data.get('coach_name'): summary_parts.append(f"• ФИО тренера: {p_data}")
    summary_parts.append("────────────")

    summary_text = "\n".join(summary_parts)
    text_to_send = f"{summary_text}\n\nВыберите поле для редактирования:"
    reply_markup = get_edit_keyboard()

    if isinstance(message, CallbackQuery):
        original_message = message.message
        try:
            await original_message.edit_text(
                text=text_to_send,
                reply_markup=reply_markup
            )
        except TelegramBadRequest as e:
            if "there is no text in the message to edit" in str(e) or "message can't be edited" in str(e):
                try:
                    await original_message.delete()
                except TelegramBadRequest:
                    pass
                new_msg = await message.bot.send_message(
                    chat_id=original_message.chat.id,
                    text=text_to_send,
                    reply_markup=reply_markup
                )
                await state.update_data(prompt_message_id=new_msg.message_id)
            else:
                print(f"Неожиданная ошибка при редактировании сообщения: {e}")
    else:
        try:
            await message.delete()
        except TelegramBadRequest as e:
            if "message to delete not found" not in str(e):
                 print(f"Ошибка при удалении сообщения пользователя: {e}")

        prompt_message_id = data.get('prompt_message_id')
        if prompt_message_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=prompt_message_id,
                    text=text_to_send,
                    reply_markup=reply_markup
                )
            except TelegramBadRequest as e:
                 print(f"Ошибка при редактировании prompt_message_id: {e}")
                 new_msg = await message.answer(
                     text=text_to_send,
                     reply_markup=reply_markup
                 )
                 await state.update_data(prompt_message_id=new_msg.message_id)
        else:
            new_msg = await message.answer(
                 text=text_to_send,
                 reply_markup=reply_markup
            )
            await state.update_data(prompt_message_id=new_msg.message_id)

# --- Фильтр для проверки прав администратора ---
class IsAdmin(BaseFilter):
    """
    Кастомный фильтр для проверки, является ли пользователь администратором.
    ID администраторов берутся из переменной окружения ADMIN_IDS.
    """
    async def __call__(self, event: Union[Message, CallbackQuery]) -> bool:
        admin_ids_str = os.getenv("ADMIN_IDS", "").split(',')
        if not admin_ids_str or not admin_ids_str[0]:
            return False
        admin_ids = {int(admin_id) for admin_id in admin_ids_str if admin_id.isdigit()}
        return event.from_user.id in admin_ids


# --- Состояния для машины состояний (FSM) ---
class RegistrationStates(StatesGroup):
    awaiting_fio = State()
    awaiting_gender = State()
    awaiting_dob = State()
    awaiting_weight_category = State()
    awaiting_class = State()
    awaiting_rank = State()
    awaiting_region = State()
    awaiting_manual_region_input = State()
    awaiting_city = State()
    awaiting_manual_city_input = State()
    awaiting_club = State()
    awaiting_manual_club_input = State()
    awaiting_coach = State()
    awaiting_manual_coach_input = State()
    awaiting_final_confirmation = State()
    awaiting_search_query = State()
    awaiting_club_search_query = State()
    awaiting_participant_search_by_club_query = State()
    awaiting_csv_file = State()
    editing_participant = State()
    awaiting_delete_confirmation = State()
    awaiting_approval = State()
    awaiting_age_category = State()
    awaiting_bracket_gender = State()
    awaiting_bracket_age_category = State()
    awaiting_bracket_weight_category = State()
    awaiting_bracket_class = State()
    awaiting_approval_page = State()
    awaiting_approval_list_selection = State()
    awaiting_approval_confirmation = State()
    awaiting_approval_swap_selection = State()
    editing_from_approval = State()
    awaiting_bracket_excel_age = State()
    awaiting_bracket_excel_weight = State()
    awaiting_bracket_excel_class = State()


user_router = Router()

# --- Клавиатуры для процесса регистрации ---
def get_registration_keyboard(current_step: str, data: dict = None):
    builder = InlineKeyboardBuilder()
    if current_step == 'gender':
        gender = data.get('gender')
        male_text = "✅ Муж" if gender == "Мужской" else "Муж"
        female_text = "✅ Жен" if gender == "Женский" else "Жен"
        builder.button(text=male_text, callback_data="gender:Мужской")
        builder.button(text=female_text, callback_data="gender:Женский")
        builder.adjust(2)

    elif current_step == 'age_category':
        gender = data.get('gender')
        if not gender:
            age_categories = get_age_categories_from_cache()
        else:
            all_categories = get_age_categories_from_cache()
            age_categories = [cat for cat in all_categories if cat.get('gender') == gender]

        for category in age_categories:
            builder.button(text=category['name'], callback_data=f"age_category:{category['id']}")
        builder.adjust(2)

    elif current_step == 'weight_category':
        age_cat_id = int(data.get('age_category_id'))
        weight_categories = get_weight_categories_from_cache(age_category_id=age_cat_id)
        for category in weight_categories:
            builder.button(text=category['name'], callback_data=f"weight_category:{category['id']}")
        builder.adjust(3)

    elif current_step == 'class':
        classes = get_classes_from_cache()
        for class_item in classes:
            builder.button(text=class_item['name'], callback_data=f"class:{class_item['id']}")
        builder.adjust(1)

    elif current_step == 'rank':
        ranks = get_ranks_from_cache()
        for rank_item in ranks:
            builder.button(text=rank_item['name'], callback_data=f"rank:{rank_item['id']}")
        builder.button(text="Пропустить ➡️", callback_data="skip_rank")
        builder.adjust(2)

    elif current_step == 'region':
        regions = get_regions_from_cache()
        for region in regions:
            builder.button(text=region['name'], callback_data=f"region:{region['id']}")
        builder.adjust(1)
        builder.row(InlineKeyboardButton(text="Ввести новый вручную", callback_data="enter_manual_region"))

    elif current_step == 'manual_region_input':
        builder.button(text="⬅️ Вернуться к списку регионов", callback_data="back_to_region_list")

    elif current_step == 'city':
        region_id = data.get('region_id')
        if region_id:
            cities = get_cities_from_cache(region_id)
            for city in cities:
                builder.button(text=city['name'], callback_data=f"city:{city['id']}")
            builder.adjust(1)
            builder.row(InlineKeyboardButton(text="Ввести новый вручную", callback_data="enter_manual_city"))

    elif current_step == 'manual_city_input':
        builder.button(text="⬅️ Вернуться к списку Городов", callback_data="back_to_city_list")

    elif current_step == 'club':
        city_id = data.get('city_id')
        if city_id:
            clubs = get_clubs_from_cache(city_id)
            for club in clubs:
                builder.button(text=club['name'], callback_data=f"club:{club['id']}")
            builder.adjust(1)
            builder.row(InlineKeyboardButton(text="Ввести новый вручную", callback_data="enter_manual_club"))

    elif current_step == 'manual_club_input':
            builder.button(text="⬅️ Вернуться к списку клубов", callback_data="back_to_club_list")

    elif current_step == 'forced_manual_club_input':
            pass

    elif current_step == 'coach':
        club_id = data.get('club_id')
        if club_id:
            coaches = get_coaches_from_cache(club_id)
            for coach in coaches:
                builder.button(text=coach['name'], callback_data=f"coach:{coach['id']}")
            builder.adjust(1)
            builder.row(InlineKeyboardButton(text="Ввести тренера вручную", callback_data="enter_manual_coach"))

    elif current_step == 'manual_coach_input':
        builder.button(text="⬅️ Вернуться к списку Тренеров", callback_data="back_to_coach_list")

    elif current_step == 'forced_manual_coach_input':
        pass

    elif current_step == 'final_confirmation':
        builder.button(text="✅ Сохранить", callback_data="save_participant")
        builder.button(text="✏️ Вернуться к редактированию", callback_data="go_back")
        builder.button(text="❌ Отменить", callback_data="cancel_registration")
        builder.adjust(1, 2)
        return builder.as_markup()

    nav_buttons = []
    if current_step != 'fio':
        if data and data.get('is_editing'):
            nav_buttons.append(
                InlineKeyboardButton(text="⬅️ Назад", callback_data="go_back")
            )
            nav_buttons.append(
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_editing")
            )
        else:
            nav_buttons.append(
                InlineKeyboardButton(text="⬅️ Назад", callback_data="go_back")
            )
            nav_buttons.append(
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_registration")
            )
        builder.row(*nav_buttons)

    return builder.as_markup()

def get_bracket_keyboard(step: str, data: dict):
    """Генерирует клавиатуру для выбора категорий для сетки."""
    builder = InlineKeyboardBuilder()
    if step == 'gender':
        # Шаг 1: Выбор пола
        builder.button(text="👨 Мужской", callback_data="bracket_gender:Мужской")
        builder.button(text="👩 Женский", callback_data="bracket_gender:Женский")
        builder.adjust(2)
        builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_main_menu"))
    elif step == 'age':
        # Шаг 2: Выбор возрастной категории для выбранного пола
        selected_gender = data.get('bracket_gender')
        age_categories = get_age_categories_with_participants()
        # Фильтруем по полу и пустые категории
        filtered_categories = [c for c in age_categories if c['gender'] == selected_gender and c['participant_count'] > 0]
        
        for category in filtered_categories:
            text = f"{category['name']} ({category['participant_count']})"
            builder.button(text=text, callback_data=f"bracket_age_cat:{category['id']}")
        
        builder.adjust(2)
        # Кнопки "Назад" и "Отмена"
        builder.row(
            InlineKeyboardButton(text="⬅️ Назад", callback_data="bracket_back_to_gender"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_main_menu")
        )
    elif step == 'class_first':
        # Новый шаг: выбор класса после выбора возраста
        age_cat_id = int(data.get('bracket_age_id'))
        classes = get_classes_with_participants(age_category_id=age_cat_id)
        # Фильтруем пустые категории
        classes = [c for c in classes if c['participant_count'] > 0]
        for class_item in classes:
            # Добавляем количество участников в скобках
            text = f"{class_item['name']} ({class_item['participant_count']})"
            builder.button(text=text, callback_data=f"bracket_class_first:{class_item['id']}")
        builder.adjust(1)
        # Кнопки "Назад" и "Отмена"
        builder.row(
            InlineKeyboardButton(text="⬅️ Назад", callback_data="tournament_lists"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_main_menu")
        )
    elif step == 'weight':
        # Выбор веса после выбора возраста и класса
        age_cat_id = int(data.get('bracket_age_id'))
        class_id = int(data.get('bracket_class_id'))
        weight_categories = get_weight_categories_with_participants_by_class(age_category_id=age_cat_id, class_id=class_id)
        # Фильтруем пустые категории
        weight_categories = [c for c in weight_categories if c['participant_count'] > 0]
        for category in weight_categories:
            # Добавляем количество участников в скобках
            text = f"{category['name']} ({category['participant_count']})"
            builder.button(text=text, callback_data=f"bracket_weight_cat:{category['id']}")
        builder.adjust(3)
        # Кнопки "Назад" и "Отмена"
        builder.row(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"bracket_age_cat:{age_cat_id}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_main_menu")
        )
    elif step == 'class':
        # Старый шаг для обратной совместимости (если используется где-то еще)
        age_cat_id = int(data.get('bracket_age_id'))
        weight_cat_id = int(data.get('bracket_weight_id'))
        classes = get_classes_with_participants(age_category_id=age_cat_id, weight_category_id=weight_cat_id)
        # Фильтруем пустые категории
        classes = [c for c in classes if c['participant_count'] > 0]
        for class_item in classes:
            # Добавляем количество участников в скобках
            text = f"{class_item['name']} ({class_item['participant_count']})"
            builder.button(text=text, callback_data=f"bracket_class:{class_item['id']}")
        builder.adjust(1)
        # Кнопки "Назад" и "Отмена" для третьего шага
        builder.row(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"bracket_weight_cat:{weight_cat_id}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_main_menu")
        )

    return builder.as_markup()


# --- Обработчик отмены регистрации ---
@user_router.callback_query(F.data == "cancel_registration", StateFilter("*"))
async def cancel_registration_handler(query: CallbackQuery, state: FSMContext):
    """Отменяет процесс регистрации и возвращает в главное меню."""
    await state.clear()
    await query.message.edit_text("Добавление отменено.")

    # Проверяем, является ли пользователь админом
    is_admin_check = IsAdmin()
    if await is_admin_check(query):
        keyboard = get_main_admin_keyboard()
    else:
        keyboard = get_main_user_keyboard()

    # Возвращаем соответствующую клавиатуру
    await query.message.answer(
        "Вы в главном меню.",
        reply_markup=keyboard
    )

# --- Обработчик кнопки "Назад" ---
@user_router.callback_query(F.data == "go_back", StateFilter("*"))
async def back_step_handler(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    if data.get('is_editing'):
        await state.set_state(RegistrationStates.editing_participant)
        await show_edit_menu(query, state)
        return

    current_state = await state.get_state()

    if current_state == RegistrationStates.awaiting_gender:
        await state.set_state(RegistrationStates.awaiting_fio)
        await query.message.edit_text(
            "Шаг 1/11. Введите Фамилию Имя Отчество участника:", # Шаг 1/11
            reply_markup=get_registration_keyboard('fio')
        )
    elif current_state == RegistrationStates.awaiting_dob:
        await state.set_state(RegistrationStates.awaiting_gender)
        await query.message.edit_text(
            "Шаг 2/11. Выберите пол:", # Шаг 2/11
            reply_markup=get_registration_keyboard('gender', data)
        )
    elif current_state == RegistrationStates.awaiting_weight_category:
        await state.set_state(RegistrationStates.awaiting_dob)
        dob_str = data.get('dob')
        dob_formatted = datetime.fromisoformat(dob_str).strftime('%d.%m.%Y') if dob_str else "Не указана"
        await query.message.edit_text(
            text=(
                f"✅ ФИО: {data.get('fio')}\n"
                f"✅ Пол: {data.get('gender')}\n\n"
                f"Шаг 3/11. Введите дату рождения (в формате ДД.ММ.ГГГГ):\n" # Шаг 3/11
                f"Текущее значение: {dob_formatted}"
            ),
            reply_markup=get_registration_keyboard('dob', data)
        )
    elif current_state == RegistrationStates.awaiting_class:
        await state.set_state(RegistrationStates.awaiting_weight_category)
        await query.message.edit_text(
            text=(
                f"✅ ФИО: {data.get('fio')}\n"
                f"✅ Пол: {data.get('gender')}\n"
                f"✅ Дата рождения: {datetime.fromisoformat(data.get('dob')).strftime('%d.%m.%Y')}\n"
                f"✅ Возрастная категория: {data.get('age_category_name')}\n\n"
                "Шаг 4/11. Выберите весовую категорию:" # Шаг 4/11
            ),
            reply_markup=get_registration_keyboard('weight_category', data)
        )
    elif current_state == RegistrationStates.awaiting_rank:
        await state.set_state(RegistrationStates.awaiting_class)
        await query.message.edit_text(
            text=(
                f"✅ ФИО: {data.get('fio')}\n"
                f"✅ Пол: {data.get('gender')}\n"
                f"✅ Дата рождения: {datetime.fromisoformat(data.get('dob')).strftime('%d.%m.%Y')}\n"
                f"✅ Возрастная категория: {data.get('age_category_name')}\n"
                f"✅ Весовая категория: {data.get('weight_category_name')}\n\n"
                "Шаг 5/11. Выберите дисциплину:" # Шаг 5/11
            ),
            reply_markup=get_registration_keyboard('class', data)
        )
    # Удаляем блоки для awaiting_rank_assignment_date и awaiting_order_number
    elif current_state == RegistrationStates.awaiting_region:
        # При возврате с шага выбора региона (7) всегда возвращаемся на шаг выбора разряда (6),
        # так как даже если класс не 'А', состояние awaiting_rank все равно проходится (с пропуском)
        await state.set_state(RegistrationStates.awaiting_rank)
        await query.message.edit_text(
            text=(
                f"✅ ФИО: {data.get('fio')}\n"
                f"✅ Пол: {data.get('gender')}\n"
                f"✅ Дата рождения: {datetime.fromisoformat(data.get('dob')).strftime('%d.%m.%Y')}\n"
                f"✅ Возрастная категория: {data.get('age_category_name')}\n"
                f"✅ Весовая категория: {data.get('weight_category_name')}\n"
                f"✅ Категория: {data.get('class_name')}\n\n"
                "Шаг 6/11. Выберите разряд (если есть):" # Шаг 6/11
            ),
            reply_markup=get_registration_keyboard('rank', data)
        )

    elif current_state in [RegistrationStates.awaiting_city, RegistrationStates.awaiting_manual_city_input]:
        await state.set_state(RegistrationStates.awaiting_region)
        summary_text_parts = []
        if 'fio' in data: summary_text_parts.append(f"✅ ФИО: {data['fio']}")
        if 'gender' in data: summary_text_parts.append(f"✅ Пол: {data['gender']}")
        if 'dob' in data: summary_text_parts.append(
            f"✅ Дата рождения: {datetime.fromisoformat(data['dob']).strftime('%d.%m.%Y')}")
        if 'age_category_name' in data: summary_text_parts.append(
            f"✅ Возрастная категория: {data['age_category_name']}")
        if 'weight_category_name' in data: summary_text_parts.append(
            f"✅ Весовая категория: {data['weight_category_name']}")
        if 'class_name' in data: summary_text_parts.append(f"✅ Категория: {data['class_name']}")
        if 'rank_name' in data and data.get('rank_name'): summary_text_parts.append(f"✅ Разряд: {data['rank_name']}") # Оставляем разряд
        # Удаляем rank_assignment_date и order_number
        summary_text = "\n".join(summary_text_parts)

        await query.message.edit_text(
            text=f"{summary_text}\n\nШаг 7/11. Выберите регион:", # Шаг 7/11
            reply_markup=get_registration_keyboard('region', data)
        )
    elif current_state in [RegistrationStates.awaiting_club, RegistrationStates.awaiting_manual_club_input]:
        await state.set_state(RegistrationStates.awaiting_city)
        summary_text_parts = []
        if 'fio' in data: summary_text_parts.append(f"✅ ФИО: {data['fio']}")
        if 'gender' in data: summary_text_parts.append(f"✅ Пол: {data['gender']}")
        if 'dob' in data: summary_text_parts.append(
            f"✅ Дата рождения: {datetime.fromisoformat(data['dob']).strftime('%d.%m.%Y')}")
        if 'age_category_name' in data: summary_text_parts.append(
            f"✅ Возрастная категория: {data['age_category_name']}")
        if 'weight_category_name' in data: summary_text_parts.append(
            f"✅ Весовая категория: {data['weight_category_name']}")
        if 'class_name' in data: summary_text_parts.append(f"✅ Категория: {data['class_name']}")
        if 'rank_name' in data and data.get('rank_name'): summary_text_parts.append(f"✅ Разряд: {data['rank_name']}")
        # Удаляем rank_assignment_date и order_number
        if 'region_name' in data: summary_text_parts.append(f"✅ Регион: {data['region_name']}")
        summary_text = "\n".join(summary_text_parts)

        if data.get('region_id') and get_cities_from_cache(data.get('region_id')):
            await state.set_state(RegistrationStates.awaiting_city)
            await query.message.edit_text(
                text=f"{summary_text}\n\nШаг 8/11. Выберите город/населенный пункт:", # Шаг 8/11
                reply_markup=get_registration_keyboard('city', data)
            )
        else:
            await state.set_state(RegistrationStates.awaiting_manual_city_input)
            await query.message.edit_text(
                text=f"{summary_text}\n\nШаг 8/11. Введите город/населённый пункт:", # Шаг 8/11
                reply_markup=get_registration_keyboard('manual_city_input', data)
            )

    elif current_state in [RegistrationStates.awaiting_coach, RegistrationStates.awaiting_manual_coach_input]:
            summary_text_parts = []
            if 'fio' in data: summary_text_parts.append(f"✅ ФИО: {data['fio']}")
            if 'gender' in data: summary_text_parts.append(f"✅ Пол: {data['gender']}")
            if 'dob' in data: summary_text_parts.append(
                f"✅ Дата рождения: {datetime.fromisoformat(data['dob']).strftime('%d.%m.%Y')}")
            if 'age_category_name' in data: summary_text_parts.append(
                f"✅ Возрастная категория: {data['age_category_name']}")
            if 'weight_category_name' in data: summary_text_parts.append(
                f"✅ Весовая категория: {data['weight_category_name']}")
            if 'class_name' in data: summary_text_parts.append(f"✅ Категория: {data['class_name']}")
            if 'rank_name' in data and data.get('rank_name'): summary_text_parts.append(f"✅ Разряд: {data['rank_name']}")
            # Удаляем rank_assignment_date и order_number
            if 'region_name' in data: summary_text_parts.append(f"✅ Регион: {data['region_name']}")
            if 'city_name' in data: summary_text_parts.append(f"✅ Город/населенный пункт: {data['city_name']}")
            summary_text = "\n".join(summary_text_parts)

            await state.set_state(RegistrationStates.awaiting_club)
            await query.message.edit_text(
                text=f"{summary_text}\n\nШаг 9/11. Выберите клуб:", # Шаг 9/11
                reply_markup=get_registration_keyboard('club', data)
            )

    elif current_state == RegistrationStates.awaiting_final_confirmation:
        summary_text_parts = []
        if 'fio' in data: summary_text_parts.append(f"✅ ФИО: {data['fio']}")
        if 'gender' in data: summary_text_parts.append(f"✅ Пол: {data['gender']}")
        if 'dob' in data: summary_text_parts.append(
            f"✅ Дата рождения: {datetime.fromisoformat(data['dob']).strftime('%d.%m.%Y')}")
        if 'age_category_name' in data: summary_text_parts.append(
            f"✅ Возрастная категория: {data['age_category_name']}")
        if 'weight_category_name' in data: summary_text_parts.append(
            f"✅ Весовая категория: {data['weight_category_name']}")
        if 'class_name' in data: summary_text_parts.append(f"✅ Категория: {data['class_name']}")
        if 'rank_name' in data and data.get('rank_name'): summary_text_parts.append(f"✅ Разряд: {data['rank_name']}")
        # Удаляем rank_assignment_date и order_number
        if 'region_name' in data: summary_text_parts.append(f"✅ Регион: {data['region_name']}")
        if 'city_name' in data: summary_text_parts.append(f"✅ Город/населенный пункт: {data['city_name']}")
        if 'club_name' in data: summary_text_parts.append(f"✅ Клуб: {data['club_name']}")
        summary_text = "\n".join(summary_text_parts)

        await state.set_state(RegistrationStates.awaiting_coach)
        await query.message.edit_text(
            text=f"{summary_text}\n\nШаг 10/11. Выберите тренера:", # Шаг 10/11
            reply_markup=get_registration_keyboard('coach', data)
        )

# --- Обработчик команды /start ---
@user_router.message(CommandStart(), ~IsAdmin())
async def cmd_start(message: Message):
    """Обработчик команды /start для обычных пользователей."""
    user_name = message.from_user.first_name
    await message.answer(
        f"Добро пожаловать, {user_name}!",
        reply_markup=get_main_user_keyboard()
    )


# --- Шаг 1: Начало регистрации и ввод ФИО ---
@user_router.callback_query(F.data == "add_participant")
async def start_registration(query: CallbackQuery, state: FSMContext):
    """
    Запускает FSM, убирает клавиатуру главного меню и запрашивает ФИО.
    """
    await query.message.edit_reply_markup(reply_markup=None)  # Убираем кнопки
    prompt_message = await query.message.answer(
        "Шаг 1/11. Введите Фамилию Имя Отчество участника:",
        reply_markup=get_registration_keyboard('fio')
    )
    await state.update_data(prompt_message_id=prompt_message.message_id)
    await state.set_state(RegistrationStates.awaiting_fio)
    await query.answer()


@user_router.message(RegistrationStates.awaiting_fio)
async def process_fio(message: Message, state: FSMContext):
    """
    Обрабатывает ФИО. В режиме регистрации переходит к выбору пола.
    В режиме редактирования возвращает в меню редактирования.
    """
    await state.update_data(fio=message.text)
    data = await state.get_data()

    if data.get('is_editing'):
        await state.set_state(RegistrationStates.editing_participant)
        await show_edit_menu(message, state)
    else:
        # Стандартная логика регистрации
        prompt_message_id = data.get('prompt_message_id')
        await message.delete()

        await message.bot.edit_message_text(
            text="Шаг 2/11. Выберите пол:",
            chat_id=message.chat.id,
            message_id=prompt_message_id,
            reply_markup=get_registration_keyboard('gender', data)
        )
        await state.set_state(RegistrationStates.awaiting_gender)

# --- Шаг 2: Выбор пола ---
@user_router.callback_query(F.data.startswith("gender:"), RegistrationStates.awaiting_gender)
async def process_gender(query: CallbackQuery, state: FSMContext):
    """
    Обрабатывает выбор пола и переходит к Шагу 3 (дата рождения).
    """
    gender = query.data.split(":")[1]
    await state.update_data(gender=gender)
    data = await state.get_data()

    if data.get('is_editing'):
        await state.set_state(RegistrationStates.editing_participant)
        await show_edit_menu(query, state)
    else:
        await query.message.edit_text(
            f"✅ ФИО: {data.get('fio')}\n"
            f"✅ Пол: {data.get('gender')}\n\n"
            "Шаг 3/11. Введите дату рождения (в формате ДД.ММ.ГГГГ):",
            reply_markup=get_registration_keyboard('dob', data)
        )
        await state.set_state(RegistrationStates.awaiting_dob)
    await query.answer()

# --- Шаг 3: Ввод и валидация даты рождения ---
@user_router.message(RegistrationStates.awaiting_dob)
async def process_dob(message: Message, state: FSMContext):
    """
    Обрабатывает введенную дату рождения, валидирует её и переходит к следующему шагу.
    Поддерживает форматы ДД.ММ.ГГГГ и ДД-ММ-ГГГГ.
    """
    date_str = message.text
    try:
        # Нормализуем разделитель и пытаемся преобразовать строку в дату
        valid_date = datetime.strptime(date_str.replace('.', '-'), '%d-%m-%Y').date()
    except ValueError:
        # Если формат неверный, отправляем сообщение об ошибке в ответ
        await message.reply("Неверная дата. Введите дату в формате ДД.ММ.ГГГГ или ДД-ММ-ГГГГ.")
        return

    # Сохраняем дату в стандартном формате ISO (ГГГГ-ММ-ДД)
    await state.update_data(dob=valid_date.isoformat())
    data = await state.get_data()

    await state.update_data(dob=valid_date.isoformat())
    data = await state.get_data()

    await message.delete()  # Удаляем сообщение с датой в любом случае
    prompt_message_id = data.get('prompt_message_id')

    if data.get('is_editing'):
        # В режиме редактирования после смены даты сбрасываем возрастную и весовую категории
        await state.update_data(age_category_id=None, age_category_name=None,
                                weight_category_id=None, weight_category_name=None)
        # Остаемся в состоянии редактирования и показываем обновленное меню
        await state.set_state(RegistrationStates.editing_participant)  # Остаемся в этом состоянии
        await show_edit_menu(message, state)  # Показываем меню с обновленными данными
    else:
        # Стандартная логика регистрации
        birth_year = valid_date.year
        gender = data.get('gender')
        age_categories = get_age_categories_from_cache()
        determined_age_category = None

        for category in age_categories:
            if category['gender'] != gender:
                continue

            min_year = category.get('min_year')
            max_year = category.get('max_year')

            if min_year is None and max_year is not None and birth_year <= max_year:
                determined_age_category = category
                break
            elif min_year is not None and max_year is not None and min_year <= birth_year <= max_year:
                determined_age_category = category
                break
            # Можно добавить обработку случая, если min_year есть, а max_year нет (для будущих категорий)

        if determined_age_category:
            await state.update_data(
                age_category_id=determined_age_category['id'],
                age_category_name=determined_age_category['name']
            )
            # Обновляем data после сохранения категории
            data = await state.get_data()

            await message.bot.edit_message_text(
                text=(
                    f"✅ ФИО: {data.get('fio')}\n"
                    f"✅ Пол: {data.get('gender')}\n"
                    f"✅ Дата рождения: {valid_date.strftime('%d.%m.%Y')}\n"
                    f"✅ Возрастная категория: {data.get('age_category_name')}\n\n"
                    "Шаг 4/11. Выберите весовую категорию:"
                ),
                chat_id=message.chat.id,
                message_id=prompt_message_id,
                reply_markup=get_registration_keyboard('weight_category', data)  # Переходим к весу
            )
            await state.set_state(RegistrationStates.awaiting_weight_category)  # Переходим к весу
        else:
            # Если категория не найдена
            # Отправляем новое сообщение вместо ответа на удаленное
            await message.answer("Не удалось определить возрастную категорию для указанного года рождения.")
            # Возвращаем пользователя на шаг ввода даты рождения (редактируем исходное промпт-сообщение)
            await state.set_state(RegistrationStates.awaiting_dob)
            await message.bot.edit_message_text(
                text=(
                    f"✅ ФИО: {data.get('fio')}\n"
                    f"✅ Пол: {data.get('gender')}\n\n"
                    "Шаг 3/11. Введите дату рождения (в формате ДД.ММ.ГГГГ):"
                ),
                chat_id=message.chat.id,
                message_id=prompt_message_id,
                reply_markup=get_registration_keyboard('dob', data)
            )


@user_router.callback_query(F.data.startswith("age_category:"), RegistrationStates.awaiting_age_category)
async def process_age_category(query: CallbackQuery, state: FSMContext):
    category_id = int(query.data.split(":")[1])
    all_categories = get_age_categories_from_cache()
    category_name = next((cat['name'] for cat in all_categories if cat['id'] == category_id), "Не найдено")

    await state.update_data(
        age_category_id=category_id,
        age_category_name=category_name,
        weight_category_id=None,
        weight_category_name=None
    )
    data = await state.get_data()

    if data.get('is_editing'):
        prompt_message_id = data.get('prompt_message_id')

        text_parts = [
            f"✅ ФИО: {data.get('fio')}",
            f"✅ Пол: {data.get('gender')}",
            f"✅ Дата рождения: {datetime.fromisoformat(data.get('dob')).strftime('%d.%m.%Y')}",
            f"✅ Возрастная категория: {data.get('age_category_name')}",
            "\nПожалуйста, выберите новую весовую категорию:"
        ]
        text = "\n".join(text_parts)

        try:
            await query.bot.edit_message_text(
                text=text,
                chat_id=query.message.chat.id,
                message_id=prompt_message_id,
                reply_markup=get_registration_keyboard('weight_category', data)
            )
        except TelegramBadRequest:
            try:
                await query.message.delete()
            except TelegramBadRequest:
                pass
            new_msg = await query.message.answer(
                text=text,
                reply_markup=get_registration_keyboard('weight_category', data)
            )
            await state.update_data(prompt_message_id=new_msg.message_id)

        await state.set_state(RegistrationStates.awaiting_weight_category)

    else:
        await query.message.edit_text(
            text=(
                f"✅ ФИО: {data.get('fio')}\n"
                f"✅ Пол: {data.get('gender')}\n"
                f"✅ Дата рождения: {datetime.fromisoformat(data.get('dob')).strftime('%d.%m.%Y')}\n"
                f"✅ Возрастная категория: {data.get('age_category_name')}\n\n"
                "Шаг 4/11. Выберите весовую категорию:"
            ),
            reply_markup=get_registration_keyboard('weight_category', data)
        )
        await state.set_state(RegistrationStates.awaiting_weight_category)
    await query.answer()

# --- Шаг 5: Выбор весовой категории ---
@user_router.callback_query(F.data.startswith("weight_category:"), RegistrationStates.awaiting_weight_category)
async def process_weight_category(query: CallbackQuery, state: FSMContext):
    """
    Обрабатывает выбор весовой категории и переходит к следующему шагу.
    """
    weight_cat_id = int(query.data.split(":")[1])
    data = await state.get_data()
    age_cat_id = int(data.get('age_category_id'))

    all_weights = get_weight_categories_from_cache(age_cat_id)
    weight_cat_name = next((cat['name'] for cat in all_weights if cat['id'] == weight_cat_id), "Не найдено")

    await state.update_data(weight_category_id=weight_cat_id, weight_category_name=weight_cat_name)
    data = await state.get_data()

    if data.get('is_editing'):
        await state.set_state(RegistrationStates.editing_participant)
        await show_edit_menu(query, state)
    else:
        available_classes = get_classes_from_cache()
        if available_classes:
            await query.message.edit_text(
                text=(
                    f"✅ ФИО: {data.get('fio')}\n"
                    f"✅ Пол: {data.get('gender')}\n"
                    f"✅ Дата рождения: {datetime.fromisoformat(data.get('dob')).strftime('%d.%m.%Y')}\n"
                    f"✅ Возрастная категория: {data.get('age_category_name')}\n"
                    f"✅ Весовая категория: {data.get('weight_category_name')}\n\n"
                    "Шаг 5/11. Выберите дисциплину:"
                ),
                reply_markup=get_registration_keyboard('class', data)
            )
            await state.set_state(RegistrationStates.awaiting_class)
        else:
            await query.message.edit_text(
                text=(
                    f"✅ ФИО: {data.get('fio')}\n"
                    f"✅ Пол: {data.get('gender')}\n"
                    f"✅ Дата рождения: {datetime.fromisoformat(data.get('dob')).strftime('%d.%m.%Y')}\n"
                    f"✅ Возрастная категория: {data.get('age_category_name')}\n"
                    f"✅ Весовая категория: {data.get('weight_category_name')}\n\n"
                    "Шаг 7/11. Выберите регион:"
                ),
                reply_markup=get_registration_keyboard('region', data)
            )
            await state.set_state(RegistrationStates.awaiting_region)
    await query.answer()

# --- Шаг 6: Выбор класса ---
@user_router.callback_query(F.data.startswith("class:"), RegistrationStates.awaiting_class)
async def process_class(query: CallbackQuery, state: FSMContext):
    class_id = int(query.data.split(":")[1])
    all_classes = get_classes_from_cache()
    class_name = next((c['name'] for c in all_classes if c['id'] == class_id), "")
    await state.update_data(class_id=class_id, class_name=class_name)
    data = await state.get_data()

    if data.get('is_editing'):
        await state.set_state(RegistrationStates.editing_participant)
        await show_edit_menu(query, state)
    else:
        # --- ЛОГИКА ПРОВЕРКИ КЛАССА ---
        # Проверяем, содержит ли имя класса букву "А" (русскую или английскую)
        if "А" in class_name.upper() or "A" in class_name.upper():
            # Если класс "А" — запрашиваем разряд
            available_ranks = get_ranks_from_cache()
            await query.message.edit_text(
                text=(
                    f"✅ ФИО: {data.get('fio')}\n"
                    f"✅ Пол: {data.get('gender')}\n"
                    f"✅ Дата рождения: {datetime.fromisoformat(data.get('dob')).strftime('%d.%m.%Y')}\n"
                    f"✅ Возрастная категория: {data.get('age_category_name')}\n"
                    f"✅ Весовая категория: {data.get('weight_category_name')}\n"
                    f"✅ Категория: {data.get('class_name')}\n\n"
                    "Шаг 6/11. Выберите разряд (если есть):"
                ),
                reply_markup=get_registration_keyboard('rank', data)
            )
            await state.set_state(RegistrationStates.awaiting_rank)
        else:
            # Если класс НЕ "А" — пропускаем разряд и идем к Региону
            # Явно обнуляем данные разряда
            await state.update_data(rank_id=None, rank_name=None, rank_assignment_date=None, order_number=None)

            await query.message.edit_text(
                text=(
                    f"✅ ФИО: {data.get('fio')}\n"
                    f"✅ Пол: {data.get('gender')}\n"
                    f"✅ Дата рождения: {datetime.fromisoformat(data.get('dob')).strftime('%d.%m.%Y')}\n"
                    f"✅ Возрастная категория: {data.get('age_category_name')}\n"
                    f"✅ Весовая категория: {data.get('weight_category_name')}\n"
                    f"✅ Категория: {data.get('class_name')}\n\n"
                    "Шаг 7/11. Выберите регион:"
                ),
                reply_markup=get_registration_keyboard('region', data)
            )
            await state.set_state(RegistrationStates.awaiting_region)

    await query.answer()

# --- Шаг 7: Выбор разряда ---
@user_router.callback_query(F.data.startswith("rank:"), RegistrationStates.awaiting_rank)
async def process_rank(query: CallbackQuery, state: FSMContext):
    rank_id = int(query.data.split(":")[1])
    all_ranks = get_ranks_from_cache()
    rank_name = next((r['name'] for r in all_ranks if r['id'] == rank_id), "")
    await state.update_data(rank_id=rank_id, rank_name=rank_name)
    data = await state.get_data()

    if data.get('is_editing'):
        await state.set_state(RegistrationStates.editing_participant)
        await show_edit_menu(query, state)
    else:
        rank_text = f"✅ Разряд: {data.get('rank_name')}\n" if data.get('rank_name') else ""
        await query.message.edit_text(
            text=(
                f"✅ ФИО: {data.get('fio')}\n"
                f"✅ Пол: {data.get('gender')}\n"
                f"✅ Дата рождения: {datetime.fromisoformat(data.get('dob')).strftime('%d.%m.%Y')}\n"
                f"✅ Возрастная категория: {data.get('age_category_name')}\n"
                f"✅ Весовая категория: {data.get('weight_category_name')}\n"
                f"✅ Категория: {data.get('class_name')}\n"
                f"{rank_text}\n"
                "Шаг 7/11. Выберите регион:"
            ),
            reply_markup=get_registration_keyboard('region', data)
        )
        await state.set_state(RegistrationStates.awaiting_region)
    await query.answer()

@user_router.callback_query(F.data == "skip_rank", RegistrationStates.awaiting_rank)
async def skip_rank_handler(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if data.get('is_editing'):
        await state.update_data(rank_id=None, rank_name=None, rank_assignment_date=None, order_number=None)
        await state.set_state(RegistrationStates.editing_participant)
        await show_edit_menu(query, state)
    else:
        await state.update_data(rank_id=None, rank_name=None, rank_assignment_date=None, order_number=None) # Явно обнуляем данные разряда
        await query.message.edit_text(
            text=(
                f"✅ ФИО: {data.get('fio')}\n"
                f"✅ Пол: {data.get('gender')}\n"
                f"✅ Дата рождения: {datetime.fromisoformat(data.get('dob')).strftime('%d.%m.%Y')}\n"
                f"✅ Возрастная категория: {data.get('age_category_name')}\n"
                f"✅ Весовая категория: {data.get('weight_category_name')}\n"
                f"✅ Категория: {data.get('class_name')}\n\n"
                "Шаг 7/11. Выберите регион:" # Номер шага изменен
            ),
            reply_markup=get_registration_keyboard('region', data)
        )
        await state.set_state(RegistrationStates.awaiting_region)
    await query.answer()


# --- Шаг 10: Выбор региона ---
@user_router.callback_query(F.data.startswith("region:"), RegistrationStates.awaiting_region)
async def process_region_selection(query: CallbackQuery, state: FSMContext):
    region_id = int(query.data.split(":")[1])
    all_regions = get_regions_from_cache()
    region_name = next((r['name'] for r in all_regions if r['id'] == region_id), "")

    await state.update_data(region_id=region_id, region_name=region_name)
    data = await state.get_data()

    if data.get('is_editing'):
        await state.set_state(RegistrationStates.editing_participant)
        await show_edit_menu(query, state)
    else:
        summary_text_parts = []
        if 'fio' in data: summary_text_parts.append(f"✅ ФИО: {data['fio']}")
        if 'gender' in data: summary_text_parts.append(f"✅ Пол: {data['gender']}")
        if 'dob' in data: summary_text_parts.append(
            f"✅ Дата рождения: {datetime.fromisoformat(data['dob']).strftime('%d.%m.%Y')}")
        if 'age_category_name' in data: summary_text_parts.append(f"✅ Возрастная категория: {data['age_category_name']}")
        if 'weight_category_name' in data: summary_text_parts.append(f"✅ Весовая категория: {data['weight_category_name']}")
        if 'class_name' in data: summary_text_parts.append(f"✅ Категория: {data['class_name']}")
        if 'rank_name' in data and data.get('rank_name'): summary_text_parts.append(f"✅ Разряд: {data['rank_name']}")
        if 'region_name' in data: summary_text_parts.append(f"✅ Регион: {data['region_name']}")
        summary_text = "\n".join(summary_text_parts)

        if get_cities_from_cache(region_id):
            await query.message.edit_text(
                text=f"{summary_text}\n\nШаг 8/11. Выберите город/населенный пункт:",
                reply_markup=get_registration_keyboard('city', data)
            )
            await state.set_state(RegistrationStates.awaiting_city)
        else:
            await query.message.edit_text(
                text=f"{summary_text}\n\nШаг 8/11. Введите город/населённый пункт:",
                reply_markup=get_registration_keyboard('manual_city_input', data)
            )
            await state.set_state(RegistrationStates.awaiting_manual_city_input)
    await query.answer()


@user_router.callback_query(F.data == "enter_manual_region", RegistrationStates.awaiting_region)
async def handle_manual_region_button(query: CallbackQuery, state: FSMContext):
    """Обрабатывает нажатие на кнопку 'Ввести новый вручную'."""
    await query.message.edit_text(
        text="Введите Область/республику/край:",
        reply_markup=get_registration_keyboard('manual_region_input')
    )
    await state.set_state(RegistrationStates.awaiting_manual_region_input)
    await query.answer()


@user_router.callback_query(F.data == "back_to_region_list", RegistrationStates.awaiting_manual_region_input)
async def handle_back_to_region_list(query: CallbackQuery, state: FSMContext):
    """Обрабатывает возврат к списку регионов со страницы ручного ввода."""
    data = await state.get_data()

    # Восстанавливаем текст предыдущего шага
    summary_text_parts = []
    if 'fio' in data: summary_text_parts.append(f"✅ ФИО: {data['fio']}")
    if 'gender' in data: summary_text_parts.append(f"✅ Пол: {data['gender']}")
    if 'dob' in data: summary_text_parts.append(
        f"✅ Дата рождения: {datetime.fromisoformat(data['dob']).strftime('%d.%m.%Y')}")
    if 'age_category_name' in data: summary_text_parts.append(f"✅ Возрастная категория: {data['age_category_name']}")
    if 'weight_category_name' in data: summary_text_parts.append(f"✅ Весовая категория: {data['weight_category_name']}")
    if 'class_name' in data: summary_text_parts.append(f"✅ Категория: {data['class_name']}")
    if 'rank_name' in data and data.get('rank_name'): summary_text_parts.append(f"✅ Разряд: {data['rank_name']}")
    if 'rank_assignment_date' in data and data.get('rank_assignment_date'): summary_text_parts.append(
        f"✅ Дата присвоения: {datetime.fromisoformat(data['rank_assignment_date']).strftime('%d.%m.%Y')}")
    if 'order_number' in data and data.get('order_number'): summary_text_parts.append(f"✅ Номер приказа: {data['order_number']}")

    summary_text = "\n".join(summary_text_parts)

    await query.message.edit_text(
        text=f"{summary_text}\n\nШаг 7/11. Выберите регион:",
        reply_markup=get_registration_keyboard('region', data)
    )
    await state.set_state(RegistrationStates.awaiting_region)
    await query.answer()

# --- Шаг 10.2: Обработка ручного ввода региона ---
@user_router.message(RegistrationStates.awaiting_manual_region_input)
async def process_manual_region_input(message: Message, state: FSMContext):
    """Обрабатывает ручной ввод региона и переходит к следующему шагу."""
    # Сохраняем название и обнуляем ID, т.к. это новая запись
    await state.update_data(region_name=message.text, region_id=None)
    await message.delete()

    data = await state.get_data()
    prompt_message_id = data.get('prompt_message_id')

    # Формируем итоговый текст со всеми данными
    summary_text_parts = []
    if 'fio' in data: summary_text_parts.append(f"✅ ФИО: {data['fio']}")
    if 'gender' in data: summary_text_parts.append(f"✅ Пол: {data['gender']}")
    if 'dob' in data: summary_text_parts.append(f"✅ Дата рождения: {datetime.fromisoformat(data['dob']).strftime('%d.%m.%Y')}")
    if 'age_category_name' in data: summary_text_parts.append(f"✅ Возрастная категория: {data['age_category_name']}")
    if 'weight_category_name' in data: summary_text_parts.append(f"✅ Весовая категория: {data['weight_category_name']}")
    if 'class_name' in data: summary_text_parts.append(f"✅ Категория: {data['class_name']}")
    if 'rank_name' in data and data.get('rank_name'): summary_text_parts.append(f"✅ Разряд: {data['rank_name']}")
    if 'rank_assignment_date' in data and data.get('rank_assignment_date'): summary_text_parts.append(f"✅ Дата присвоения: {datetime.fromisoformat(data['rank_assignment_date']).strftime('%d.%m.%Y')}")
    if 'order_number' in data and data.get('order_number'): summary_text_parts.append(f"✅ Номер приказа: {data['order_number']}")
    if 'region_name' in data: summary_text_parts.append(f"✅ Регион: {data['region_name']}")
    summary_text = "\n".join(summary_text_parts)

    # Так как регион был введен вручную, сразу переходим к ручному вводу города
    await message.bot.edit_message_text(
        text=f"{summary_text}\n\nШаг 8/11. Введите город/населённый пункт:",
        chat_id=message.chat.id,
        message_id=prompt_message_id,
        reply_markup=get_registration_keyboard('manual_city_input', data)
    )
    await state.set_state(RegistrationStates.awaiting_manual_city_input)

# --- Шаг 11: Выбор города ---
@user_router.callback_query(F.data.startswith("city:"), RegistrationStates.awaiting_city)
async def process_city_selection(query: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор города из списка и переходит к следующему шагу."""
    city_id = int(query.data.split(":")[1])
    data = await state.get_data()
    all_cities = get_cities_from_cache(data.get('region_id'))
    city_name = next((c['name'] for c in all_cities if c['id'] == city_id), "")

    await state.update_data(city_id=city_id, city_name=city_name)
    data = await state.get_data()

    # Формируем итоговый текст со всеми данными
    summary_text_parts = []
    if 'fio' in data: summary_text_parts.append(f"✅ ФИО: {data['fio']}")
    if 'gender' in data: summary_text_parts.append(f"✅ Пол: {data['gender']}")
    if 'dob' in data: summary_text_parts.append(
        f"✅ Дата рождения: {datetime.fromisoformat(data['dob']).strftime('%d.%m.%Y')}")
    if 'age_category_name' in data: summary_text_parts.append(f"✅ Возрастная категория: {data['age_category_name']}")
    if 'weight_category_name' in data: summary_text_parts.append(
        f"✅ Весовая категория: {data['weight_category_name']}")
    if 'class_name' in data: summary_text_parts.append(f"✅ Категория: {data['class_name']}")
    if 'rank_name' in data and data.get('rank_name'): summary_text_parts.append(f"✅ Разряд: {data['rank_name']}")
    if 'rank_assignment_date' in data and data.get('rank_assignment_date'): summary_text_parts.append(
        f"✅ Дата присвоения: {datetime.fromisoformat(data['rank_assignment_date']).strftime('%d.%m.%Y')}")
    if 'order_number' in data and data.get('order_number'): summary_text_parts.append(f"✅ Номер приказа: {data['order_number']}")
    if 'region_name' in data: summary_text_parts.append(f"✅ Регион: {data['region_name']}")
    if 'city_name' in data: summary_text_parts.append(f"✅ Город/населенный пункт: {data['city_name']}")
    summary_text = "\n".join(summary_text_parts)

    # Переходим к выбору клуба
    await query.message.edit_text(
        text=f"{summary_text}\n\nШаг 9/11. Выберите клуб:",  # Шаг 9/11
        reply_markup=get_registration_keyboard('club', data)
    )
    await state.set_state(RegistrationStates.awaiting_club)

    await query.answer()


@user_router.callback_query(F.data == "enter_manual_city", RegistrationStates.awaiting_city)
async def handle_manual_city_button(query: CallbackQuery, state: FSMContext):
    """Обрабатывает нажатие на кнопку 'Ввести новый вручную' для города."""
    await query.message.edit_text(
        text="Введите Город/населённый пункт:",
        reply_markup=get_registration_keyboard('manual_city_input')
    )
    await state.set_state(RegistrationStates.awaiting_manual_city_input)
    await query.answer()


@user_router.callback_query(F.data == "back_to_city_list", RegistrationStates.awaiting_manual_city_input)
async def handle_back_to_city_list(query: CallbackQuery, state: FSMContext):
    """Обрабатывает возврат к списку городов со страницы ручного ввода."""
    data = await state.get_data()
    # Восстанавливаем текст, который был на шаге выбора региона
    summary_text_parts = []
    if 'fio' in data: summary_text_parts.append(f"✅ ФИО: {data['fio']}")
    if 'gender' in data: summary_text_parts.append(f"✅ Пол: {data['gender']}")
    if 'dob' in data: summary_text_parts.append(
        f"✅ Дата рождения: {datetime.fromisoformat(data['dob']).strftime('%d.%m.%Y')}")
    if 'age_category_name' in data: summary_text_parts.append(f"✅ Возрастная категория: {data['age_category_name']}")
    if 'weight_category_name' in data: summary_text_parts.append(
        f"✅ Весовая категория: {data['weight_category_name']}")
    if 'class_name' in data: summary_text_parts.append(f"✅ Категория: {data['class_name']}")
    if 'rank_name' in data and data.get('rank_name'): summary_text_parts.append(f"✅ Разряд: {data['rank_name']}")
    if 'rank_assignment_date' in data and data.get('rank_assignment_date'): summary_text_parts.append(
        f"✅ Дата присвоения: {datetime.fromisoformat(data['rank_assignment_date']).strftime('%d.%m.%Y')}")
    if 'order_number' in data and data.get('order_number'): summary_text_parts.append(f"✅ Номер приказа: {data['order_number']}")
    if 'region_name' in data: summary_text_parts.append(f"✅ Регион: {data['region_name']}")
    summary_text = "\n".join(summary_text_parts)

    await query.message.edit_text(
        text=f"{summary_text}\n\nШаг 8/11. Выберите город/населенный пункт:",  # Шаг 8/11
        reply_markup=get_registration_keyboard('city', data)
    )
    await state.set_state(RegistrationStates.awaiting_city)
    await query.answer()


@user_router.message(RegistrationStates.awaiting_manual_city_input)
async def process_manual_city_input(message: Message, state: FSMContext):
    """Обрабатывает ручной ввод города и переходит к следующему шагу."""
    await state.update_data(city_name=message.text, city_id=None)
    data = await state.get_data()

    if data.get('is_editing'):
        await state.set_state(RegistrationStates.editing_participant)
        await show_edit_menu(message, state)
    else:
        await message.delete()
        summary_text_parts = []
        if 'fio' in data: summary_text_parts.append(f"✅ ФИО: {data['fio']}")
        if 'gender' in data: summary_text_parts.append(f"✅ Пол: {data['gender']}")
        if 'dob' in data: summary_text_parts.append(
            f"✅ Дата рождения: {datetime.fromisoformat(data['dob']).strftime('%d.%m.%Y')}")
        if 'age_category_name' in data: summary_text_parts.append(f"✅ Возрастная категория: {data['age_category_name']}")
        if 'weight_category_name' in data: summary_text_parts.append(
            f"✅ Весовая категория: {data['weight_category_name']}")
        if 'class_name' in data: summary_text_parts.append(f"✅ Категория: {data['class_name']}")
        if 'rank_name' in data and data.get('rank_name'): summary_text_parts.append(f"✅ Разряд: {data['rank_name']}")
        if 'rank_assignment_date' in data and data.get('rank_assignment_date'): summary_text_parts.append(
            f"✅ Дата присвоения: {datetime.fromisoformat(data['rank_assignment_date']).strftime('%d.%m.%Y')}")
        if 'order_number' in data and data.get('order_number'): summary_text_parts.append(f"✅ Номер приказа: {data['order_number']}")
        if 'region_name' in data: summary_text_parts.append(f"✅ Регион: {data['region_name']}")
        if 'city_name' in data: summary_text_parts.append(f"✅ Город/населенный пункт: {data['city_name']}")
        summary_text = "\n".join(summary_text_parts)

        prompt_message_id = data.get('prompt_message_id')

        await message.bot.edit_message_text(
            text=f"{summary_text}\n\nШаг 9/11. Введите название Клуба:",
            chat_id=message.chat.id,
            message_id=prompt_message_id,
            reply_markup=get_registration_keyboard('forced_manual_club_input', data)
        )
        await state.set_state(RegistrationStates.awaiting_manual_club_input)


# --- Шаг 12: Выбор клуба ---
@user_router.callback_query(F.data.startswith("club:"), RegistrationStates.awaiting_club)
async def process_club_selection(query: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор клуба из списка и переходит к следующему шагу."""
    club_id = int(query.data.split(":")[1])
    data = await state.get_data()
    all_clubs = get_clubs_from_cache(data.get('city_id'))
    club_name = next((c['name'] for c in all_clubs if c['id'] == club_id), "")
    await state.update_data(club_id=club_id, club_name=club_name)
    data = await state.get_data()

    if data.get('is_editing'):
        await state.set_state(RegistrationStates.editing_participant)
        await show_edit_menu(query, state)
    else:
        summary_text_parts = []
        if 'fio' in data: summary_text_parts.append(f"✅ ФИО: {data['fio']}")
        if 'gender' in data: summary_text_parts.append(f"✅ Пол: {data['gender']}")
        if 'dob' in data: summary_text_parts.append(
            f"✅ Дата рождения: {datetime.fromisoformat(data['dob']).strftime('%d.%m.%Y')}")
        if 'age_category_name' in data: summary_text_parts.append(f"✅ Возрастная категория: {data['age_category_name']}")
        if 'weight_category_name' in data: summary_text_parts.append(f"✅ Весовая категория: {data['weight_category_name']}")
        if 'class_name' in data: summary_text_parts.append(f"✅ Категория: {data['class_name']}")
        if 'rank_name' in data and data.get('rank_name'): summary_text_parts.append(f"✅ Разряд: {data['rank_name']}")
        if 'rank_assignment_date' in data and data.get('rank_assignment_date'): summary_text_parts.append(
            f"✅ Дата присвоения: {datetime.fromisoformat(data['rank_assignment_date']).strftime('%d.%m.%Y')}")
        if 'order_number' in data and data.get('order_number'): summary_text_parts.append(f"✅ Номер приказа: {data['order_number']}")
        if 'region_name' in data: summary_text_parts.append(f"✅ Регион: {data['region_name']}")
        if 'city_name' in data: summary_text_parts.append(f"✅ Город/населенный пункт: {data['city_name']}")
        if 'club_name' in data: summary_text_parts.append(f"✅ Клуб: {data['club_name']}")
        summary_text = "\n".join(summary_text_parts)

        await query.message.edit_text(
            text=f"{summary_text}\n\nШаг 10/11. Выберите тренера:",
            reply_markup=get_registration_keyboard('coach', data)
        )
        await state.set_state(RegistrationStates.awaiting_coach)
    await query.answer()


@user_router.callback_query(F.data == "enter_manual_club", RegistrationStates.awaiting_club)
async def handle_manual_club_button(query: CallbackQuery, state: FSMContext):
    """Обрабатывает нажатие на кнопку 'Ввести новый вручную' для клуба."""
    await query.message.edit_text(
        text="Введите название Клуба:",
        reply_markup=get_registration_keyboard('manual_club_input')
    )
    await state.set_state(RegistrationStates.awaiting_manual_club_input)
    await query.answer()


@user_router.callback_query(F.data == "back_to_club_list", RegistrationStates.awaiting_manual_club_input)
async def handle_back_to_club_list(query: CallbackQuery, state: FSMContext):
    """Обрабатывает возврат к списку клубов."""
    data = await state.get_data()

    # Формируем итоговый текст со всеми данными, включая город
    summary_text_parts = []
    if 'fio' in data: summary_text_parts.append(f"✅ ФИО: {data['fio']}")
    # Формируем итоговый текст со всеми данными, включая город
    summary_text_parts = []
    if 'fio' in data: summary_text_parts.append(f"✅ ФИО: {data['fio']}")
    if 'gender' in data: summary_text_parts.append(f"✅ Пол: {data['gender']}")
    if 'dob' in data: summary_text_parts.append(
        f"✅ Дата рождения: {datetime.fromisoformat(data['dob']).strftime('%d.%m.%Y')}")
    if 'age_category_name' in data: summary_text_parts.append(f"✅ Возрастная категория: {data['age_category_name']}")
    if 'weight_category_name' in data: summary_text_parts.append(
        f"✅ Весовая категория: {data['weight_category_name']}")
    if 'class_name' in data: summary_text_parts.append(f"✅ Категория: {data['class_name']}")
    if 'rank_name' in data and data.get('rank_name'): summary_text_parts.append(f"✅ Разряд: {data['rank_name']}")
    if 'rank_assignment_date' in data and data.get('rank_assignment_date'): summary_text_parts.append(
        f"✅ Дата присвоения: {datetime.fromisoformat(data['rank_assignment_date']).strftime('%d.%m.%Y')}")
    if 'order_number' in data and data.get('order_number'): summary_text_parts.append(f"✅ Номер приказа: {data['order_number']}")
    if 'region_name' in data: summary_text_parts.append(f"✅ Регион: {data['region_name']}")
    if 'city_name' in data: summary_text_parts.append(f"✅ Город/населенный пункт: {data['city_name']}")
    summary_text = "\n".join(summary_text_parts)

    await query.message.edit_text(
        text=f"{summary_text}\n\nШаг 9/11. Выберите клуб:",
        reply_markup=get_registration_keyboard('club', data)
    )
    await state.set_state(RegistrationStates.awaiting_club)
    await query.answer()


@user_router.message(RegistrationStates.awaiting_manual_club_input)
async def process_manual_club_input(message: Message, state: FSMContext):
    """Обрабатывает ручной ввод клуба."""
    await state.update_data(club_name=message.text, club_id=None)
    await message.delete()
    data = await state.get_data()

    data = await state.get_data()
    prompt_message_id = data.get('prompt_message_id')

    summary_text_parts = []
    if 'fio' in data: summary_text_parts.append(f"✅ ФИО: {data['fio']}")
    if 'gender' in data: summary_text_parts.append(f"✅ Пол: {data['gender']}")
    if 'dob' in data: summary_text_parts.append(
        f"✅ Дата рождения: {datetime.fromisoformat(data['dob']).strftime('%d.%m.%Y')}")
    if 'age_category_name' in data: summary_text_parts.append(f"✅ Возрастная категория: {data['age_category_name']}")
    if 'weight_category_name' in data: summary_text_parts.append(f"✅ Весовая категория: {data['weight_category_name']}")
    if 'class_name' in data: summary_text_parts.append(f"✅ Категория: {data['class_name']}")
    if 'rank_name' in data and data.get('rank_name'): summary_text_parts.append(f"✅ Разряд: {data['rank_name']}")
    if 'rank_assignment_date' in data and data.get('rank_assignment_date'): summary_text_parts.append(
        f"✅ Дата присвоения: {datetime.fromisoformat(data['rank_assignment_date']).strftime('%d.%m.%Y')}")
    if 'order_number' in data and data.get('order_number'): summary_text_parts.append(f"✅ Номер приказа: {data['order_number']}")
    if 'region_name' in data: summary_text_parts.append(f"✅ Регион: {data['region_name']}")
    if 'city_name' in data: summary_text_parts.append(f"✅ Город/населенный пункт: {data['city_name']}")
    if 'club_name' in data: summary_text_parts.append(f"✅ Клуб: {data['club_name']}")
    summary_text = "\n".join(summary_text_parts)

    # Так как клуб был введен вручную, сразу переходим к ручному вводу тренера
    await message.bot.edit_message_text(
        text=f"{summary_text}\n\nШаг 10/11. Введите Тренера:",
        chat_id=message.chat.id,
        message_id=prompt_message_id,
        reply_markup=get_registration_keyboard('forced_manual_coach_input', data)
    )
    await state.set_state(RegistrationStates.awaiting_manual_coach_input)


# --- Шаг 13: Выбор тренера ---
@user_router.callback_query(F.data.startswith("coach:"), RegistrationStates.awaiting_coach)
async def process_coach_selection(query: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор тренера из списка и завершает регистрацию."""
    coach_id = int(query.data.split(":")[1])
    data = await state.get_data()
    all_coaches = get_coaches_from_cache(data.get('club_id'))
    coach_name = next((c['name'] for c in all_coaches if c['id'] == coach_id), "")
    await state.update_data(coach_id=coach_id, coach_name=coach_name)

    data = await state.get_data()  # Перезапрашиваем данные после обновления

    if data.get('is_editing'):
        await state.set_state(RegistrationStates.editing_participant)
        await show_edit_menu(query, state)
    else:
        summary_text_parts = ["────────────"]
        if 'fio' in data: summary_text_parts.append(f"• ФИО: {data['fio']}")
        if 'gender' in data: summary_text_parts.append(f"• Пол: {data['gender']}")
        if 'dob' in data: summary_text_parts.append(
            f"• Дата рождения: {datetime.fromisoformat(data['dob']).strftime('%d.%m.%Y')}")
        if 'age_category_name' in data: summary_text_parts.append(f"• Возрастная категория: {data['age_category_name']}")
        if data.get('weight_category_name'): summary_text_parts.append(
            f"• Весовая категория: {data['weight_category_name'].replace(' кг', '')}")
        if data.get('class_name'): summary_text_parts.append(f"• Категория: {data['class_name'].split(' ')[0]}")
        if 'rank_name' in data and data.get('rank_name'): summary_text_parts.append(f"• Разряд: {data['rank_name']}")
        if 'rank_assignment_date' in data and data.get('rank_assignment_date'): summary_text_parts.append(
            f"• Дата присвоения: {datetime.fromisoformat(data['rank_assignment_date']).strftime('%d.%m.%Y')}")
        if 'order_number' in data and data.get('order_number'): summary_text_parts.append(f"• Номер приказа: {data['order_number']}")
        if 'region_name' in data: summary_text_parts.append(f"• Регион: {data['region_name']}")
        if 'city_name' in data: summary_text_parts.append(f"• Город/населённый пункт: {data['city_name']}")
        if 'club_name' in data: summary_text_parts.append(f"• Клуб: {data['club_name']}")
        if 'coach_name' in data: summary_text_parts.append(f"• ФИО тренера: {data['coach_name']}")
        summary_text_parts.append("────────────")
        summary_text = "\n".join(summary_text_parts)

        await query.message.edit_text(
            text=f"Проверьте данные перед сохранением:\n\n{summary_text}",
            reply_markup=get_registration_keyboard('final_confirmation', data)
        )
        await state.set_state(RegistrationStates.awaiting_final_confirmation)
    await query.answer()


@user_router.callback_query(F.data == "enter_manual_coach", RegistrationStates.awaiting_coach)
async def handle_manual_coach_button(query: CallbackQuery, state: FSMContext):
    """Обрабатывает нажатие на кнопку 'Ввести тренера вручную'."""
    await query.message.edit_text(
        text="Введите Тренера:",
        reply_markup=get_registration_keyboard('manual_coach_input')
    )
    await state.set_state(RegistrationStates.awaiting_manual_coach_input)
    await query.answer()


@user_router.callback_query(F.data == "back_to_coach_list", RegistrationStates.awaiting_manual_coach_input)
async def handle_back_to_coach_list(query: CallbackQuery, state: FSMContext):
    """Обрабатывает возврат к списку тренеров."""
    data = await state.get_data()

    summary_text_parts = []
    if 'fio' in data: summary_text_parts.append(f"✅ ФИО: {data['fio']}")
    if 'gender' in data: summary_text_parts.append(f"✅ Пол: {data['gender']}")
    if 'dob' in data: summary_text_parts.append(
        f"✅ Дата рождения: {datetime.fromisoformat(data['dob']).strftime('%d.%m.%Y')}")
    if 'age_category_name' in data: summary_text_parts.append(f"✅ Возрастная категория: {data['age_category_name']}")
    if 'weight_category_name' in data: summary_text_parts.append(f"✅ Весовая категория: {data['weight_category_name']}")
    if 'class_name' in data: summary_text_parts.append(f"✅ Категория: {data['class_name']}")
    if 'rank_name' in data and data.get('rank_name'): summary_text_parts.append(f"✅ Разряд: {data['rank_name']}")
    if 'rank_assignment_date' in data and data.get('rank_assignment_date'): summary_text_parts.append(
        f"✅ Дата присвоения: {datetime.fromisoformat(data['rank_assignment_date']).strftime('%d.%m.%Y')}")
    if 'order_number' in data and data.get('order_number'): summary_text_parts.append(f"✅ Номер приказа: {data['order_number']}")
    if 'region_name' in data: summary_text_parts.append(f"✅ Регион: {data['region_name']}")
    if 'city_name' in data: summary_text_parts.append(f"✅ Город/населенный пункт: {data['city_name']}")
    if 'club_name' in data: summary_text_parts.append(f"✅ Клуб: {data['club_name']}")
    summary_text = "\n".join(summary_text_parts)

    await query.message.edit_text(
        text=f"{summary_text}\n\nШаг 10/11. Выберите тренера:",
        reply_markup=get_registration_keyboard('coach', data)
    )
    await state.set_state(RegistrationStates.awaiting_coach)
    await query.answer()


@user_router.message(RegistrationStates.awaiting_manual_coach_input)
async def process_manual_coach_input(message: Message, state: FSMContext):
    """Обрабатывает ручной ввод тренера и завершает регистрацию."""
    await state.update_data(coach_name=message.text, coach_id=None)
    data = await state.get_data()

    if data.get('is_editing'):
        await state.set_state(RegistrationStates.editing_participant)
        await show_edit_menu(message, state)
    else:
        await message.delete()
        prompt_message_id = data.get('prompt_message_id')
        summary_text_parts = ["────────────"]
        if 'fio' in data: summary_text_parts.append(f"• ФИО: {data['fio']}")
        if 'gender' in data: summary_text_parts.append(f"• Пол: {data['gender']}")
        if 'dob' in data: summary_text_parts.append(
            f"• Дата рождения: {datetime.fromisoformat(data['dob']).strftime('%d.%m.%Y')}")
        if 'age_category_name' in data: summary_text_parts.append(f"• Возрастная категория: {data['age_category_name']}")
        if data.get('weight_category_name'): summary_text_parts.append(
            f"• Весовая категория: {data['weight_category_name'].replace(' кг', '')}")
        if data.get('class_name'): summary_text_parts.append(f"• Категория: {data['class_name'].split(' ')[0]}")
        if 'rank_name' in data and data.get('rank_name'): summary_text_parts.append(f"• Разряд: {data['rank_name']}")
        if 'rank_assignment_date' in data and data.get('rank_assignment_date'): summary_text_parts.append(
            f"• Дата присвоения: {datetime.fromisoformat(data['rank_assignment_date']).strftime('%d.%m.%Y')}")
        if 'order_number' in data and data.get('order_number'): summary_text_parts.append(f"• Номер приказа: {data['order_number']}")
        if 'region_name' in data: summary_text_parts.append(f"• Регион: {data['region_name']}")
        if 'city_name' in data: summary_text_parts.append(f"• Город/населённый пункт: {data['city_name']}")
        if 'club_name' in data: summary_text_parts.append(f"• Клуб: {data['club_name']}")
        if 'coach_name' in data: summary_text_parts.append(f"• ФИО тренера: {data['coach_name']}")
        summary_text_parts.append("────────────")
        summary_text = "\n".join(summary_text_parts)

        await message.bot.edit_message_text(
            text=f"Проверьте данные перед сохранением:\n\n{summary_text}",
            chat_id=message.chat.id,
            message_id=prompt_message_id,
            reply_markup=get_registration_keyboard('final_confirmation', data)
        )
        await state.set_state(RegistrationStates.awaiting_final_confirmation)

# --- Шаг 14: Финальное подтверждение и сохранение ---
@user_router.callback_query(F.data == "save_participant", RegistrationStates.awaiting_final_confirmation)
async def save_registration(query: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()

        new_entities_added = (
                data.get("region_id") is None and data.get("region_name") or
                data.get("city_id") is None and data.get("city_name") or
                data.get("club_id") is None and data.get("club_name") or
                data.get("coach_id") is None and data.get("coach_name")
        )

        # Удаляем ненужные ключи перед сохранением
        data.pop('rank_assignment_date', None)
        # Явно устанавливаем rank_name в None, если разряд не был выбран
        if 'rank_name' not in data or data.get('rank_name') is None:
            data['rank_name'] = None
            data['rank_id'] = None
            data['rank_assigned_on'] = None
            data['order_number'] = None
        else:
            # Убеждаемся, что rank_assigned_on и order_number будут None, если они не были введены
            data['rank_assigned_on'] = data.get('rank_assigned_on') # Если ключа нет, get вернет None
            data['order_number'] = data.get('order_number') # Если ключа нет, get вернет None

        status = save_participant_data(data, tgid_who_added=query.from_user.id)
        if status == "created":
            final_message = f"✅ Добавлен участник: {data.get('fio')}"
        elif status == "updated":
            final_message = f"✅ Обновлён участник: {data.get('fio')}"
        else:
            final_message = "Данные сохранены."

        if new_entities_added:
            update_cache()
        await query.message.edit_text(final_message, reply_markup=None)
        await query.answer()


    except Exception as e:
        await query.message.edit_text(f"Произошла ошибка при сохранении: {e}")
        await query.answer("Ошибка!", show_alert=True)

        await state.clear()

        is_admin_check = IsAdmin()
        if await is_admin_check(query):
            keyboard = get_main_admin_keyboard()
        else:
            keyboard = get_main_user_keyboard()
        await query.message.answer("Вы возвращены в главное меню.", reply_markup=keyboard)

    else:
        came_from_club_id = data.get('came_from_club_id')
        await state.clear()
        if came_from_club_id:
            all_clubs = get_all_clubs_from_cache()
            club_name = next((c['name'] for c in all_clubs if c['id'] == came_from_club_id), "Неизвестный клуб")
            await state.update_data(current_club_id=came_from_club_id, current_club_name=club_name)
            page = 1
            participants, total_records, total_pages = get_participants_by_club(club_id=came_from_club_id, page=page)
            text = f"Клуб: {club_name}\nУчастников: {total_records}\nСтраница {page}/{total_pages}"

            await query.message.edit_text(
                text,
                reply_markup=get_club_participants_keyboard(participants, total_pages, page, came_from_club_id)
            )


# --- Логика просмотра списка участников ---

def get_participants_keyboard(participants: list, total_pages: int, current_page: int, search_query: str = None):
    """Генерирует клавиатуру для списка участников с пагинацией и поиском."""
    builder = InlineKeyboardBuilder()
    # Кнопки с ФИО участников
    for p in participants:
        builder.button(text=p['fio'], callback_data=f"view_participant:{p['id']}")
    builder.adjust(1)

    # Кнопки навигации
    nav_buttons = []
    search_str = search_query if search_query else ""
    if current_page > 1:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"pnp:{current_page - 1}:{search_str}"))
    nav_buttons.append(InlineKeyboardButton(text=f"Стр {current_page}/{total_pages}", callback_data="noop"))
    if current_page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"pnp:{current_page + 1}:{search_str}"))
    builder.row(*nav_buttons)

    # Кнопка поиска и возврата в меню
    builder.row(InlineKeyboardButton(text="🔍 Поиск по ФИО", callback_data="search_participant"))
    builder.row(InlineKeyboardButton(text="⬅️ В главное меню", callback_data="back_to_main_menu"))
    return builder.as_markup()


@user_router.callback_query(F.data == "list_participants")
async def list_participants_handler(query: CallbackQuery, state: FSMContext):
    """Отображает первую страницу списка участников."""
    await state.clear()
    page = 1
    participants, total_records, total_pages = get_participants(page=page)

    text = (f"Список участников: {total_records} записей\n"
            f"Страница {page}/{total_pages}\n\n"
            f"Выберите участника на кнопках ниже.")

    await query.message.edit_text(
        text,
        reply_markup=get_participants_keyboard(participants, total_pages, page)
    )
    await query.answer()


@user_router.callback_query(F.data.startswith("pnp:"))
async def participant_pagination_handler(query: CallbackQuery, state: FSMContext):
    """Обрабатывает переключение страниц в списке участников."""
    try:
        _, page_str, search_query = query.data.split(":", 2)
    except ValueError:
        return
    page = int(page_str)
    search_query = search_query if search_query else None

    participants, total_records, total_pages = get_participants(page=page, search_query=search_query)

    if search_query:
        text = (f"Результаты поиска по '{search_query}': {total_records} найдено\n"
                f"Страница {page}/{total_pages}\n\n"
                f"Выберите участника на кнопках ниже.")
    else:
        text = (f"Список участников: {total_records} записей\n"
                f"Страница {page}/{total_pages}\n\n"
                f"Выберите участника на кнопках ниже.")

    await query.message.edit_text(
        text,
        reply_markup=get_participants_keyboard(participants, total_pages, page, search_query)
    )
    await query.answer()


@user_router.callback_query(F.data == "search_participant")
async def search_participant_prompt(query: CallbackQuery, state: FSMContext):
    """Запрашивает у пользователя ФИО для поиска."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="list_participants"))
    await query.message.edit_text(
        "Введите ФИО для поиска:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(RegistrationStates.awaiting_search_query)
    await query.answer()


@user_router.message(RegistrationStates.awaiting_search_query)
async def process_participant_search(message: Message, state: FSMContext):
    """Обрабатывает введенный поисковый запрос и показывает результаты."""
    await state.clear()
    search_query = message.text
    page = 1

    participants, total_records, total_pages = get_participants(page=page, search_query=search_query)

    if not participants:
        text = f"По вашему запросу '{search_query}' ничего не найдено."
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="⬅️ К списку участников", callback_data="list_participants"))
        await message.answer(text, reply_markup=keyboard.as_markup())
        return

    text = (f"Результаты поиска по '{search_query}': {total_records} найдено\n"
            f"Страница {page}/{total_pages}\n\n"
            f"Выберите участника на кнопках ниже.")

    await message.answer(
        text,
        reply_markup=get_participants_keyboard(participants, total_pages, page, search_query)
    )

async def _show_participant_card(query: CallbackQuery, participant_id: int, state: FSMContext):
    participant_data = get_participant_by_id(participant_id)

    if not participant_data:
        await query.answer("Участник не найден.", show_alert=True)
        return

    summary_parts = ["────────────"]
    if fio := participant_data.get('fio'): summary_parts.append(f"• ФИО: {fio}")
    if gender := participant_data.get('gender'): summary_parts.append(f"• Пол: {gender}")
    if dob := participant_data.get('dob'): summary_parts.append(f"• Дата рождения: {dob.strftime('%d.%m.%Y')}")
    if age_category := participant_data.get('age_category_name'): summary_parts.append(f"• Возрастная категория: {age_category}")
    if weight_category := participant_data.get('weight_category_name'): summary_parts.append(f"• Весовая категория: {str(weight_category).replace(' кг', '')}")
    if class_name := participant_data.get('class_name'): summary_parts.append(f"• Категория: {class_name.split(' ')[0]}")
    if rank := participant_data.get('rank_name'): summary_parts.append(f"• Разряд: {rank}")
    if region := participant_data.get('region_name'): summary_parts.append(f"• Регион: {region}")
    if city := participant_data.get('city_name'): summary_parts.append(f"• Город/населённый пункт: {city}")
    if club := participant_data.get('club_name'): summary_parts.append(f"• Клуб: {club}")
    if coach := participant_data.get('coach_name'): summary_parts.append(f"• ФИО тренера: {coach}")
    summary_parts.append("────────────")

    summary_text = "\n".join(summary_parts)
    builder = InlineKeyboardBuilder()

    is_admin_check = IsAdmin()
    if await is_admin_check(query):
        builder.row(
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_participant:{participant_id}"),
            InlineKeyboardButton(text="❌ Удалить", callback_data=f"delete_participant:{participant_id}")
        )

    data = await state.get_data()
    came_from_club_id = data.get('came_from_club_id')

    back_callback = "list_participants"
    back_text = "⬅️ К списку участников"
    if came_from_club_id:
        back_callback = f"view_club:{came_from_club_id}"
        back_text = "⬅️ К участникам клуба"

    builder.row(InlineKeyboardButton(text=back_text, callback_data=back_callback))

    await query.message.edit_text(summary_text, reply_markup=builder.as_markup())

@user_router.callback_query(F.data.startswith("view_participant:"))
async def view_participant_handler(query: CallbackQuery, state: FSMContext):
    """Отображает подробную информацию об участнике."""
    parts = query.data.split(":")
    participant_id = int(parts[1])

    # Проверяем, пришли ли мы из списка клуба, и сохраняем ID в состояние
    if len(parts) > 3 and parts[2] == 'club':
        club_id = int(parts[3])
        await state.update_data(came_from_club_id=club_id)
    else:
        # Убедимся, что в состоянии не осталось старого ID клуба
        await state.update_data(came_from_club_id=None)

    await _show_participant_card(query, participant_id, state)
    await query.answer()

# --- Логика просмотра участников по клубам ---

def get_clubs_list_keyboard(clubs: list, total_pages: int, current_page: int, search_query: str = None):
    """Генерирует клавиатуру для списка клубов."""
    builder = InlineKeyboardBuilder()
    for club in clubs:
        builder.button(text=club['name'], callback_data=f"view_club:{club['id']}")
    builder.adjust(1)
    nav_buttons = []
    search_str = search_query if search_query else ""
    if current_page > 1:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"cpnp:{current_page - 1}:{search_str}"))
    nav_buttons.append(InlineKeyboardButton(text=f"Стр {current_page}/{total_pages}", callback_data="noop"))
    if current_page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"cpnp:{current_page + 1}:{search_str}"))
    builder.row(*nav_buttons)
    builder.row(InlineKeyboardButton(text="🔍 Поиск по названию", callback_data="search_club"))
    builder.row(InlineKeyboardButton(text="⬅️ В главное меню", callback_data="back_to_main_menu"))
    return builder.as_markup()

def get_club_participants_keyboard(participants: list, total_pages: int, current_page: int, club_id: int, search_query: str = None):
    """Генерирует клавиатуру для списка участников клуба."""
    builder = InlineKeyboardBuilder()
    for p in participants:
        builder.button(text=p['fio'], callback_data=f"view_participant:{p['id']}:club:{club_id}")
    builder.adjust(1)
    nav_buttons = []
    search_str = search_query if search_query else ""
    if current_page > 1:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"ppcp:{club_id}:{current_page - 1}:{search_str}"))
    nav_buttons.append(InlineKeyboardButton(text=f"Стр {current_page}/{total_pages}", callback_data="noop"))
    if current_page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"ppcp:{club_id}:{current_page + 1}:{search_str}"))
    builder.row(*nav_buttons)
    builder.row(InlineKeyboardButton(text="🔍 Поиск по ФИО", callback_data=f"search_participant_by_club:{club_id}"))
    builder.row(InlineKeyboardButton(text="⬅️ Все клубы", callback_data="club_participants"))
    return builder.as_markup()

@user_router.callback_query(F.data == "club_participants")
async def list_clubs_handler(query: CallbackQuery, state: FSMContext):
    """Отображает первую страницу списка клубов."""
    await state.clear()
    page = 1
    clubs, total_records, total_pages = get_clubs(page=page)
    text = f"Клубы: {total_records} шт.\nСтраница {page}/{total_pages}"
    await query.message.edit_text(text, reply_markup=get_clubs_list_keyboard(clubs, total_pages, page))
    await query.answer()

@user_router.callback_query(F.data.startswith("cpnp:"))
async def club_pagination_handler(query: CallbackQuery, state: FSMContext):
    """Обрабатывает пагинацию списка клубов."""
    try:
        _, page_str, search_query = query.data.split(":", 2)
    except ValueError: return
    page = int(page_str)
    search_query = search_query if search_query else None
    clubs, total_records, total_pages = get_clubs(page=page, search_query=search_query)
    if search_query:
        text = f"Поиск по клубам '{search_query}': {total_records} найдено\nСтраница {page}/{total_pages}"
    else:
        text = f"Клубы: {total_records} шт.\nСтраница {page}/{total_pages}"
    await query.message.edit_text(text, reply_markup=get_clubs_list_keyboard(clubs, total_pages, page, search_query))
    await query.answer()

@user_router.callback_query(F.data == "search_club")
async def search_club_prompt(query: CallbackQuery, state: FSMContext):
    """Запрашивает название клуба для поиска."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="club_participants"))
    await query.message.edit_text(
        "Введите название клуба для поиска:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(RegistrationStates.awaiting_club_search_query)
    await query.answer()

@user_router.message(RegistrationStates.awaiting_club_search_query)
async def process_club_search(message: Message, state: FSMContext):
    """Обрабатывает поиск по клубам."""
    await state.clear()
    search_query = message.text
    page = 1
    clubs, total_records, total_pages = get_clubs(page=page, search_query=search_query)
    if not clubs:
        keyboard = InlineKeyboardBuilder().row(InlineKeyboardButton(text="⬅️ К списку клубов", callback_data="club_participants")).as_markup()
        await message.answer(f"По запросу '{search_query}' ничего не найдено.", reply_markup=keyboard)
        return
    text = f"Поиск по клубам '{search_query}': {total_records} найдено\nСтраница {page}/{total_pages}"
    await message.answer(text, reply_markup=get_clubs_list_keyboard(clubs, total_pages, page, search_query))

@user_router.callback_query(F.data.startswith("view_club:"))
async def list_participants_by_club_handler(query: CallbackQuery, state: FSMContext):
    """Отображает список участников для выбранного клуба."""
    club_id = int(query.data.split(":")[1])
    all_clubs = get_all_clubs_from_cache()
    club_name = next((c['name'] for c in all_clubs if c['id'] == club_id), "Неизвестный клуб")
    await state.update_data(current_club_id=club_id, current_club_name=club_name)
    page = 1
    participants, total_records, total_pages = get_participants_by_club(club_id=club_id, page=page)
    text = f"Клуб: {club_name}\nУчастников: {total_records}\nСтраница {page}/{total_pages}"
    await query.message.edit_text(text, reply_markup=get_club_participants_keyboard(participants, total_pages, page, club_id))
    await query.answer()

@user_router.callback_query(F.data.startswith("ppcp:"))
async def participant_by_club_pagination_handler(query: CallbackQuery, state: FSMContext):
    """Обрабатывает пагинацию списка участников клуба."""
    try:
        _, club_id_str, page_str, search_query = query.data.split(":", 3)
    except ValueError: return
    club_id = int(club_id_str)
    page = int(page_str)
    search_query = search_query if search_query else None
    data = await state.get_data()
    club_name = data.get("current_club_name", "Неизвестный клуб")
    participants, total_records, total_pages = get_participants_by_club(club_id, page, search_query)
    if search_query:
        text = f"Клуб: {club_name}\nПоиск по '{search_query}': {total_records} найдено\nСтраница {page}/{total_pages}"
    else:
        text = f"Клуб: {club_name}\nУчастников: {total_records}\nСтраница {page}/{total_pages}"
    await query.message.edit_text(text, reply_markup=get_club_participants_keyboard(participants, total_pages, page, club_id, search_query))
    await query.answer()

@user_router.callback_query(F.data.startswith("search_participant_by_club:"))
async def search_participant_by_club_prompt(query: CallbackQuery, state: FSMContext):
    """Запрашивает ФИО для поиска в клубе."""
    club_id = int(query.data.split(":")[1])
    await state.update_data(search_in_club_id=club_id)
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data=f"view_club:{club_id}"))
    await query.message.edit_text(
        "Введите ФИО для поиска в этом клубе:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(RegistrationStates.awaiting_participant_search_by_club_query)
    await query.answer()

@user_router.message(RegistrationStates.awaiting_participant_search_by_club_query)
async def process_participant_search_by_club(message: Message, state: FSMContext):
    """Обрабатывает поиск участников в конкретном клубе."""
    data = await state.get_data()
    club_id = data.get("search_in_club_id")
    club_name = data.get("current_club_name", "Неизвестный клуб")
    search_query = message.text
    await state.clear()
    await state.update_data(current_club_id=club_id, current_club_name=club_name)
    page = 1
    participants, total_records, total_pages = get_participants_by_club(club_id, page, search_query)
    if not participants:
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="⬅️ К участникам клуба", callback_data=f"view_club:{club_id}"))
        await message.answer(f"В клубе '{club_name}' по запросу '{search_query}' ничего не найдено.", reply_markup=builder.as_markup())
        return
    text = f"Клуб: {club_name}\nПоиск по '{search_query}': {total_records} найдено\nСтраница {page}/{total_pages}"
    await message.answer(text, reply_markup=get_club_participants_keyboard(participants, total_pages, page, club_id, search_query))

@user_router.callback_query(F.data == "back_to_main_menu")
async def back_to_main_menu_handler(query: CallbackQuery, state: FSMContext):
    """Возвращает пользователя в главное меню."""
    await state.clear()
    is_admin_check = IsAdmin()
    if await is_admin_check(query):
        keyboard = get_main_admin_keyboard()
        text = "Вы в главном меню администратора."
    else:
        keyboard = get_main_user_keyboard()
        text = "Вы в главном меню."
    
    # Проверяем, есть ли текст в сообщении (edit_text работает только для текстовых сообщений)
    try:
        if query.message.text:
            # Текстовое сообщение - можно изменить
            await query.message.edit_text(text, reply_markup=keyboard)
        else:
            # Сообщение с фото или другим медиа - удаляем и отправляем новое
            await query.message.delete()
            await query.message.answer(text, reply_markup=keyboard)
    except TelegramBadRequest:
        # Если не удалось изменить (например, сообщение уже удалено), отправляем новое
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.answer(text, reply_markup=keyboard)
    except Exception:
        # Любая другая ошибка - отправляем новое сообщение
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.answer(text, reply_markup=keyboard)


@user_router.callback_query(F.data == "preliminary_list")
async def preliminary_list_handler(query: CallbackQuery):
    """
    Формирует и отправляет предварительный список участников в виде Excel-файла.
    """
    await query.message.edit_text("Пожалуйста, подождите, генерируется файл...")

    participants = get_all_participants_for_report()

    temp_dir = "temp_files"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    # Формируем имя файла с текущей датой
    current_date = datetime.now().strftime("%d.%m.%Y")
    filename = f"Предварительный список {current_date}.xlsx"
    file_path = os.path.join(temp_dir, filename)

    generate_preliminary_list_excel(participants, file_path)

    await query.message.answer_document(
        FSInputFile(file_path),
        caption="Предварительный список участников."
    )
    await query.message.delete()

    try:
        os.remove(file_path)
    except OSError as e:
        print(f"Ошибка при удалении временного файла: {e}")


# --- Логика генерации турнирной сетки ---

# @user_router.callback_query(F.data == "tournament_lists")
# async def tournament_lists_start(query: CallbackQuery, state: FSMContext):
#     """Шаг 1: Запрос возрастной категории."""
#     try:
#         await query.message.edit_text(
#             "Выберите возрастную категорию для генерации сетки:",
#             reply_markup=get_bracket_keyboard('age', {})
#         )
#     except TelegramBadRequest:
#         # Ошибка возникает, если пытаться отредактировать сообщение с документом
#         await query.message.delete()
#         await query.message.answer(
#             "Выберите возрастную категорию для генерации сетки:",
#             reply_markup=get_bracket_keyboard('age', {})
#         )
#
#     await state.set_state(RegistrationStates.awaiting_bracket_age_category)
#     await query.answer()
#
#
# @user_router.callback_query(F.data.startswith("bracket_age_cat:"), StateFilter(RegistrationStates.awaiting_bracket_age_category, RegistrationStates.awaiting_bracket_weight_category, RegistrationStates.awaiting_bracket_class))
# async def tournament_lists_age_selected(query: CallbackQuery, state: FSMContext):
#     """Шаг 2: Запрос весовой категории."""
#     age_cat_id = int(query.data.split(":")[1])
#     await state.update_data(bracket_age_id=age_cat_id)
#     data = await state.get_data()
#
#     try:
#         await query.message.edit_text(
#             "Теперь выберите весовую категорию:",
#             reply_markup=get_bracket_keyboard('weight', data)
#         )
#     except TelegramBadRequest:
#         # Эта ошибка возникает при попытке отредактировать сообщение с документом (когда жмем "назад" после генерации)
#         await query.message.delete()
#         await query.message.answer(
#             "Теперь выберите весовую категорию:",
#             reply_markup=get_bracket_keyboard('weight', data)
#         )
#
#     await state.set_state(RegistrationStates.awaiting_bracket_weight_category)
#     await query.answer()
#
#
# @user_router.callback_query(F.data.startswith("bracket_weight_cat:"),
#                             RegistrationStates.awaiting_bracket_weight_category)
# async def tournament_lists_weight_selected(query: CallbackQuery, state: FSMContext):
#     """Шаг 3: Запрос класса участников."""
#     weight_cat_id = int(query.data.split(":")[1])
#     await state.update_data(bracket_weight_id=weight_cat_id)
#     data = await state.get_data()
#
#     try:
#         await query.message.edit_text(
#             "Теперь выберите класс участников:",
#             reply_markup=get_bracket_keyboard('class', data)
#         )
#     except TelegramBadRequest:
#         await query.message.delete()
#         await query.message.answer(
#             "Теперь выберите класс участников:",
#             reply_markup=get_bracket_keyboard('class', data)
#         )
#
#     await state.set_state(RegistrationStates.awaiting_bracket_class)
#     await query.answer()
#
#
# @user_router.callback_query(F.data.startswith("bracket_class:"),
#                             RegistrationStates.awaiting_bracket_class)
# async def tournament_lists_class_selected_and_generate(query: CallbackQuery, state: FSMContext):
#     """Шаг 4: Генерация и отправка списка участников."""
#     await query.message.edit_text("Пожалуйста, подождите, генерируется список...")
#     data = await state.get_data()
#     age_cat_id = data.get('bracket_age_id')
#     weight_cat_id = data.get('bracket_weight_id')
#     class_id = int(query.data.split(":")[1])
#
#     participants = get_participants_for_bracket(age_cat_id, weight_cat_id, class_id)
#
#     builder = InlineKeyboardBuilder()
#     builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"bracket_weight_cat:{weight_cat_id}"))
#     builder.row(InlineKeyboardButton(text="📋 В главное меню", callback_data="back_to_main_menu"))
#
#     if not participants:
#         await query.message.edit_text(
#             "В этой категории нет зарегистрированных участников.",
#             reply_markup=builder.as_markup()
#         )
#         return
#
#     # "Посев"
#     seeded_list = get_seeded_participants(participants)
#
#     # --- Сбор информации для заголовка ---
#     age_cat_obj = next((c for c in get_age_categories_from_cache() if c['id'] == age_cat_id), None)
#     weight_cat_obj = next((c for c in get_weight_categories_from_cache(age_cat_id) if c['id'] == weight_cat_id), None)
#     class_obj = next((c for c in get_classes_from_cache() if c['id'] == class_id), None)
#
#     header_parts = []
#     if age_cat_obj:
#         header_parts.append(f"{age_cat_obj['name']} ({age_cat_obj['gender']})")
#     if weight_cat_obj:
#         header_parts.append(f"{weight_cat_obj['name']}")
#     if class_obj:
#         header_parts.append(f"Класс {class_obj['name'].split(' ')[0]}")
#
#     header_text = ", ".join(header_parts)
#
#     participant_lines = []
#     for i, p in enumerate(seeded_list, 1):
#         if p:
#             participant_lines.append(f"{i}. {p['fio']} ({p.get('city_name', '')}, {p.get('club_name', '')})")
#         else:
#             participant_lines.append(f"{i}. BYE")
#
#     response_text = f"<b>{header_text}</b>\n\n" + "\n".join(participant_lines)
#
#     await query.message.edit_text(
#         response_text,
#         reply_markup=builder.as_markup(),
#         parse_mode="HTML"
#     )
#     await query.answer()

# --- Новые состояния и клавиатуры для постраничного вывода ---

class TournamentListStates(StatesGroup):
    browsing = State()


def get_tournament_list_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопками навигации для списка категорий."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️", callback_data=f"tourn_list_page:{page - 1}"),
        InlineKeyboardButton(text=f"Стр {page}/{total_pages}", callback_data="noop_action"),
        InlineKeyboardButton(text="▶️", callback_data=f"tourn_list_page:{page + 1}")
    )
    builder.row(InlineKeyboardButton(text="⬅️ В главное меню", callback_data="back_to_main_menu"))
    return builder.as_markup()


async def send_tournament_list_page(message: Message, state: FSMContext, page: int):
    """Отправляет страницу с информацией о конкретной категории."""
    data = await state.get_data()
    sorted_categories = data.get("sorted_categories", [])
    total_pages = len(sorted_categories)

    # Нормализация номера страницы
    if page < 1:
        page = total_pages
    if page > total_pages:
        page = 1

    await state.update_data(current_page=page)

    # Получаем данные для текущей страницы
    category_key, participant_list = sorted_categories[page - 1]
    class_name, gender, age_cat_name, weight_name = category_key

    # Формируем текст сообщения
    # --- Изменяем формат заголовка ---
    class_letter = class_name.split(' ')[0]  # Получаем только букву класса
    gender_short = "Муж" if gender == "Мужской" else "Жен"
    header = (f"<b>Грид групп</b>: Категория {html.escape(class_letter)} • {html.escape(gender_short)} • "
              f"возр. кат. {html.escape(age_cat_name)} • вес {html.escape(weight_name)}\n"
              f"Участников: {len(participant_list)}\nСтр {page}/{total_pages}\n────────────")

    response_parts = [header]
    seeded_list = get_seeded_participants(participant_list)

    # --- Изменяем формат вывода участника ---
    for i, p in enumerate(seeded_list, 1):
        if p:
            # Используем html.escape для безопасности
            fio = html.escape(p.get('fio', ''))
            city = html.escape(p.get('city_name', '—'))
            club = html.escape(p.get('club_name', '—'))
            weight_formatted = html.escape(format_weight(p.get('weight', None)))  # Используем format_weight
            age = html.escape(p.get('age_category_name', '—'))
            class_letter_participant = html.escape(
                p.get('class_name', '').split(' ')[0] if p.get('class_name') else '—')

            response_parts.append(
                f"• <b>{fio}</b> ({city} • {club}) — "
                f"вес: {weight_formatted.replace(' кг', '')} | кат.: {age} | Категория: {class_letter_participant}"
            )
        else:
            response_parts.append(f"• BYE")

    final_text = "\n".join(response_parts)
    keyboard = get_tournament_list_keyboard(page, total_pages)

    # Отправляем или редактируем сообщение
    try:
        await message.edit_text(final_text, reply_markup=keyboard)
    except (TelegramBadRequest, AttributeError):
        # Если не получилось отредактировать (например, первое сообщение), отправляем новое
        await message.answer(final_text, reply_markup=keyboard)


@user_router.callback_query(F.data == "tournament_lists")
async def tournament_lists_start(query: CallbackQuery, state: FSMContext):
    """
    Шаг 1: Запрос пола. Показывает выбор пола перед выбором возрастной категории.
    """
    try:
        await query.message.edit_text(
            "Выберите пол:",
            reply_markup=get_bracket_keyboard('gender', {})
        )
    except TelegramBadRequest:
        await query.message.delete()
        await query.message.answer(
            "Выберите пол:",
            reply_markup=get_bracket_keyboard('gender', {})
        )

    await state.set_state(RegistrationStates.awaiting_bracket_gender)
    await query.answer()


@user_router.callback_query(F.data.startswith("bracket_gender:"), RegistrationStates.awaiting_bracket_gender)
async def tournament_lists_gender_selected(query: CallbackQuery, state: FSMContext):
    """Шаг 2: Запрос возрастной категории после выбора пола."""
    gender = query.data.split(":")[1]
    await state.update_data(bracket_gender=gender)
    data = await state.get_data()

    try:
        await query.message.edit_text(
            "Выберите возрастную категорию:",
            reply_markup=get_bracket_keyboard('age', data)
        )
    except TelegramBadRequest:
        await query.message.delete()
        await query.message.answer(
            "Выберите возрастную категорию:",
            reply_markup=get_bracket_keyboard('age', data)
        )

    await state.set_state(RegistrationStates.awaiting_bracket_age_category)
    await query.answer()


@user_router.callback_query(F.data.startswith("bracket_age_cat:"), RegistrationStates.awaiting_bracket_age_category)
async def tournament_lists_age_selected(query: CallbackQuery, state: FSMContext):
    """Шаг 3: Запрос класса участников (изменен порядок - сначала класс, потом вес)."""
    age_cat_id = int(query.data.split(":")[1])
    await state.update_data(bracket_age_id=age_cat_id)
    data = await state.get_data()

    try:
        await query.message.edit_text(
            "Теперь выберите класс участников:",
            reply_markup=get_bracket_keyboard('class_first', data)
        )
    except TelegramBadRequest:
        await query.message.delete()
        await query.message.answer(
            "Теперь выберите класс участников:",
            reply_markup=get_bracket_keyboard('class_first', data)
        )

    await state.set_state(RegistrationStates.awaiting_bracket_class)
    await query.answer()


@user_router.callback_query(F.data.startswith("bracket_class_first:"))
async def tournament_lists_class_first_selected(query: CallbackQuery, state: FSMContext):
    """Шаг 4: Запрос весовой категории после выбора класса."""
    class_id = int(query.data.split(":")[1])
    await state.update_data(bracket_class_id=class_id)
    data = await state.get_data()

    try:
        await query.message.edit_text(
            "Теперь выберите весовую категорию:",
            reply_markup=get_bracket_keyboard('weight', data)
        )
    except TelegramBadRequest:
        await query.message.delete()
        await query.message.answer(
            "Теперь выберите весовую категорию:",
            reply_markup=get_bracket_keyboard('weight', data)
        )

    await state.set_state(RegistrationStates.awaiting_bracket_weight_category)
    await query.answer()


@user_router.callback_query(F.data.startswith("bracket_weight_cat:"))
async def tournament_lists_weight_selected(query: CallbackQuery, state: FSMContext):
    """Шаг 5: Генерация списка участников."""
    weight_cat_id = int(query.data.split(":")[1])
    await state.update_data(bracket_weight_id=weight_cat_id)
    data = await state.get_data()
    
    age_cat_id = data.get('bracket_age_id')
    class_id = data.get('bracket_class_id')
    
    if not age_cat_id or not class_id:
        await query.answer("Ошибка: не выбраны возрастная категория или класс.", show_alert=True)
        return
    
    # Генерируем список участников напрямую
    participants = get_participants_for_bracket(age_cat_id, weight_cat_id, class_id)

    builder = InlineKeyboardBuilder()
    # Кнопка "Назад" возвращает к выбору весовой категории для выбранного класса
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back_to_weight_selection:{class_id}"))
    builder.row(InlineKeyboardButton(text="📋 В главное меню", callback_data="back_to_main_menu"))

    if not participants:
        await query.message.edit_text(
            "В этой категории нет зарегистрированных участников.",
            reply_markup=builder.as_markup()
        )
        return

    # Получаем информацию о категории для заголовка
    from db.cache import get_age_categories_from_cache, get_weight_categories_from_cache, get_classes_from_cache
    
    age_cat_obj = next((c for c in get_age_categories_from_cache() if c['id'] == age_cat_id), None)
    weight_cat_obj = next((c for c in get_weight_categories_from_cache(age_cat_id) if c['id'] == weight_cat_id), None)
    class_obj = next((c for c in get_classes_from_cache() if c['id'] == class_id), None)

    # Формируем заголовок как на скриншоте
    header_parts = []
    if age_cat_obj and weight_cat_obj and class_obj:
        gender_ru = "Мужской" if age_cat_obj.get('gender') == 'Мужской' else "Женский"
        age_name = age_cat_obj['name']
        # В кэше вес уже отформатирован как строка в поле 'name'
        weight_name = weight_cat_obj['name'].replace(' кг', '')
        class_letter = class_obj['name'].split(' ')[0]
        header_parts.append(f"{age_name} ({gender_ru}), {weight_name} кг, Класс {class_letter}")

    header_text = ", ".join(header_parts) if header_parts else "Список участников"

    # Формируем список участников в формате как на скриншоте: "1. Имя (Место, Клуб)"
    participant_lines = []
    for i, p in enumerate(participants, 1):
        city_name = p.get('city_name', '').strip()
        club_name = p.get('club_name', '').strip()
        location_info = f"{city_name}, {club_name}" if city_name and club_name else (city_name or club_name or "")
        participant_lines.append(f"{i}. {p['fio']} ({location_info})" if location_info else f"{i}. {p['fio']}")

    response_text = f"{header_text}\n\n" + "\n".join(participant_lines)

    await query.message.edit_text(
        response_text,
        reply_markup=builder.as_markup(),
        parse_mode=None
    )
    await query.answer()


@user_router.callback_query(F.data == "bracket_back_to_gender")
async def bracket_back_to_gender(query: CallbackQuery, state: FSMContext):
    """Возврат к выбору пола."""
    await state.update_data(bracket_gender=None)
    try:
        await query.message.edit_text(
            "Выберите пол:",
            reply_markup=get_bracket_keyboard('gender', {})
        )
    except TelegramBadRequest:
        await query.message.delete()
        await query.message.answer(
            "Выберите пол:",
            reply_markup=get_bracket_keyboard('gender', {})
        )
    await state.set_state(RegistrationStates.awaiting_bracket_gender)
    await query.answer()


@user_router.callback_query(F.data == "bracket_back_to_age")
async def bracket_back_to_age(query: CallbackQuery, state: FSMContext):
    """Возврат к выбору возрастной категории."""
    data = await state.get_data()
    try:
        await query.message.edit_text(
            "Выберите возрастную категорию:",
            reply_markup=get_bracket_keyboard('age', data)
        )
    except TelegramBadRequest:
        await query.message.delete()
        await query.message.answer(
            "Выберите возрастную категорию:",
            reply_markup=get_bracket_keyboard('age', data)
        )
    await state.set_state(RegistrationStates.awaiting_bracket_age_category)
    await query.answer()


@user_router.callback_query(F.data.startswith("back_to_weight_selection:"))
async def back_to_weight_selection(query: CallbackQuery, state: FSMContext):
    """Возврат к выбору весовой категории с сохранением выбранного класса."""
    class_id = int(query.data.split(":")[1])
    await state.update_data(bracket_class_id=class_id)
    data = await state.get_data()

    try:
        await query.message.edit_text(
            "Выберите весовую категорию:",
            reply_markup=get_bracket_keyboard('weight', data)
        )
    except TelegramBadRequest:
        await query.message.delete()
        await query.message.answer(
            "Выберите весовую категорию:",
            reply_markup=get_bracket_keyboard('weight', data)
        )

    await state.set_state(RegistrationStates.awaiting_bracket_weight_category)
    await query.answer()


@user_router.callback_query(F.data.startswith("bracket_class:"),
                            RegistrationStates.awaiting_bracket_class)
async def tournament_lists_class_selected_and_generate(query: CallbackQuery, state: FSMContext):
    """Старый обработчик для обратной совместимости (если используется где-то еще)."""
    await query.message.edit_text("Пожалуйста, подождите, генерируется список...")
    data = await state.get_data()
    age_cat_id = data.get('bracket_age_id')
    weight_cat_id = data.get('bracket_weight_id')
    class_id = int(query.data.split(":")[1])

    participants = get_participants_for_bracket(age_cat_id, weight_cat_id, class_id)

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"bracket_weight_cat:{weight_cat_id}"))
    builder.row(InlineKeyboardButton(text="📋 В главное меню", callback_data="back_to_main_menu"))

    if not participants:
        await query.message.edit_text(
            "В этой категории нет зарегистрированных участников.",
            reply_markup=builder.as_markup()
        )
        return

    # Получаем информацию о категории для заголовка
    from db.cache import get_age_categories_from_cache, get_weight_categories_from_cache, get_classes_from_cache
    
    age_cat_obj = next((c for c in get_age_categories_from_cache() if c['id'] == age_cat_id), None)
    weight_cat_obj = next((c for c in get_weight_categories_from_cache(age_cat_id) if c['id'] == weight_cat_id), None)
    class_obj = next((c for c in get_classes_from_cache() if c['id'] == class_id), None)

    # Формируем заголовок как на скриншоте
    header_parts = []
    if age_cat_obj and weight_cat_obj and class_obj:
        gender_ru = "Мужской" if age_cat_obj.get('gender') == 'Мужской' else "Женский"
        age_name = age_cat_obj['name']
        # В кэше вес уже отформатирован как строка в поле 'name'
        weight_name = weight_cat_obj['name'].replace(' кг', '')
        class_letter = class_obj['name'].split(' ')[0]
        header_parts.append(f"{age_name} ({gender_ru}), {weight_name} кг, Класс {class_letter}")

    header_text = ", ".join(header_parts) if header_parts else "Список участников"

    # Формируем список участников в формате как на скриншоте: "1. Имя (Место, Клуб)"
    participant_lines = []
    for i, p in enumerate(participants, 1):
        city_name = p.get('city_name', '').strip()
        club_name = p.get('club_name', '').strip()
        location_info = f"{city_name}, {club_name}" if city_name and club_name else (city_name or club_name or "")
        participant_lines.append(f"{i}. {p['fio']} ({location_info})" if location_info else f"{i}. {p['fio']}")

    response_text = f"{header_text}\n\n" + "\n".join(participant_lines)

    await query.message.edit_text(
        response_text,
        reply_markup=builder.as_markup(),
        parse_mode=None
    )
    await query.answer()