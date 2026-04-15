import math
from collections import defaultdict
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

def get_main_user_keyboard():
    """Создает и возвращает клавиатуру главного меню пользователя."""
    builder = InlineKeyboardBuilder()
    buttons = [
        ("📝 Список участников", "list_participants"),
        ("➕ Добавить участника", "add_participant"),
        ("🏢 Участники по клубам", "club_participants"),
        ("📊 Турнирные списки", "pair_list"),
        ("📋 Предварительный список", "preliminary_list"),
    ]
    for text, callback_data in buttons:
        builder.button(text=text, callback_data=callback_data)
    builder.adjust(2)
    return builder.as_markup()


def get_main_admin_keyboard():
    """Создает и возвращает клавиатуру главного меню администратора."""
    builder = InlineKeyboardBuilder()
    buttons = [
        ("📝 Список участников", "list_participants"),
        ("➕ Добавить участника", "add_participant"),
        ("🏢 Участники по клубам", "club_participants"),
        ("📊 Турнирные списки", "tournament_lists"),
        ("📋 Предварительный список", "preliminary_list"),
        ("⚖️ Список для взвешивания", "weigh_in_list"),
        ("✅ Утвердить таблицы", "approve_tables"),
        ("⏳ Сетки участников", "prepare_approval"),
        ("👥 Список пар", "get_pairs_file"),
        ("📄 Сформировать протокол", "generate_protocol"),
        ("📥 Импорт участников из CSV", "import_csv"),
    ]
    for text, callback_data in buttons:
        builder.button(text=text, callback_data=callback_data)
    builder.adjust(2)
    return builder.as_markup()

def get_edit_keyboard():
    builder = InlineKeyboardBuilder()
    fields_to_edit = {
        "fio": "ФИО", "gender": "Пол", "dob": "Дата рождения",
        "age_category_id": "Возрастная категория", "weight_category_id": "Весовая категория",
        "class_id": "Категория", "rank_name": "Разряд", "region_id": "Регион",
        "city_id": "Город", "club_id": "Клуб", "coach_id": "Тренер",
    }
    keys_to_show = ["fio", "gender", "dob", "age_category_id", "weight_category_id",
                    "class_id", "rank_name", "region_id", "city_id", "club_id", "coach_id"]

    for key in keys_to_show:
        if key in fields_to_edit:
             builder.button(text=fields_to_edit[key], callback_data=f"edit_field:{key}")

    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="✅ Сохранить и выйти", callback_data="save_edited_participant"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_editing"))
    return builder.as_markup()

def get_approval_list_keyboard(categories: list, current_category_index: int, grid_page: int = 1):
    """Генерирует клавиатуру со списком всех сеток для быстрого перехода с пагинацией."""
    builder = InlineKeyboardBuilder()

    page_size = 48  # 8 рядов по 6 кнопок
    total_grid_pages = math.ceil(len(categories) / page_size) if categories else 1
    start_index = (grid_page - 1) * page_size
    end_index = start_index + page_size

    # 1. Сетка быстрого перехода для текущей страницы
    nav_grid_buttons = []
    if categories:
        for i, cat_data in enumerate(categories[start_index:end_index], start=start_index):
            is_approved = cat_data["approved"]
            status_icon = "✅" if is_approved else "❌"
            nav_grid_buttons.append(
                InlineKeyboardButton(text=f"{i + 1}{status_icon}", callback_data=f"approve_jump_to:{i}")
            )
        builder.row(*nav_grid_buttons)
        builder.adjust(6)

    # 2. Кнопки пагинации для самой сетки
    grid_nav_buttons = []
    if total_grid_pages > 1:
        if grid_page > 1:
            grid_nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"approve_grid_page:{grid_page - 1}"))

        grid_nav_buttons.append(InlineKeyboardButton(text=f"{grid_page}/{total_grid_pages}", callback_data="noop_action"))

        if grid_page < total_grid_pages:
            grid_nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"approve_grid_page:{grid_page + 1}"))

        builder.row(*grid_nav_buttons)

    # 3. Кнопка "Назад"
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад к странице", callback_data=f"approve_jump_to:{current_category_index}")
    )

    return builder.as_markup()


def get_approval_keyboard(current_page: int, total_pages: int, is_approved: bool, participants: list = None,
                          swap_from_index: int = None):
    """Генерирует клавиатуру для интерфейса утверждения сеток."""
    builder = InlineKeyboardBuilder()

    # --- Участники для замены ---
    if participants:
        # Убираем "пустые" места (BYE) из списка для отрисовки кнопок
        active_participants = [p for p in participants if p is not None]

        # Определяем, активна ли функция замены (кликабельны ли кнопки)
        is_swappable = len(active_participants) > 1

        unpaired_participant = None
        participants_to_pair = [] # Инициализируем пустым списком
        if active_participants: # Проверяем, есть ли активные участники
            if len(active_participants) % 2 != 0:
                unpaired_participant = active_participants[-1]
                participants_to_pair = active_participants[:-1]
            else:
                participants_to_pair = active_participants

        # Цикл для обработки пар участников
        for i in range(0, len(participants_to_pair), 2):
            p1 = participants_to_pair[i]
            p2 = participants_to_pair[i + 1]

            # Проверяем наличие 'id' перед использованием .index()
            if not p1 or 'id' not in p1 or not p2 or 'id' not in p2:
                 continue # Пропускаем пару, если данные некорректны

            try:
                p1_idx = participants.index(p1)
                p2_idx = participants.index(p2)
            except ValueError:
                continue # Пропускаем, если участник не найден в исходном списке

            p1_text = p1['fio']
            p2_text = p2['fio']

            # Сокращаем ФИО до "Фамилия И." и добавляем клуб
            p1_text_short = ' '.join(p1_text.split()[:1]) + f" {p1_text.split()[1][0]}." if len(
                p1_text.split()) > 1 else p1_text
            p1_text_short += f" ({p1.get('club_name', 'Без клуба')})"

            p2_text_short = ' '.join(p2_text.split()[:1]) + f" {p2_text.split()[1][0]}." if len(
                p2_text.split()) > 1 else p2_text
            p2_text_short += f" ({p2.get('club_name', 'Без клуба')})"

            if swap_from_index == p1_idx:
                p1_text_short = f"▶️ {p1_text_short}"
            if swap_from_index == p2_idx:
                p2_text_short = f"▶️ {p2_text_short}"

            # Если замена невозможна, кнопка не будет иметь эффекта
            p1_callback = f"approve_swap:{p1_idx}" if is_swappable else "noop_action"
            p2_callback = f"approve_swap:{p2_idx}" if is_swappable else "noop_action"

            builder.row(
                InlineKeyboardButton(text=p1_text_short, callback_data=p1_callback),
                InlineKeyboardButton(text=p2_text_short, callback_data=p2_callback)
            )

        # --- Добавляем кнопку для непарного участника ПОСЛЕ цикла ---
        if unpaired_participant:
            p_text = unpaired_participant['fio']
            p_real_id = unpaired_participant.get('id')
            if p_real_id:
                try:
                    p_idx = participants.index(unpaired_participant)
                except ValueError:
                    p_idx = -1 # Участник не найден в исходном списке (маловероятно)

                p_text_short = ' '.join(p_text.split()[:1]) + f" {p_text.split()[1][0]}." if len(
                    p_text.split()) > 1 else p_text
                p_text_short += f" ({unpaired_participant.get('club_name', 'Без клуба')})"

                if swap_from_index == p_idx:
                    p_text_short = f"▶️ {p_text_short}"

                # Если активных участников всего 1, эта кнопка ведет на редактирование, иначе - на swap (если swappable)
                if len(active_participants) == 1:
                     p_callback = f"edit_participant_from_approval:{p_real_id}"
                elif is_swappable:
                     p_callback = f"approve_swap:{p_idx}"
                else: # Если участников больше 1, но is_swappable == False (все BYE кроме одного?) - делаем noop
                     p_callback = "noop_action"

                builder.row(InlineKeyboardButton(text=p_text_short, callback_data=p_callback))

    # Кнопки действий
    approval_text = "✅ Снять утверждение" if is_approved else "✅ Утвердить"
    builder.row(
        InlineKeyboardButton(text="🔄 Перегенерировать", callback_data="approve_regenerate"),
        InlineKeyboardButton(text=approval_text, callback_data="approve_confirm")
    )

    # Кнопки пагинации
    nav_buttons = []
    if current_page > 1:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data="approve_page:prev"))

    status_icon = "✅" if is_approved else "❌"
    nav_buttons.append(
        InlineKeyboardButton(text=f"{status_icon} {current_page}/{total_pages}", callback_data="approve_show_list"))

    if current_page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data="approve_page:next"))

    if nav_buttons:
        builder.row(*nav_buttons)

    # Кнопка сброса выбора появляется только если кто-то выбран
    if swap_from_index is not None:
        builder.row(InlineKeyboardButton(text="↩️ Сбросить выбор", callback_data="approve_reset_swap"))

    # Кнопка возврата в меню
    builder.row(InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_main_menu"))

    return builder.as_markup()