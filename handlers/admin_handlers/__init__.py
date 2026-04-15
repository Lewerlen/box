import asyncio
import os
import uuid
import random
from collections import defaultdict
from datetime import datetime
from handlers.user_handlers import (tournament_lists_start)
from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, FSInputFile, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards import get_main_admin_keyboard, get_approval_keyboard, get_approval_list_keyboard, get_main_user_keyboard
from db.cache import update_cache
from db.database import (
    get_participant_by_id, update_participant_by_id, get_all_participants_for_report,
    delete_participant_by_id, get_participants_for_approval, get_approved_statuses,
    update_approval_status, get_participants,
    save_custom_bracket_order, get_custom_bracket_order, delete_custom_bracket_order
)
from utils.csv_importer import process_csv_import
from utils.excel_generator import generate_protocol_excel, generate_preliminary_list_excel, generate_weigh_in_list_excel, generate_all_brackets_excel, generate_pairs_list_excel
from utils.formatters import format_weight
from utils.draw_bracket import get_seeded_participants, draw_bracket_image
import html
from aiogram.filters.callback_data import CallbackData
from typing import List, Dict, Tuple
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from handlers.user_handlers import (IsAdmin, RegistrationStates,
                                    process_class, process_dob, process_fio, process_age_category,
                                    process_rank, process_weight_category,
                                    skip_rank_handler, start_registration,
                                    list_participants_handler, participant_pagination_handler,
                                    search_participant_prompt, process_participant_search,
                                    view_participant_handler, back_to_main_menu_handler,
                                    show_edit_menu, get_registration_keyboard,
                                    list_clubs_handler, club_pagination_handler,
                                    search_club_prompt, process_club_search,
                                    list_participants_by_club_handler, participant_by_club_pagination_handler,
                                    search_participant_by_club_prompt, process_participant_search_by_club,
                                    _show_participant_card
                                    )
# ======================== константы и утилиты для /grid =========================
AGE_ALLOWED = ["8-9", "10-11", "12-13", "14-15", "16-17", "старше 18"]
GENDER_ORDER = {"Женский": 0, "Мужской": 1}

def norm_age(v: str) -> str:
    s = (v or "").strip().lower().replace("ё", "е")
    mapping = {
        "10-11":"10-11","10–11":"10-11",
        "12-13":"12-13","12–13":"12-13",
        "14-15":"14-15","14–15":"14-15",
        "16-17":"16-17","16–17":"16-17",
        "18 и старше":"старше 18","18 и старше.":"старше 18","18+":"старше 18","взрослые":"старше 18",
    }
    return mapping.get(s, v or "")

def _ensure_age_order_map() -> Dict[str, int]:
    return {norm_age(a): i for i, a in enumerate(AGE_ALLOWED)}

def _weight_num(w: str) -> float:
    """
    Преобразует строку с весом в число для сортировки.
    В случае ошибки или отсутствия значения возвращает очень большое число.
    """
    if not w or w == "N/A":
        return 1e9  # Очень большое число, чтобы участники без веса были в конце
    try:
        # Убираем лишние символы и пробуем преобразовать в число
        return float(w.replace('+', '').replace(' кг', '').strip())
    except (ValueError, TypeError):
        return 1e9 # Возвращаем большое число и в случае других ошибок

# ======================== CallbackData для /grid =========================
class GridAllCb(CallbackData, prefix="ga"):
    a: str
    p: int

class GridUserCb(CallbackData, prefix="gus"):
    i: int
    p: int
    src: str = "grid"

# --- Создание роутера для административных хендлеров ---
admin_router = Router()
admin_router.message.filter(IsAdmin())
admin_router.callback_query.filter(IsAdmin())



# --- Обработчики команд ---

@admin_router.message(CommandStart())
async def cmd_start_admin(message: Message):
    """Обработчик команды /start для администратора."""
    user_name = message.from_user.first_name
    await message.answer(
        f"Добро пожаловать, администратор {user_name}!",
        reply_markup=get_main_admin_keyboard()
    )


@admin_router.message(Command("admin"))
async def cmd_admin_panel(message: Message):
    """Обработчик команды /admin для вызова панели администратора."""
    user_name = message.from_user.first_name
    await message.answer(
        f"Добро пожаловать, администратор {user_name}!",
        reply_markup=get_main_admin_keyboard()
    )


@admin_router.callback_query(F.data == "weigh_in_list")
async def weigh_in_list_handler(query: CallbackQuery):
    """
    Формирует и отправляет список для взвешивания в виде Excel-файла.
    """
    await query.message.edit_text("Пожалуйста, подождите, генерируется файл...")

    participants = get_all_participants_for_report()

    temp_dir = "temp_files"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    # Формируем имя файла с текущей датой
    current_date = datetime.now().strftime("%d.%m.%Y")
    filename = f"Список для взвешивания {current_date}.xlsx"
    file_path = os.path.join(temp_dir, filename)

    generate_weigh_in_list_excel(participants, file_path)

    await query.message.answer_document(
        FSInputFile(file_path),
        caption="Список участников для взвешивания."
    )
    await query.message.delete()

    try:
        os.remove(file_path)
    except OSError as e:
        print(f"Ошибка при удалении временного файла: {e}")


@admin_router.message(Command("start_approve_grid"))
async def cmd_start_approve_grid(message: Message):
    """Заглушка для команды подготовки утверждения таблиц."""
    await message.answer("Заглушка: команда для подготовки утверждения таблиц.")


@admin_router.message(Command("approve_grid"))
async def cmd_approve_grid(message: Message):
    """Заглушка для команды перехода к утверждению таблиц."""
    await message.answer("Заглушка: команда для перехода к утверждению таблиц.")


def _build_groups_abc() -> List[Tuple[Tuple[str, int, int, float, str, str, str], List[int]]]:
    """Группирует участников по Дисциплине (A, B, C), полу, возрасту и весу."""
    age_map = _ensure_age_order_map()
    all_participants = get_all_participants_for_report()

    groups: Dict[str, Dict[Tuple, List[int]]] = {"А (Опытный)": {}, "В (Новичок)": {}, "С (Дебютант)": {}}

    for i, r in enumerate(all_participants):
        cl = r.get("class_name")
        if not cl or cl not in groups:
            continue

        gen = r.get("gender")
        age = norm_age(r.get("age_category_name", ""))
        w_str = format_weight(r.get("weight"))
        w = _weight_num(w_str)


        key_common = (
            GENDER_ORDER.get(gen, 99),
            age_map.get(age, 99),
            w,
            gen or "—",
            age or "—",
            w_str or "—"
        )

        groups[cl].setdefault(key_common, []).append(i)

    ordered: List[Tuple[Tuple[str, ...], List[int]]] = []

    for class_name in sorted(groups.keys()):
        class_groups = groups[class_name]
        for k in sorted(class_groups.keys()):
            idxs = class_groups[k]
            # Внутри группы сортируем по ФИО
            idxs.sort(key=lambda j: (
                all_participants[j].get('fio').lower()
            ))
            ordered.append(((class_name,) + k, idxs))

    return ordered

def _groups_page_meta(page: int) -> Tuple[List[int], int, int, int, Tuple[str,int,int,float,str,str,str]]:
    groups = _build_groups_abc()
    n_groups = len(groups)
    pmax = max(1, n_groups)
    page = max(1, min(page, pmax))
    key, idxs = groups[page-1] if n_groups else (("A",0,0,0.0,"—","—","—"), [])
    return idxs, n_groups, pmax, page, key

def _grid_header(n_part: int, page: int, pmax: int, key: Tuple[str,int,int,float,str,str,str]) -> str:
    bucket, _, _, _, gen, age, w = key
    return (
        f"<b>Грид групп</b>: Категория {html.escape(bucket)} • {html.escape(gen)} • возр. кат. {html.escape(age)} • вес {html.escape(w)}\n"
        f"Участников: {n_part}\nСтр {page}/{pmax}\n────────────"
    )

def _format_group_text(page: int) -> str:
    idxs, n_groups, pmax, page, key = _groups_page_meta(page)
    all_participants = get_all_participants_for_report()
    lines = [_grid_header(len(idxs), page, pmax, key)]
    for gi in idxs:
        r = all_participants[gi]
        fio  = r.get('fio')
        city = r.get("city_name") or "—"
        club = r.get("club_name") or "—"
        w    = format_weight(r.get("weight"))
        age  = norm_age(r.get("age_category_name") or "—")
        cl   = r.get("class_name") or "—"
        lines.append(
            f"• <b>{html.escape(fio)}</b> ({html.escape(city)} • {html.escape(club)}) — "
            f"вес: {html.escape(w)} | кат.: {html.escape(age)} | категория: {html.escape(cl)}"
        )
    if not idxs:
        lines.append("В группе нет участников.")
    return "\n".join(lines)

def keyboard_grid(page: int) -> InlineKeyboardMarkup:
    idxs, n_groups, pmax, page, _ = _groups_page_meta(page)
    all_participants = get_all_participants_for_report()
    kb_rows: List[List[InlineKeyboardButton]] = []
    for gi in idxs:
        kb_rows.append([InlineKeyboardButton(text=all_participants[gi].get('fio'), callback_data=GridUserCb(i=gi, p=page).pack())])
    kb_rows.append([
        InlineKeyboardButton(text="◀️", callback_data=GridAllCb(a="prev", p=page).pack()),
        InlineKeyboardButton(text=f"Стр {page}/{pmax}", callback_data=GridAllCb(a="noop", p=page).pack()),
        InlineKeyboardButton(text="▶️", callback_data=GridAllCb(a="next", p=page).pack()),
    ])
    return InlineKeyboardMarkup(inline_keyboard=kb_rows)


# Адаптированный обработчик /grid из проекта Test
@admin_router.callback_query(F.data == "pair_list")
async def grid_start(query: CallbackQuery, state: FSMContext):
    """Отображает первую страницу грида групп."""
    participants = get_all_participants_for_report()
    if not participants:
        await query.message.edit_text("Данных нет.")
        return
    page = 1
    await query.message.edit_text(
        _format_group_text(page),
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard_grid(page)
    )
    await state.set_state(RegistrationStates.awaiting_approval) # Устанавливаем состояние
    await query.answer()


@admin_router.callback_query(GridAllCb.filter(), RegistrationStates.awaiting_approval)
async def on_grid_group_pager(call: CallbackQuery, callback_data: GridAllCb, state: FSMContext):
    """Обрабатывает пагинацию по группам в /grid."""
    participants = get_all_participants_for_report()
    if not participants:
        await call.answer("Нет данных.")
        return
    _, n_groups, pmax, p, _ = _groups_page_meta(callback_data.p)
    if callback_data.a == "prev":
        p = p - 1 if p > 1 else pmax
    elif callback_data.a == "next":
        p = p + 1 if p < pmax else 1

    await call.message.edit_text(
        _format_group_text(p),
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard_grid(p)
    )
    await call.answer()


@admin_router.callback_query(GridUserCb.filter(), RegistrationStates.awaiting_approval)
async def on_grid_user(call: CallbackQuery, callback_data: GridUserCb, state: FSMContext):
    """Показывает карточку участника при клике на него в /grid."""
    participants = get_all_participants_for_report()
    gi = callback_data.i
    page = callback_data.p

    if not (0 <= gi < len(participants)):
        await call.answer("Запись не найдена")
        return

    participant_id = participants[gi].get('id')
    if not participant_id:
        # В get_all_participants_for_report нет ID, используем get_participants
        all_p_with_ids = get_participants()
        # Простая сверка по ФИО, может быть неточной при полных тезках
        fio_to_find = participants[gi].get('fio')
        found = next((p for p in all_p_with_ids if p.get('fio') == fio_to_find), None)
        if found:
            participant_id = found.get('id')
        else:
            await call.answer("Не удалось найти ID участника.")
            return

    await _show_participant_card(call, int(participant_id), state)
    # Сохраняем контекст для кнопки "Назад"
    await state.update_data(grid_page=page)


@admin_router.callback_query(F.data == "preliminary_list")
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
# --- Обработчики импорта CSV ---

@admin_router.callback_query(F.data == "import_csv")
async def prompt_for_csv_import(query: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки 'Импорт участников из CSV'.
    Запрашивает у администратора CSV-файл.
    """
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_main_menu"))
    await query.message.edit_text(
        "Пожалуйста, отправьте CSV-файл для импорта данных участников. \n"
        "Убедитесь, что файл соответствует требуемому формату.",
        reply_markup=builder.as_markup()
    )
    await state.set_state(RegistrationStates.awaiting_csv_file)
    await query.answer()


async def run_import_and_notify(
        bot: Bot, file_path: str, tgid_who_added: int, chat_id: int
):
    """
    Вспомогательная функция для запуска импорта в фоне
    и отправки уведомления по завершении.
    """
    stats = await process_csv_import(file_path, tgid_who_added)

    # Формируем отчет
    if stats['errors'] == -1:
        report_message = f"❗️ Произошла критическая ошибка во время обработки файла.\n\n"
        if stats["error_details"]:
            report_message += f"Детали: {stats['error_details'][0]}"
    else:
        report_message = (
            "✅ Импорт завершен!\n\n"
            f"👤 Новых участников: {stats['created']}\n"
            f"🔄 Данные обновлены: {stats['updated']}\n"
            f"❌ Строк с ошибками: {stats['errors']}"
        )
        if stats["error_details"]:
            report_message += "\n\n📋 Примеры ошибок:"
            for detail in stats["error_details"]:
                report_message += f"\n- {detail}"

    await bot.send_message(chat_id, report_message)

    # Очищаем временный файл
    try:
        os.remove(file_path)
    except OSError as e:
        print(f"Ошибка при удалении файла {file_path}: {e}")


@admin_router.message(RegistrationStates.awaiting_csv_file, F.document)
async def handle_csv_import(message: Message, state: FSMContext, bot: Bot):
    """
    Принимает CSV-файл от администратора, скачивает его
    и запускает асинхронную обработку.
    """
    if message.document.mime_type not in ['text/csv', 'application/vnd.ms-excel']:
        await message.answer(
            "Неверный формат файла. Пожалуйста, отправьте файл в формате CSV."
        )
        return

    # Создаем временную папку, если ее нет
    temp_dir = "temp_files"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    # Скачиваем файл
    file_info = await bot.get_file(message.document.file_id)
    file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.csv")
    await bot.download_file(file_info.file_path, destination=file_path)

    await message.answer(
        f"Файл '{message.document.file_name}' получен и поставлен в очередь на обработку. "
        f"Вы будете уведомлены о результате."
    )
    await state.clear()

    # Запускаем обработку в фоновом режиме
    asyncio.create_task(
        run_import_and_notify(
            bot=bot,
            file_path=file_path,
            tgid_who_added=message.from_user.id,
            chat_id=message.chat.id
        )
    )

@admin_router.callback_query(F.data.startswith("edit_participant:"))
async def start_editing_handler(query: CallbackQuery, state: FSMContext):
    """Начинает процесс редактирования участника, загружает данные в FSM."""
    participant_id = int(query.data.split(":")[1])
    participant_data = get_participant_by_id(participant_id)
    if not participant_data:
        await query.answer("Участник не найден.", show_alert=True)
        return

    # Загружаем в FSM все данные участника, чтобы с ними работать
    await state.set_state(RegistrationStates.editing_participant)

    # Преобразуем дату в ISO формат для совместимости
    if dob_date := participant_data.get('dob'):
        participant_data['dob'] = dob_date.isoformat()

    await state.update_data(
        is_editing=True,
        participant_id=participant_id,
        prompt_message_id=query.message.message_id,  # Сохраняем ID сообщения
        **participant_data
    )

    await show_edit_menu(query, state)  # Вызываем общую функцию
    await query.answer()


@admin_router.callback_query(F.data.startswith("edit_field:"), StateFilter(RegistrationStates.editing_participant, RegistrationStates.editing_from_approval))
async def edit_field_handler(query: CallbackQuery, state: FSMContext):
    field_to_edit = query.data.split(":")[1]
    data = await state.get_data()
    current_state = await state.get_state()

    text_input_fields = {
        "fio": (RegistrationStates.awaiting_fio, "Введите новое ФИО:"),
        "dob": (RegistrationStates.awaiting_dob, "Введите новую дату рождения (ДД.ММ.ГГГГ):"),
    }
    keyboard_fields = {
        "gender": (RegistrationStates.awaiting_gender, "Выберите новый пол:", "gender"),
        "age_category_id": (RegistrationStates.awaiting_age_category, "Выберите новую возрастную категорию:", "age_category"),
        "weight_category_id": (RegistrationStates.awaiting_weight_category, "Выберите новую весовую категорию:", "weight_category"),
        "class_id": (RegistrationStates.awaiting_class, "Выберите новую дисциплину:", "class"),
        "rank_name": (RegistrationStates.awaiting_rank, "Выберите новый разряд:", "rank"),
        "region_id": (RegistrationStates.awaiting_region, "Выберите новый регион:", "region"),
        "city_id": (RegistrationStates.awaiting_city, "Выберите новый город:", "city"),
        "club_id": (RegistrationStates.awaiting_club, "Выберите новый клуб:", "club"),
        "coach_id": (RegistrationStates.awaiting_coach, "Выберите нового тренера:", "coach"),
    }

    target_state, prompt_text, keyboard_type = (None, None, None)

    await state.update_data(editing_return_state=current_state)

    if field_to_edit in text_input_fields:
        target_state, prompt_text = text_input_fields[field_to_edit]
        try:
            await query.message.edit_text(prompt_text, reply_markup=None)
        except TelegramBadRequest:
            await query.message.delete()
            new_msg = await query.message.answer(prompt_text, reply_markup=None)
            await state.update_data(prompt_message_id=new_msg.message_id)

    elif field_to_edit in keyboard_fields:
        target_state, prompt_text, keyboard_type = keyboard_fields[field_to_edit]
        keyboard = get_registration_keyboard(keyboard_type, data)
        try:
            await query.message.edit_text(prompt_text, reply_markup=keyboard)
        except TelegramBadRequest:
            await query.message.delete()
            new_msg = await query.message.answer(prompt_text, reply_markup=keyboard)
            await state.update_data(prompt_message_id=new_msg.message_id)

    if target_state:
        await state.set_state(target_state)
    else:
        await query.answer(f"Редактирование этого поля в разработке.", show_alert=True)
        await state.set_state(current_state)

    await query.answer()


@admin_router.callback_query(F.data == "cancel_editing", StateFilter("*"))
async def cancel_editing_handler(query: CallbackQuery, state: FSMContext):
    """Отменяет редактирование и возвращает к просмотру карточки или к утверждению."""
    current_state_str = await state.get_state()
    data = await state.get_data()
    # Обрабатываем только если действительно в режиме редактирования
    if not data.get('is_editing'):
        await query.answer()
        return
    participant_id = data.get('participant_id')
    came_from_club_id = data.get('came_from_club_id') # Получаем ID клуба

    # Проверяем, было ли редактирование из меню утверждения
    if current_state_str == RegistrationStates.editing_from_approval: # <--- НАЧАЛО БЛОКА ДЛЯ ВОЗВРАТА К УТВЕРЖДЕНИЮ
        approval_index = data.get('return_to_approval_index')
        await state.clear() # Очищаем состояние

        # ---- Перезагрузка данных для утверждения ----
        participants_app = get_participants_for_approval()
        grouped_by_category = defaultdict(list)
        for p in participants_app:
            class_name_val = p.get('class_name', 'Неизвестный класс')
            # Нормализуем название класса
            from utils.formatters import normalize_class_name
            class_name_val = normalize_class_name(class_name_val)
            gender_val = p.get('gender', 'Неизвестный пол')
            age_cat_name_val = p.get('age_category_name', 'Неизвестный возраст')
            weight_val = format_weight(p.get('weight', None)).replace(' кг', '')
            key = (class_name_val, gender_val, age_cat_name_val, weight_val)
            grouped_by_category[key].append(p)

        approved_statuses_from_db = get_approved_statuses()
        approval_categories = []
        for category_key, participant_list in grouped_by_category.items():
            auto_seeded_list = get_seeded_participants(participant_list)
            custom_order_ids = get_custom_bracket_order(category_key)
            final_seeded_list = auto_seeded_list
            participants_changed_flag = False

            if custom_order_ids:
                current_participant_map = {p['id']: p for p in participant_list if p and 'id' in p}
                original_participant_ids = set(current_participant_map.keys())
                saved_participant_ids_set = set(pid for pid in custom_order_ids if pid is not None)

                if original_participant_ids != saved_participant_ids_set:
                    participants_changed_flag = True
                    delete_custom_bracket_order(category_key)
                    if category_key in approved_statuses_from_db:
                        update_approval_status(category_key, False)
                        approved_statuses_from_db.discard(category_key)
                else:
                    # Состав не изменился, применяем сохраненный порядок
                    # Создаем карту ID -> Участник для быстрого поиска
                    participant_map = {p['id']: p for p in auto_seeded_list if p and 'id' in p}
                    # Восстанавливаем порядок, сохраняя структуру BYE слотов
                    reordered_list = []
                    participant_idx = 0
                    for slot in auto_seeded_list:
                        if slot is None:
                            # Сохраняем BYE слот
                            reordered_list.append(None)
                        else:
                            # Вставляем участника согласно сохраненному порядку
                            if participant_idx < len(custom_order_ids):
                                p_id = custom_order_ids[participant_idx]
                                reordered_list.append(participant_map.get(p_id))
                                participant_idx += 1
                            else:
                                reordered_list.append(None)
                    
                    # Проверяем, что размер сетки совпадает и все участники применены
                    if len(reordered_list) == len(auto_seeded_list) and participant_idx == len(custom_order_ids):
                        final_seeded_list = reordered_list
                    else:
                        participants_changed_flag = True
                        delete_custom_bracket_order(category_key)
                        if category_key in approved_statuses_from_db:
                            update_approval_status(category_key, False)
                            approved_statuses_from_db.discard(category_key)

            approval_categories.append({
                "key": category_key,
                "original_participants": participant_list,
                "participants": final_seeded_list,
                "approved": category_key in approved_statuses_from_db and not participants_changed_flag
            })
        # ---- Конец перезагрузки данных ----

        total_categories = len(approval_categories)

        if approval_index is not None and 0 <= approval_index < total_categories:
            await state.set_state(RegistrationStates.awaiting_approval_page)
            # Восстанавливаем данные в state для страницы утверждения
            await state.update_data(
                approval_categories=approval_categories,
                current_category_index=approval_index,
                total_categories=total_categories,
                swap_from_index=None # Сбрасываем выбор для swap
            )
            await send_approval_page(query, state) # Возвращаемся на страницу утверждения

        else: # Если индекс некорректен
            await query.message.answer("Ошибка возврата к утверждению. Вы в главном меню.",
                                       reply_markup=get_main_admin_keyboard())
            try:
                await query.message.delete()
            except TelegramBadRequest:
                pass

    else:
        # Стандартная логика отмены (возврат к карточке)
        await state.clear() # Очищаем состояние
        if came_from_club_id and participant_id:
            # Временно записываем ID клуба обратно в состояние, чтобы _show_participant_card
            # сформировал правильную кнопку "Назад"
            await state.update_data(came_from_club_id=came_from_club_id)
            await _show_participant_card(query, participant_id, state)
        # Если came_from_club_id нет, значит пришли из общего списка,
        # _show_participant_card сам сделает кнопку "К списку участников"
        elif participant_id:
             await _show_participant_card(query, participant_id, state)
        else:
             # Если participant_id нет (маловероятно), возвращаем в главное меню
             is_admin_check = IsAdmin()
             keyboard = get_main_admin_keyboard() if await is_admin_check(query) else get_main_user_keyboard()
             await query.message.edit_text("Вы в главном меню.", reply_markup=keyboard)

    await query.answer()

@admin_router.callback_query(F.data == "save_edited_participant", StateFilter(RegistrationStates.editing_participant, RegistrationStates.editing_from_approval))
async def save_edited_participant(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    participant_id = data.get('participant_id')
    return_to_approval = await state.get_state() == RegistrationStates.editing_from_approval
    approval_index = data.get('return_to_approval_index')

    saved_successfully = False
    came_from_club_id = data.get('came_from_club_id')

    try:
        new_entities_added = (
                data.get("region_id") is None and data.get("region_name") or
                data.get("city_id") is None and data.get("city_name") or
                data.get("club_id") is None and data.get("club_name") or
                data.get("coach_id") is None and data.get("coach_name")
        )

        update_data = {}
        fields_to_copy = [
            "fio", "gender", "dob", "age_category_id", "weight_category_id",
            "region_id", "city_id", "club_id", "coach_id", "class_id",
        ]
        key_map = {
            "rank_name": "rank_title",
        }

        for key in fields_to_copy:
            if key in data:
                update_data[key] = data[key]
        for old_key, new_key in key_map.items():
            if old_key in data:
                update_data[new_key] = data[old_key]

        final_update_data = update_data

        if not data.get("rank_name"):
            final_update_data["rank_title"] = None
            final_update_data["rank_assigned_on"] = None
            final_update_data["order_number"] = None
        else:
            final_update_data["rank_assigned_on"] = None
            final_update_data["order_number"] = None

        update_participant_by_id(
            participant_id=participant_id,
            participant_data=final_update_data,  # Теперь используется правильный словарь
            tgid_who_updated=query.from_user.id
        )

        if new_entities_added:
            update_cache()

        await query.answer("✅ Данные успешно обновлены!", show_alert=True)
        saved_successfully = True

    except Exception as e:
        await query.answer(f"❌ Ошибка при сохранении: {e}", show_alert=True)
        await state.clear()
        try:
            await query.message.edit_text("Произошла ошибка при сохранении. Попробуйте снова.",
                                          reply_markup=get_main_admin_keyboard())
        except TelegramBadRequest:
            await query.message.answer("Произошла ошибка при сохранении. Попробуйте снова.",
                                       reply_markup=get_main_admin_keyboard())
            try:
                await query.message.delete()
            except TelegramBadRequest:
                pass
        return

    if not saved_successfully:
        await state.clear()
        return

    if return_to_approval:
        participants_app = get_participants_for_approval()
        grouped_by_category = defaultdict(list)
        for p in participants_app:
            class_name_val = p.get('class_name', 'Неизвестный класс')
            # Нормализуем название класса
            from utils.formatters import normalize_class_name
            class_name_val = normalize_class_name(class_name_val)
            gender_val = p.get('gender', 'Неизвестный пол')
            age_cat_name_val = p.get('age_category_name', 'Неизвестный возраст')
            weight_val = format_weight(p.get('weight', None)).replace(' кг', '')
            key = (class_name_val, gender_val, age_cat_name_val, weight_val)
            grouped_by_category[key].append(p)

        approved_statuses_from_db = get_approved_statuses()
        approval_categories = []
        for category_key, participant_list in grouped_by_category.items():
            auto_seeded_list = get_seeded_participants(participant_list)
            custom_order_ids = get_custom_bracket_order(category_key)
            final_seeded_list = auto_seeded_list
            participants_changed_flag = False

            if custom_order_ids:
                current_participant_map = {p['id']: p for p in participant_list if p and 'id' in p}
                original_participant_ids = set(current_participant_map.keys())
                saved_participant_ids_set = set(pid for pid in custom_order_ids if pid is not None)

                if original_participant_ids != saved_participant_ids_set:
                    participants_changed_flag = True
                    delete_custom_bracket_order(category_key)
                    if category_key in approved_statuses_from_db:
                        update_approval_status(category_key, False)
                        approved_statuses_from_db.discard(category_key)
                else:
                    # Состав не изменился, применяем сохраненный порядок
                    # Создаем карту ID -> Участник для быстрого поиска
                    participant_map = {p['id']: p for p in auto_seeded_list if p and 'id' in p}
                    # Восстанавливаем порядок, сохраняя структуру BYE слотов
                    reordered_list = []
                    participant_idx = 0
                    for slot in auto_seeded_list:
                        if slot is None:
                            # Сохраняем BYE слот
                            reordered_list.append(None)
                        else:
                            # Вставляем участника согласно сохраненному порядку
                            if participant_idx < len(custom_order_ids):
                                p_id = custom_order_ids[participant_idx]
                                reordered_list.append(participant_map.get(p_id))
                                participant_idx += 1
                            else:
                                reordered_list.append(None)
                    
                    # Проверяем, что размер сетки совпадает и все участники применены
                    if len(reordered_list) == len(auto_seeded_list) and participant_idx == len(custom_order_ids):
                        final_seeded_list = reordered_list
                    else:
                        participants_changed_flag = True
                        delete_custom_bracket_order(category_key)
                        if category_key in approved_statuses_from_db:
                            update_approval_status(category_key, False)
                            approved_statuses_from_db.discard(category_key)

            approval_categories.append({
                "key": category_key,
                "original_participants": participant_list,
                "participants": final_seeded_list,
                "approved": category_key in approved_statuses_from_db and not participants_changed_flag
            })
        total_categories = len(approval_categories)

        if approval_index is not None and 0 <= approval_index < total_categories:
            await state.clear()
            await state.set_state(RegistrationStates.awaiting_approval_page)
            await state.update_data(
                approval_categories=approval_categories,
                current_category_index=approval_index,
                total_categories=total_categories,
                swap_from_index=None
            )
            await send_approval_page(query, state)

        else:
            await state.clear()
            await query.message.answer("Ошибка возврата к утверждению (страница не найдена). Вы в главном меню.",
                                       reply_markup=get_main_admin_keyboard())
            try:
                await query.message.delete()
            except TelegramBadRequest:
                pass

    else:
        await state.clear()
        if came_from_club_id:
            await state.update_data(came_from_club_id=came_from_club_id)
        await _show_participant_card(query, participant_id, state)


@admin_router.callback_query(F.data.startswith("delete_participant:"))
async def delete_participant_prompt(query: CallbackQuery, state: FSMContext):
    """Запрашивает подтверждение на удаление участника."""
    participant_id = int(query.data.split(":")[1])
    participant_data = get_participant_by_id(participant_id)
    if not participant_data:
        await query.answer("Участник не найден.", show_alert=True)
        return

    # Сохраняем came_from_club_id из текущего состояния, если он есть
    data = await state.get_data()
    came_from_club_id = data.get('came_from_club_id')
    await state.update_data(participant_id_to_delete=participant_id, came_from_club_id=came_from_club_id)

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Да, удалить", callback_data=f"confirm_delete:{participant_id}")
    )
    builder.row(
        InlineKeyboardButton(text="Нет, я передумал", callback_data=f"cancel_delete:{participant_id}")
    )

    await query.message.edit_text(
        f"Вы уверены, что хотите удалить участника {participant_data.get('fio')}?",
        reply_markup=builder.as_markup()
    )
    await state.set_state(RegistrationStates.awaiting_delete_confirmation)
    await query.answer()


@admin_router.callback_query(F.data.startswith("confirm_delete:"), RegistrationStates.awaiting_delete_confirmation)
async def confirm_delete_participant(query: CallbackQuery, state: FSMContext):
    """Подтверждает и выполняет удаление участника."""
    participant_id = int(query.data.split(":")[1])
    # Сохраняем came_from_club_id перед очисткой состояния
    data = await state.get_data()
    came_from_club_id = data.get('came_from_club_id')
    
    try:
        delete_participant_by_id(participant_id)
        await query.answer("Участник удален.", show_alert=True)
    except Exception as e:
        await query.message.edit_text(f"Ошибка при удалении: {e}")
        await query.answer("Ошибка!", show_alert=True)
        await state.clear()
        return
    
    await state.clear()
    
    # Если пришли из клуба, возвращаемся к списку участников клуба
    if came_from_club_id:
        # Импортируем необходимые функции для показа клуба
        from db.cache import get_all_clubs_from_cache
        from db.database import get_participants_by_club
        from handlers.user_handlers import get_club_participants_keyboard
        
        all_clubs = get_all_clubs_from_cache()
        club_name = next((c['name'] for c in all_clubs if c['id'] == came_from_club_id), "Неизвестный клуб")
        await state.update_data(current_club_id=came_from_club_id, current_club_name=club_name)
        page = 1
        participants, total_records, total_pages = get_participants_by_club(club_id=came_from_club_id, page=page)
        text = f"Клуб: {club_name}\nУчастников: {total_records}\nСтраница {page}/{total_pages}"
        try:
            await query.message.edit_text(
                text,
                reply_markup=get_club_participants_keyboard(participants, total_pages, page, came_from_club_id)
            )
        except TelegramBadRequest:
            # Если не удалось отредактировать сообщение, отправляем новое
            await query.message.answer(
                text,
                reply_markup=get_club_participants_keyboard(participants, total_pages, page, came_from_club_id)
            )
    else:
        # Иначе возвращаемся в главное меню
        try:
            await query.message.edit_text(
                "Вы в главном меню.",
                reply_markup=get_main_admin_keyboard()
            )
        except TelegramBadRequest:
            # Если не удалось отредактировать сообщение, отправляем новое
            await query.message.answer(
                "Вы в главном меню.",
                reply_markup=get_main_admin_keyboard()
            )


@admin_router.callback_query(F.data.startswith("cancel_delete:"), RegistrationStates.awaiting_delete_confirmation)
async def cancel_delete_handler(query: CallbackQuery, state: FSMContext):
    """Отменяет удаление и возвращает к карточке участника."""
    participant_id = int(query.data.split(":")[1])
    # Восстанавливаем данные о том, откуда пришли, если они были
    data = await state.get_data()
    came_from_club_id = data.get('came_from_club_id')
    await state.clear()
    if came_from_club_id:
        await state.update_data(came_from_club_id=came_from_club_id)

    # Просто вызываем хелпер для отображения карточки
    await _show_participant_card(query, participant_id, state)

# --- Регистрация общих обработчиков для админского роутера ---
admin_router.callback_query.register(start_registration, F.data == "add_participant")
admin_router.message.register(process_fio, RegistrationStates.awaiting_fio)
admin_router.message.register(process_dob, RegistrationStates.awaiting_dob)
admin_router.callback_query.register(
    process_age_category,
    RegistrationStates.awaiting_age_category,
    F.data.startswith("age_category:")
)

admin_router.callback_query.register(
    process_weight_category,
    RegistrationStates.awaiting_weight_category,
    F.data.startswith("weight_category:")
)

admin_router.callback_query.register(
    process_class,
    RegistrationStates.awaiting_class,
    F.data.startswith("class:")
)

admin_router.callback_query.register(
    process_rank,
    RegistrationStates.awaiting_rank,
    F.data.startswith("rank:")
)

admin_router.callback_query.register(
    skip_rank_handler,
    RegistrationStates.awaiting_rank,
    F.data == "skip_rank"
)

from handlers.user_handlers import (process_region_selection, process_city_selection,
                                    process_club_selection, process_coach_selection)

admin_router.callback_query.register(
    process_region_selection,
    RegistrationStates.awaiting_region,
    F.data.startswith("region:")
)
admin_router.callback_query.register(
    process_city_selection,
    RegistrationStates.awaiting_city,
    F.data.startswith("city:")
)
admin_router.callback_query.register(
    process_club_selection,
    RegistrationStates.awaiting_club,
    F.data.startswith("club:")
)
admin_router.callback_query.register(
    process_coach_selection,
    RegistrationStates.awaiting_coach,
    F.data.startswith("coach:")
)

# --- Регистрация обработчиков для списка участников ---
admin_router.callback_query.register(list_participants_handler, F.data == "list_participants")
admin_router.callback_query.register(participant_pagination_handler, F.data.startswith("pnp:"))
admin_router.callback_query.register(search_participant_prompt, F.data == "search_participant")
admin_router.message.register(process_participant_search, RegistrationStates.awaiting_search_query)
admin_router.callback_query.register(back_to_main_menu_handler, F.data == "back_to_main_menu")
admin_router.callback_query.register(view_participant_handler, F.data.startswith("view_participant:"))
# --- Регистрация обработчиков для участников по клубам ---
admin_router.callback_query.register(list_clubs_handler, F.data == "club_participants")
admin_router.callback_query.register(club_pagination_handler, F.data.startswith("cpnp:"))
admin_router.callback_query.register(search_club_prompt, F.data == "search_club")
admin_router.message.register(process_club_search, RegistrationStates.awaiting_club_search_query)
admin_router.callback_query.register(list_participants_by_club_handler, F.data.startswith("view_club:"))
admin_router.callback_query.register(participant_by_club_pagination_handler, F.data.startswith("ppcp:"))
admin_router.callback_query.register(search_participant_by_club_prompt, F.data.startswith("search_participant_by_club:"))
admin_router.message.register(process_participant_search_by_club, RegistrationStates.awaiting_participant_search_by_club_query)
# --- Регистрация обработчиков для турнирной сетки ---
# Шаг 1: Нажатие кнопки "Турнирные списки"
admin_router.callback_query.register(
    tournament_lists_start,
    F.data == "tournament_lists"
)

# --- Регистрация обработчиков для удаления ---
admin_router.callback_query.register(delete_participant_prompt, F.data.startswith("delete_participant:"))
admin_router.callback_query.register(confirm_delete_participant, F.data.startswith("confirm_delete:"), RegistrationStates.awaiting_delete_confirmation)
admin_router.callback_query.register(cancel_delete_handler, F.data.startswith("cancel_delete:"), RegistrationStates.awaiting_delete_confirmation)
#  Шаг 2: Выбор возрастной категории (срабатывает из нескольких состояний для кнопки "Назад")
# admin_router.callback_query.register(
#     tournament_lists_age_selected,
#     F.data.startswith("bracket_age_cat:"),
#     StateFilter(RegistrationStates.awaiting_bracket_age_category, RegistrationStates.awaiting_bracket_weight_category, RegistrationStates.awaiting_bracket_class)
# )
#
#  Шаг 3: Выбор весовой категории и переход к выбору класса
# admin_router.callback_query.register(
#     tournament_lists_weight_selected,
#     F.data.startswith("bracket_weight_cat:"),
#     RegistrationStates.awaiting_bracket_weight_category
# )
#
#  Шаг 4: Выбор класса и генерация сетки
# admin_router.callback_query.register(
#     tournament_lists_class_selected_and_generate,
#     F.data.startswith("bracket_class:"),
#     RegistrationStates.awaiting_bracket_class
# )


async def send_approval_page(query: CallbackQuery, state: FSMContext):
    """Отрисовывает и отправляет текущую страницу с полной сеткой для утверждения."""
    data = await state.get_data()
    categories = data.get('approval_categories', [])
    cat_idx = data.get('current_category_index', 0)
    total_categories = data.get('total_categories', 0)

    if not categories or cat_idx >= len(categories):
        await query.message.edit_text("Нет участников для утверждения.", reply_markup=None)
        await state.clear()
        return

    category_data = categories[cat_idx]
    category_key = category_data["key"]
    seeded_participants = category_data["participants"]
    is_approved = category_data["approved"]

    # --- Подготовка информации для заголовка картинки ---
    age_cat_name = category_key[2]
    gender = category_key[1]
    class_name_short = category_key[0].split(' ')[0]
    age_group_text = ""
    if gender == "Мужской":
        if age_cat_name == "старше 18":
            age_group_text = "Муж"
        else:
            age_group_text = f"Муж {age_cat_name} лет"
    else:  # Женский
        if age_cat_name == "старше 18":
            age_group_text = "Жен"
        else:
            age_group_text = f"Жен {age_cat_name} лет"

    age_group_text += f", Категория {class_name_short}"

    header_info = {
        "line1": "Чемпионат и Первенство республики Башкортостан по муайтай",
        "line2": f"Весовая категория {category_key[3]} кг",
        "line3": age_group_text,
        "line4": "31.10 - 03.11.2025"
    }

    # --- Отрисовка и отправка ---
    temp_dir = "temp_files"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    file_path = os.path.join(temp_dir, f"bracket_{uuid.uuid4()}.png")

    draw_bracket_image(seeded_participants, file_path, header_info)

    swap_from_index = data.get('swap_from_index')
    keyboard = get_approval_keyboard(cat_idx + 1, total_categories, is_approved, seeded_participants,
                                     swap_from_index=swap_from_index)
    await query.message.answer_photo(
        FSInputFile(file_path),
        reply_markup=keyboard
    )
    await query.message.delete()
    os.remove(file_path)

@admin_router.callback_query(F.data == "approve_tables")
async def start_approval_process(query: CallbackQuery, state: FSMContext):
    """Начинает процесс утверждения таблиц."""
    await query.message.edit_text("Пожалуйста, подождите, идет подготовка данных...")

    participants = get_participants_for_approval()
    if not participants:
        await query.message.edit_text("Нет участников для утверждения.")
        return

    # 1. Группируем по полной категории
    grouped_by_category = defaultdict(list)
    for p in participants:
        key = (
            p['class_name'],
            p['gender'],
            p['age_category_name'],
            format_weight(p['weight']).replace(' кг', '')
        )
        grouped_by_category[key].append(p)

        # 2. Для каждой категории "сеем" участников и добавляем статус утверждения
    approved_statuses_from_db = get_approved_statuses()  # Получаем статусы из БД
    approval_categories = []
    for category_key, participant_list in grouped_by_category.items():
        # --- Получаем автоматически сгенерированный порядок ---
        auto_seeded_list = get_seeded_participants(participant_list)

        # --- Проверяем наличие пользовательского порядка ---
        custom_order_ids = get_custom_bracket_order(category_key)
        final_seeded_list = auto_seeded_list  # По умолчанию используем автоматический
        participants_changed = False  # Флаг для отслеживания изменений состава

        if custom_order_ids:
            # Пытаемся применить пользовательский порядок
            current_participant_map = {p['id']: p for p in participant_list if p and 'id' in p}
            original_participant_ids = set(current_participant_map.keys())
            saved_participant_ids = set(custom_order_ids)

            # Проверяем, изменился ли состав участников с момента сохранения
            if original_participant_ids != saved_participant_ids:
                participants_changed = True
                # Состав изменился, удаляем старый пользовательский порядок
                delete_custom_bracket_order(category_key)
                # Сбрасываем статус утверждения в БД, если он был
                if category_key in approved_statuses_from_db:
                    update_approval_status(category_key, False)
                    approved_statuses_from_db.remove(category_key)  # Обновляем локальный сет
                print(f"Состав участников изменился для {category_key}. Пользовательский порядок сброшен.")
            else:
                # Состав не изменился, применяем сохраненный порядок
                # Создаем карту ID -> Участник для быстрого поиска
                participant_map = {p['id']: p for p in auto_seeded_list if p and 'id' in p}
                # Восстанавливаем порядок, сохраняя структуру BYE слотов
                reordered_list = []
                participant_idx = 0
                for slot in auto_seeded_list:
                    if slot is None:
                        # Сохраняем BYE слот
                        reordered_list.append(None)
                    else:
                        # Вставляем участника согласно сохраненному порядку
                        if participant_idx < len(custom_order_ids):
                            p_id = custom_order_ids[participant_idx]
                            reordered_list.append(participant_map.get(p_id))
                            participant_idx += 1
                        else:
                            reordered_list.append(None)

                # Проверяем, что размер сетки совпадает
                if len(reordered_list) == len(auto_seeded_list) and participant_idx == len(custom_order_ids):
                    final_seeded_list = reordered_list
                    print(f"Применен пользовательский порядок для {category_key}")
                else:
                    # Если размеры не совпадают (ошибка), сбрасываем кастомный порядок
                    participants_changed = True  # Считаем это изменением состава
                    delete_custom_bracket_order(category_key)
                    if category_key in approved_statuses_from_db:
                        update_approval_status(category_key, False)
                        approved_statuses_from_db.remove(category_key)
                    print(
                        f"Ошибка применения пользовательского порядка (несовпадение размера) для {category_key}. Порядок сброшен.")

        approval_categories.append({
            "key": category_key,
            "original_participants": participant_list,
            "participants": final_seeded_list,
            "approved": category_key in approved_statuses_from_db and not participants_changed
        })

    total_categories = len(approval_categories)

    await state.update_data(
        approval_categories=approval_categories,
        current_category_index=0,
        total_categories=total_categories
    )

    await state.set_state(RegistrationStates.awaiting_approval_page)

    await send_approval_page(query, state)
    await query.answer()


@admin_router.callback_query(F.data.startswith("approve_page:"), RegistrationStates.awaiting_approval_page)
async def approval_pagination_handler(query: CallbackQuery, state: FSMContext):
    """Обрабатывает пагинацию сеток в режиме утверждения."""
    action = query.data.split(":")[1]
    data = await state.get_data()
    total_categories = data.get('total_categories', 0)
    cat_idx = data.get('current_category_index', 0)

    if action == "next":
        if cat_idx + 1 < total_categories:
            cat_idx += 1
        else:
            await query.answer("Это последняя сетка.", show_alert=True)
            return
    elif action == "prev":
        if cat_idx > 0:
            cat_idx -= 1
        else:
            await query.answer("Это первая сетка.", show_alert=True)
            return

    await state.update_data(current_category_index=cat_idx, swap_from_index=None)
    await state.set_state(RegistrationStates.awaiting_approval_page)
    await send_approval_page(query, state)
    await query.answer()


def _format_page_ranges(pages: list[int]) -> str:
    """Компактно форматирует список номеров страниц в строку вида '1-3, 5, 7-8'."""
    if not pages:
        return ""
    pages = sorted([p + 1 for p in pages])
    ranges = []
    start_of_range = pages[0]
    for i in range(1, len(pages)):
        if pages[i] != pages[i - 1] + 1:
            end_of_range = pages[i - 1]
            if start_of_range == end_of_range:
                ranges += [str(start_of_range)]
            else:
                ranges += [f"{start_of_range}-{end_of_range}"]
            start_of_range = pages[i]

    # Обработка последнего диапазона
    end_of_range = pages[-1]
    if start_of_range == end_of_range:
        ranges += [str(start_of_range)]
    else:
        ranges += [f"{start_of_range}-{end_of_range}"]

    return ", ".join(ranges)


# Cловарь для эмодзи-иконок from handlers.user_handlers import (IsAdmin, RegistrationStates,
#                                     process_class, process_dob, process_fio,
#                                     process_rank, process_weight_category,
#                                     skip_rank_handler, start_registration,ов
CLASS_EMOJI = {
    'А': '🅰️',
    'В': '🅱️',
    'С': '🅲'
}


def _age_cat_sort_key(age_cat_str: str):
    """Вспомогательная функция для правильной числовой сортировки возрастных категорий."""
    # "старше 18" -> 18, "8-9" -> 8, "10-11" -> 10
    if 'старше' in age_cat_str:
        return int(age_cat_str.split(' ')[1])
    return int(age_cat_str.split('-')[0])


@admin_router.callback_query(F.data == "approve_show_list", RegistrationStates.awaiting_approval_page)
async def show_approval_list(query: CallbackQuery, state: FSMContext):
    """Показывает список всех сеток для быстрой навигации."""
    data = await state.get_data()
    categories = data.get('approval_categories', [])
    current_index = data.get('current_category_index', 0)

    # 1. Группировка данных
    grouped_pages = {
        "Жен": defaultdict(lambda: defaultdict(list)),
        "Муж": defaultdict(lambda: defaultdict(list))
    }
    gender_map_keys = {"Женский": "Жен", "Мужской": "Муж"}

    for i, cat_data in enumerate(categories):
        class_name, gender, age_cat, _ = cat_data["key"]
        gender_key = gender_map_keys.get(gender)
        if gender_key:
            class_short = class_name.split(' ')[0]
            if class_short in CLASS_EMOJI:
                grouped_pages[gender_key][class_short][age_cat].append(i)

    # 2. Формирование текстового сообщения
    message_text_parts = ["<b>Категория / Возрастная категория / Номер страницы</b>\n"]
    for gender_display in ["Жен", "Муж"]:  # Заменено
        classes = grouped_pages[gender_display]
        if not any(classes.values()):
             continue

        message_text_parts.append(f"<u>{gender_display}</u>")

        # Готовим списки строк для каждого класса
        class_lines = {'А': [], 'В': [], 'С': []}
        # Явно указываем порядок итерации C -> B -> A
        for class_short in ['С', 'В', 'А']:
            if class_short in classes:
                # Сортируем возрастные категории численно
                sorted_age_cats = sorted(classes[class_short].keys(), key=_age_cat_sort_key)
                for age_cat in sorted_age_cats:
                    pages = classes[class_short][age_cat]
                    page_ranges = _format_page_ranges(pages)
                    emoji = CLASS_EMOJI.get(class_short, '')
                    class_lines[class_short].append(f"{emoji} {age_cat} - {page_ranges}")

        # Построчное формирование колонок
        max_rows = max(len(lines) for lines in class_lines.values()) if any(class_lines.values()) else 0
        for i in range(max_rows):
            row_parts = []
            for class_short in ['А', 'В', 'С']:
                # Добавляем элемент из колонки, если он есть, иначе пустую строку для сохранения структуры
                row_parts.append(class_lines[class_short][i] if i < len(class_lines[class_short]) else "")

            # Собираем строку, убирая пустые "колонки" в конце
            final_row = " | ".join(row_parts).rstrip(" |").strip()
            if final_row:
                message_text_parts.append(final_row)

        message_text_parts.append("")  # Пустая строка для отступа

    final_text = "\n".join(message_text_parts)

    await query.message.delete()
    await query.message.answer(
        final_text,
        reply_markup=get_approval_list_keyboard(categories, current_index),
        parse_mode="HTML"
    )
    await state.set_state(RegistrationStates.awaiting_approval_list_selection)
    await query.answer()


@admin_router.callback_query(F.data.startswith("approve_jump_to:"), RegistrationStates.awaiting_approval_list_selection)
async def jump_to_approval_page(query: CallbackQuery, state: FSMContext):
    """Переходит к выбранной странице утверждения."""
    new_index = int(query.data.split(":")[1])
    await state.update_data(current_category_index=new_index, swap_from_index=None)
    await state.set_state(RegistrationStates.awaiting_approval_page)

    # Просто вызываем функцию отрисовки для нового индекса
    await send_approval_page(query, state)
    await query.answer()


@admin_router.callback_query(F.data.startswith("approve_grid_page:"),
                             RegistrationStates.awaiting_approval_list_selection)
async def approval_grid_pagination_handler(query: CallbackQuery, state: FSMContext):
    """Обрабатывает пагинацию в списке сеток для утверждения."""
    grid_page = int(query.data.split(":")[1])

    # Получаем данные из состояния, чтобы перерисовать сообщение
    data = await state.get_data()
    categories = data.get('approval_categories', [])
    current_index = data.get('current_category_index', 0)

    # Текст сообщения остается тем же, меняется только клавиатура
    await query.message.edit_reply_markup(
        reply_markup=get_approval_list_keyboard(categories, current_index, grid_page=grid_page)
    )
    await query.answer()

@admin_router.callback_query(F.data == "approve_confirm", RegistrationStates.awaiting_approval_page)
async def approve_confirm_handler(query: CallbackQuery, state: FSMContext):
    """Обрабатывает утверждение текущей сетки."""
    data = await state.get_data()
    categories = data.get('approval_categories', [])
    cat_idx = data.get('current_category_index', 0)

    if categories and cat_idx < len(categories):
        # Переключаем статус
        is_now_approved = not categories[cat_idx]['approved']
        categories[cat_idx]['approved'] = is_now_approved
        await state.update_data(approval_categories=categories)

        # Сохраняем изменение в БД
        category_key = categories[cat_idx]['key']
        update_approval_status(category_key, is_now_approved)

        # Обновляем текущую страницу, чтобы показать изменение статуса
    await send_approval_page(query, state)
    await query.answer()


@admin_router.callback_query(F.data == "approve_regenerate", RegistrationStates.awaiting_approval_page)
async def approve_regenerate_handler(query: CallbackQuery, state: FSMContext):
    """Перегенерирует сетку для текущей категории в случайном порядке."""
    # Уведомляем пользователя, что процесс начался (без редактирования сообщения)
    await query.answer("Пожалуйста, подождите, идет перегенерация сетки...")

    data = await state.get_data()
    categories = data.get('approval_categories', [])
    cat_idx = data.get('current_category_index', 0)

    if not categories or cat_idx >= len(categories):
        await query.message.edit_text("Ошибка: не удалось найти категорию.")
        await state.clear()
        return

    category_data = categories[cat_idx]
    category_key = category_data["key"]
    original_participants = category_data.get("original_participants") # Берем исходный список

    if not original_participants:
        await query.message.edit_text("Ошибка: не найден исходный список участников.")
        await state.clear() # Сбрасываем состояние при ошибке
        return

    # Перемешиваем исходный список участников случайным образом
    shuffled_participants = list(original_participants) # Создаем копию
    random.shuffle(shuffled_participants)

    # Генерируем новый "посев" на основе перемешанного списка
    new_seeded_list = get_seeded_participants(shuffled_participants)

    # Обновляем данные в состоянии
    categories[cat_idx]['participants'] = new_seeded_list
    categories[cat_idx]['approved'] = False # Сбрасываем статус утверждения
    await state.update_data(approval_categories=categories, swap_from_index=None)

    # Обновляем статус в БД
    update_approval_status(category_key, False)
    # Удаляем сохраненный пользовательский порядок, так как сетка перегенерирована
    delete_custom_bracket_order(category_key)


    # Отправляем обновленную страницу
    await send_approval_page(query, state)

@admin_router.callback_query(F.data == "noop_action")
async def handle_noop_action(query: CallbackQuery):
    """Обработчик для неактивных кнопок, просто подтверждает получение."""
    await query.answer()


@admin_router.callback_query(F.data.startswith("approve_swap:"), StateFilter(RegistrationStates.awaiting_approval_page, RegistrationStates.awaiting_approval_swap_selection))
async def approve_swap_handler(query: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор участников для замены местами."""
    swap_to_index = int(query.data.split(":")[1])
    data = await state.get_data()
    swap_from_index = data.get('swap_from_index')

    if swap_from_index is None:
        # Это первый выбранный участник
        await state.update_data(swap_from_index=swap_to_index)
        await state.set_state(RegistrationStates.awaiting_approval_swap_selection)

        # Обновляем клавиатуру, не перерисовывая картинку
        categories = data.get('approval_categories', [])
        cat_idx = data.get('current_category_index', 0)
        total_categories = data.get('total_categories', 0)
        category_data = categories[cat_idx]
        seeded_participants = category_data["participants"]
        is_approved = category_data["approved"]

        keyboard = get_approval_keyboard(cat_idx + 1, total_categories, is_approved, seeded_participants,
                                     swap_from_index=swap_to_index)

        await query.message.edit_reply_markup(reply_markup=keyboard)
        await query.answer("Участник выбран. Выберите второго для замены.")
    else:
        # Это второй участник, меняем их местами
        if swap_from_index == swap_to_index:
            await query.answer("Вы выбрали одного и того же участника.", show_alert=True)
            return

        categories = data.get('approval_categories', [])
        cat_idx = data.get('current_category_index', 0)

        if categories and cat_idx < len(categories):
            participants_list = categories[cat_idx]['participants']
            # Меняем местами
            p1 = participants_list[swap_from_index]
            p2 = participants_list[swap_to_index]
            participants_list[swap_from_index] = p2
            participants_list[swap_to_index] = p1
            categories[cat_idx]['participants'] = participants_list
            categories[cat_idx]['approved'] = False  # Сбрасываем статус утверждения в state

            # --- Сохраняем новый порядок в БД ---
            category_key = categories[cat_idx]['key']
            # Собираем ID, сохраняя None для BYE
            current_order_ids = [p['id'] if p else None for p in participants_list]
            # Удаляем None перед сохранением в массив INTEGER[]
            current_order_ids_filtered = [pid for pid in current_order_ids if pid is not None]
            save_custom_bracket_order(category_key, current_order_ids_filtered)

            # --- Сбрасываем статус утверждения в БД ---
            update_approval_status(category_key, False)
            # -------------------------------------

            await state.update_data(approval_categories=categories, swap_from_index=None)
            await state.set_state(RegistrationStates.awaiting_approval_page)

            await send_approval_page(query, state)
            await query.answer("Участники поменялись местами.")
        else:
            await query.answer("Произошла ошибка, попробуйте снова.", show_alert=True)
            await state.clear()


@admin_router.callback_query(F.data == "approve_reset_swap", RegistrationStates.awaiting_approval_swap_selection)
async def approve_reset_swap_handler(query: CallbackQuery, state: FSMContext):
    """Сбрасывает выбор участника для замены."""
    await state.update_data(swap_from_index=None)
    await state.set_state(RegistrationStates.awaiting_approval_page)
    await send_approval_page(query, state)
    await query.answer("Выбор сброшен.")

@admin_router.callback_query(F.data.startswith("edit_participant_from_approval:"))
async def edit_participant_from_approval_handler(query: CallbackQuery, state: FSMContext):
    """Начинает редактирование участника из меню утверждения."""
    participant_id = int(query.data.split(":")[1])
    participant_data_db = get_participant_by_id(participant_id)
    if not participant_data_db:
        await query.answer("Участник не найден.", show_alert=True)
        return

    # Запоминаем индекс ТЕКУЩЕЙ СТРАНИЦЫ утверждения
    current_approval_data = await state.get_data()
    approval_index = current_approval_data.get('current_category_index')

    # Не очищаем состояние здесь, а переходим в новое
    await state.set_state(RegistrationStates.editing_from_approval) # Используем новое состояние

    # Преобразуем даты в ISO формат для совместимости FSM
    if dob_date := participant_data_db.get('dob'):
        participant_data_db['dob'] = dob_date.isoformat()
    if rank_date := participant_data_db.get('rank_assigned_on'):
         # Обрабатываем возможное None значение перед форматированием
        if rank_date:
            participant_data_db['rank_assigned_on'] = rank_date.isoformat()
        else:
            participant_data_db['rank_assigned_on'] = None # Явно устанавливаем None


    # Собираем данные для нового состояния
    data_to_save_in_new_state = {
        "is_editing": True,
        "participant_id": participant_id,
        "prompt_message_id": query.message.message_id,
        **participant_data_db,
        # Сохраняем индекс страницы для возврата
        "return_to_approval_index": approval_index
    }

    # Обновляем данные в НОВОМ состоянии
    await state.update_data(**data_to_save_in_new_state)

    await show_edit_menu(query, state)
    await query.answer()

@admin_router.callback_query(F.data == "prepare_approval")  # Убран StateFilter
async def handle_generate_full_bracket_excel(query: CallbackQuery, state: FSMContext):
    """
    Формирует единый Excel-файл со всеми турнирными сетками.
    Использует данные из состояния, если они есть, иначе генерирует с нуля.
    """
    current_state = await state.get_state()  # Запоминаем текущее состояние
    await query.message.edit_text("Пожалуйста, подождите, идет подготовка полного файла с сетками...")

    data = await state.get_data()
    approval_categories = data.get('approval_categories')
    grouped_by_category = {}

    if approval_categories:
        # Используем данные из состояния (с возможными ручными изменениями)
        grouped_by_category = {
            cat['key']: cat['participants'] for cat in approval_categories
        }
    else:
        # Генерируем с нуля, если в состоянии ничего нет
        participants = get_participants_for_approval()
        if not participants:
            await query.message.edit_text("Нет участников для построения сеток.")
            return

        # 1. Группируем
        temp_grouped = defaultdict(list)
        for p in participants:
            key = (
                p['class_name'],
                p['gender'],
                p['age_category_name'],
                format_weight(p['weight']).replace(' кг', '')
            )
            temp_grouped[key].append(p)

        # 2. Сеем и применяем сохраненный кастомный порядок из БД
        for key, participant_list in temp_grouped.items():
            auto_seeded_list = get_seeded_participants(participant_list)
            final_seeded_list = auto_seeded_list  # По умолчанию используем автоматический
            
            # Проверяем наличие пользовательского порядка
            custom_order_ids = get_custom_bracket_order(key)
            if custom_order_ids:
                current_participant_map = {p['id']: p for p in participant_list if p and 'id' in p}
                original_participant_ids = set(current_participant_map.keys())
                saved_participant_ids = set(custom_order_ids)
                
                # Проверяем, изменился ли состав участников с момента сохранения
                if original_participant_ids == saved_participant_ids:
                    # Состав не изменился, применяем сохраненный порядок
                    # Создаем карту ID -> Участник для быстрого поиска
                    participant_map = {p['id']: p for p in auto_seeded_list if p and 'id' in p}
                    # Восстанавливаем порядок, сохраняя структуру BYE слотов
                    reordered_list = []
                    participant_idx = 0
                    for slot in auto_seeded_list:
                        if slot is None:
                            # Сохраняем BYE слот
                            reordered_list.append(None)
                        else:
                            # Вставляем участника согласно сохраненному порядку
                            if participant_idx < len(custom_order_ids):
                                p_id = custom_order_ids[participant_idx]
                                reordered_list.append(participant_map.get(p_id))
                                participant_idx += 1
                            else:
                                reordered_list.append(None)
                    
                    # Проверяем, что размер сетки совпадает и все участники применены
                    if len(reordered_list) == len(auto_seeded_list) and participant_idx == len(custom_order_ids):
                        final_seeded_list = reordered_list
            
            grouped_by_category[key] = final_seeded_list

    # --- Генерация и отправка файла ---
    temp_dir = "temp_files"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    filename = f"Все_сетки_{datetime.now().strftime('%d%m%Y_%H%M')}.xlsx"
    file_path = os.path.join(temp_dir, filename)

    try:
        generate_all_brackets_excel(grouped_by_category, file_path)

        await query.message.answer_document(
            FSInputFile(file_path),
            caption="Турнирные сетки по всем категориям."
        )
        await query.message.delete()

        # Если хендлер был вызван из главного меню (без состояния), возвращаем туда же
        if current_state is None:
            await query.message.answer("Вы в главном меню администратора.", reply_markup=get_main_admin_keyboard())

    except Exception as e:
        await query.message.answer(f"Произошла ошибка при создании файла с сетками: {e}")
        # Если были в главном меню, возвращаемся туда же
        if current_state is None:
            await query.message.answer("Вы в главном меню администратора.", reply_markup=get_main_admin_keyboard())
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError as e:
                print(f"Ошибка при удалении временного файла {file_path}: {e}")

    await query.answer()

@admin_router.callback_query(F.data == "get_pairs_file")
async def generate_pairs_file_handler(query: CallbackQuery, state: FSMContext):
    """
    Формирует и отправляет Excel-файл со списком пар.
    Использует данные из состояния FSM (если они есть), иначе генерирует из БД.
    """
    await query.message.edit_text("Пожалуйста, подождите, идет подготовка файла со списком пар...")

    data = await state.get_data()
    approval_categories = data.get('approval_categories')
    grouped_by_category = {}

    if approval_categories:
        # Используем данные из состояния (с возможными ручными изменениями)
        grouped_by_category = {
            cat['key']: cat['participants'] for cat in approval_categories
        }
    else:
        # Генерируем с нуля, если в состоянии ничего нет
        participants = get_participants_for_approval()
        if not participants:
            await query.message.edit_text("Нет участников для построения пар.")
            return

        temp_grouped = defaultdict(list)
        for p in participants:
            key = (
                p['class_name'], p['gender'], p['age_category_name'],
                format_weight(p['weight']).replace(' кг', '')
            )
            temp_grouped[key].append(p)

        # Применяем сохраненный кастомный порядок из БД
        for key, participant_list in temp_grouped.items():
            auto_seeded_list = get_seeded_participants(participant_list)
            final_seeded_list = auto_seeded_list  # По умолчанию используем автоматический
            
            # Проверяем наличие пользовательского порядка
            custom_order_ids = get_custom_bracket_order(key)
            if custom_order_ids:
                current_participant_map = {p['id']: p for p in participant_list if p and 'id' in p}
                original_participant_ids = set(current_participant_map.keys())
                saved_participant_ids = set(custom_order_ids)
                
                # Проверяем, изменился ли состав участников с момента сохранения
                if original_participant_ids == saved_participant_ids:
                    # Состав не изменился, применяем сохраненный порядок
                    # Создаем карту ID -> Участник для быстрого поиска
                    participant_map = {p['id']: p for p in auto_seeded_list if p and 'id' in p}
                    # Восстанавливаем порядок, сохраняя структуру BYE слотов
                    reordered_list = []
                    participant_idx = 0
                    for slot in auto_seeded_list:
                        if slot is None:
                            # Сохраняем BYE слот
                            reordered_list.append(None)
                        else:
                            # Вставляем участника согласно сохраненному порядку
                            if participant_idx < len(custom_order_ids):
                                p_id = custom_order_ids[participant_idx]
                                reordered_list.append(participant_map.get(p_id))
                                participant_idx += 1
                            else:
                                reordered_list.append(None)
                    
                    # Проверяем, что размер сетки совпадает и все участники применены
                    if len(reordered_list) == len(auto_seeded_list) and participant_idx == len(custom_order_ids):
                        final_seeded_list = reordered_list
            
            grouped_by_category[key] = final_seeded_list

    temp_dir = "temp_files"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    filename = f"Состав_пар_{datetime.now().strftime('%d%m%Y_%H%M')}.xlsx"
    file_path = os.path.join(temp_dir, filename)

    try:
        generate_pairs_list_excel(grouped_by_category, file_path)
        await query.message.answer_document(
            FSInputFile(file_path),
            caption="Файл со списком пар."
        )
        await query.message.delete()
    except Exception as e:
        await query.message.answer(f"Произошла ошибка при создании файла: {e}")
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError as e:
                print(f"Ошибка при удалении временного файла {file_path}: {e}")

    # После отправки файла всегда возвращаем в главное меню админа
    await query.message.answer("Вы в главном меню администратора.", reply_markup=get_main_admin_keyboard())
    await query.answer()


@admin_router.callback_query(F.data == "generate_protocol")
async def generate_protocol_handler(query: CallbackQuery):
    """
    Формирует и отправляет итоговый протокол в виде Excel-файла.
    """
    await query.message.edit_text("Пожалуйста, подождите, генерируется файл протокола...")

    # Используем обновленную функцию для получения всех данных
    participants = get_all_participants_for_report()
    if not participants:
        await query.message.edit_text("Нет участников для формирования протокола.")
        # Возвращаем в главное меню админа
        await query.message.answer("Вы в главном меню администратора.", reply_markup=get_main_admin_keyboard())
        return

    temp_dir = "temp_files"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    # Формируем имя файла
    current_date_str = datetime.now().strftime("%d.%m.%Y")
    filename = f"Итоговый протокол {current_date_str}.xlsx"
    file_path = os.path.join(temp_dir, filename)

    try:
        # Вызываем новую функцию генерации
        generate_protocol_excel(participants, file_path)

        await query.message.answer_document(
            FSInputFile(file_path),
            caption="Итоговый протокол соревнований."
        )
        await query.message.delete() # Удаляем "Пожалуйста, подождите..."

    except Exception as e:
        await query.message.answer(f"Произошла ошибка при создании файла протокола: {e}")
        # В случае ошибки, все равно возвращаем в меню
        await query.message.answer("Вы в главном меню администратора.", reply_markup=get_main_admin_keyboard())
    finally:
        # Удаляем временный файл
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError as e:
                print(f"Ошибка при удалении временного файла протокола: {e}")

    await query.answer()
admin_router.callback_query.register(generate_protocol_handler, F.data == "generate_protocol")
