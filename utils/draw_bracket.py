from PIL import Image, ImageDraw, ImageFont
import math
import os
from collections import defaultdict
from utils.formatters import format_fio_without_patronymic

# Стандартный порядок "посева" для разведения сильнейших участников по сетке
SEED_ORDERS = {
    2: [1, 2],
    4: [1, 4, 3, 2],
    8: [1, 8, 5, 4, 3, 6, 7, 2],
    16: [1, 16, 9, 8, 5, 12, 13, 4, 3, 14, 11, 6, 7, 10, 15, 2],
    32: [1, 32, 17, 16, 9, 24, 25, 8, 5, 28, 21, 12, 13, 20, 29, 4, 3, 30, 19, 14, 11, 22, 27, 6, 7, 26, 23, 10, 15, 18, 31, 2],
}


def get_seeded_participants(participants: list) -> list:
    """
    Принимает список участников и расставляет их в сетку, соблюдая два правила:
    1. Максимально разводит участников из одного клуба.
    2. Формирует структуру сетки (расстановку боев и пропусков) согласно
       схемам из документа "муайтай сетки.docx".
    """
    num_participants = len(participants)
    if not participants:
        return []

    # Шаг 1: "Посев" участников для разведения одноклубников
    # ----------------------------------------------------
    bracket_size = 1
    while bracket_size < num_participants:
        bracket_size *= 2
    if bracket_size == 1: bracket_size = 2

    clubs = defaultdict(list)
    for p in participants:
        clubs[p.get('club_name') or 'Без клуба'].append(p)

    sorted_clubs = sorted(clubs.values(), key=len, reverse=True)
    flat_participants_list = [p for club_list in sorted_clubs for p in club_list]

    seed_map = {seed: None for seed in range(1, num_participants + 1)}
    for i, p in enumerate(flat_participants_list):
        seed_map[i + 1] = p

    # Создаем предварительный "посеянный" список участников
    # Этот список отражает, кто с кем должен был бы играть в идеальной сетке
    # для максимального разведения одноклубников
    pre_seeded_order = []
    seed_order_template = SEED_ORDERS.get(bracket_size, list(range(1, bracket_size + 1)))
    for seed in seed_order_template:
        if seed <= num_participants:
            pre_seeded_order.append(seed_map[seed])

    p = pre_seeded_order  # Теперь 'p' - это отсортированный по посеву список участников

    # Шаг 2: Применение схемы из документа к "посеянному" списку
    # ----------------------------------------------------------
    drawing_order = [None] * bracket_size

    if num_participants == 3:  # Сетка на 4
        drawing_order = [p[0], None, p[1], p[2]]
    elif num_participants == 5:  # Сетка на 8
        drawing_order = [p[0], None, p[1], None, p[2], None, p[3], p[4]]
    elif num_participants == 6:  # Сетка на 8
        drawing_order = [p[0], p[1], p[2], p[3], p[4], None, p[5], None]
    elif num_participants == 7:  # Сетка на 8
        drawing_order = [p[0], None, p[1], p[2], p[3], p[4], p[5], p[6]]
    elif num_participants == 9:  # Сетка на 16
        drawing_order = [p[2], None, p[3], None, p[4], None, p[5], None, p[6], None, p[7], None, p[8], None, p[0], p[1]]
    elif num_participants == 10:  # Сетка на 16
        drawing_order = [p[0], p[1], p[2], p[3], p[4], None, p[5], None, p[6], None, p[7], None, p[8], None, p[9], None]
    elif num_participants == 11:  # Сетка на 16
        drawing_order = [p[0], p[1], p[2], p[3], p[4], p[5], p[6], None, p[7], None, p[8], None, p[9], None, p[10],
                         None]
    elif num_participants == 12:  # Сетка на 16
        drawing_order = [p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], None, p[9], None, p[10], None, p[11],
                         None]
    elif num_participants == 13:  # Сетка на 16
        drawing_order = [p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9], p[10], None, p[11], None, p[12],
                         None]
    elif num_participants == 14:  # Сетка на 16
        drawing_order = [p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9], p[10], p[11], p[12], None, p[13],
                         None]
    else:
        # Для стандартных случаев (2, 4, 8, 16) или не описанных в схеме
        temp_seeded_list = [None] * bracket_size
        participant_idx = 0
        for seed in seed_order_template:
            if seed <= num_participants:
                temp_seeded_list[seed - 1] = p[participant_idx]
                participant_idx += 1

        # Пересобираем в порядке отрисовки
        drawing_order = [temp_seeded_list[s - 1] for s in seed_order_template]

    return drawing_order


def draw_bracket_image(seeded_participants: list, file_path: str, header_info: dict = None):
    """
    Рисует изображение турнирной сетки с заголовком и доп. информацией,
    корректно отображая пропуски раунда (bye) для любого количества участников.
    """
    num_participants = len([p for p in seeded_participants if p is not None])
    bracket_size = len(seeded_participants)
    if bracket_size < 2: return

    num_rounds = int(math.log2(bracket_size))

    # Константы для рисования
    HEADER_HEIGHT = 120
    H_MATCH = 150
    W_ROUND = 300
    W_NAME = 400
    PAD = 30
    LINE_W = 2

    IMG_WIDTH = int(W_NAME + num_rounds * W_ROUND + PAD * 2)
    if IMG_WIDTH < 1200:
        IMG_WIDTH = 1200
    IMG_HEIGHT = int((bracket_size / 2) * H_MATCH + PAD * 2 + HEADER_HEIGHT)

    # --- Загрузка шрифта ---
    font_path = os.path.join("fonts", "DejaVuSans.ttf")
    try:
        font = ImageFont.truetype(font_path, 18)
        small_font = ImageFont.truetype(font_path, 14)
    except IOError:
        print(f"ПРЕДУПРЕЖДЕНИЕ: Шрифт не найден. Кириллица может отображаться некорректно.")
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    img = Image.new('RGB', (IMG_WIDTH, IMG_HEIGHT), 'white')
    draw = ImageDraw.Draw(img)

    # --- Отрисовка заголовка ---
    if header_info:
        y_cursor = PAD
        line1 = header_info.get("line1", "")
        if line1:
            draw.multiline_text((IMG_WIDTH / 2, y_cursor), line1, font=small_font, fill='black', anchor="ma",
                                align="center")
            y_cursor += 45
        draw.text((PAD, y_cursor), header_info.get("line2", ""), font=font, fill='black', anchor="ls")
        draw.text((IMG_WIDTH / 2, y_cursor), header_info.get("line3", ""), font=font, fill='black', anchor="ms")
        draw.text((IMG_WIDTH - PAD, y_cursor), header_info.get("line4", ""), font=font, fill='black', anchor="rs")

    top_offset = PAD + HEADER_HEIGHT

    # --- СПЕЦИАЛЬНЫЙ СЛУЧАЙ ДЛЯ 3 УЧАСТНИКОВ ---
    if num_participants == 3 and bracket_size == 4 and seeded_participants[1] is None:
        # Этот блок сработает только для расстановки [p0, None, p1, p2]
        bye_participant = seeded_participants[0]
        fighter1 = seeded_participants[2]
        fighter2 = seeded_participants[3]

        # --- Рисуем бой в нижней части сетки ---
        y_f1_center = (2 * H_MATCH / 2) + (H_MATCH / 4) + top_offset
        y_f2_center = (3 * H_MATCH / 2) + (H_MATCH / 4) + top_offset

        for p, y_center in [(fighter1, y_f1_center), (fighter2, y_f2_center)]:
            if p:
                name = format_fio_without_patronymic(p['fio'])
                details = f"{p.get('city_name', '')}, {p.get('club_name', '')}".strip(', ').strip()
                draw.text((PAD + 5, y_center - 20), name, font=font, fill='black')
                if details:
                    draw.text((PAD + 5, y_center + 8), details, font=small_font, fill='black')
                draw.line([(PAD, y_center + 25), (PAD + W_NAME, y_center + 25)], fill='black', width=LINE_W)

        # --- Соединительные линии для боя ---
        y_mid_fight = (y_f1_center + 25 + y_f2_center + 25) / 2
        x_start_r1 = PAD + W_NAME
        x_end_r1 = x_start_r1 + W_ROUND
        draw.line([(x_start_r1, y_f1_center + 25), (x_start_r1, y_f2_center + 25)], fill='black', width=LINE_W)
        draw.line([(x_start_r1, y_mid_fight), (x_end_r1, y_mid_fight)], fill='black', width=LINE_W)

        # --- Рисуем участника с "bye" СПЕРЕДИ и ВЫШЕ ---
        y_bye_center = (0 * H_MATCH / 2) + (H_MATCH / 4) + top_offset
        y_bye_line = y_bye_center + 25

        if bye_participant:
            name = format_fio_without_patronymic(bye_participant['fio'])
            details = f"{bye_participant.get('city_name', '')}, {bye_participant.get('club_name', '')}".strip(
                ', ').strip()
            # Рисуем текст в колонке следующего этапа
            draw.text((x_start_r1 + 5, y_bye_center - 20), name, font=font, fill='black')
            if details:
                draw.text((x_start_r1 + 5, y_bye_center + 8), details, font=small_font, fill='black')
            # Просто подчеркиваем имя, без полного бокса
            draw.line([(x_start_r1, y_bye_line), (x_end_r1, y_bye_line)], fill='black', width=LINE_W)

        # --- Финальные соединительные линии ---
        x_start_r2 = PAD + W_NAME + W_ROUND
        x_end_r2 = x_start_r2 + W_ROUND
        y_final_mid = (y_mid_fight + y_bye_line) / 2

        draw.line([(x_start_r2, y_mid_fight), (x_start_r2, y_bye_line)], fill='black', width=LINE_W)
        draw.line([(x_start_r2, y_final_mid), (x_end_r2, y_final_mid)], fill='black', width=LINE_W)

        img.save(file_path)
        return

    # --- СПЕЦИАЛЬНЫЙ СЛУЧАЙ ДЛЯ 5 УЧАСТНИКОВ ---
    elif num_participants == 5 and bracket_size == 8 and \
             seeded_participants[1] is None and seeded_participants[3] is None and seeded_participants[5] is None:
        # Этот блок сработает только для расстановки [p0, None, p1, None, p2, None, p3, p4]
        fighter1 = seeded_participants[6]  # p3
        fighter2 = seeded_participants[7]  # p4
        bye_participants = [seeded_participants[0], seeded_participants[2], seeded_participants[4]]  # p0, p1, p2

        x_start_r1 = PAD + W_NAME
        x_end_r1 = x_start_r1 + W_ROUND
        x_start_r2 = x_end_r1
        x_end_r2 = x_start_r2 + W_ROUND
        x_start_r3 = x_end_r2
        x_end_r3 = x_start_r3 + W_ROUND

        # --- Рисуем бой в нижней части сетки (1-й раунд) ---
        y_f1_center = (6 * H_MATCH / 2) + (H_MATCH / 4) + top_offset
        y_f2_center = (7 * H_MATCH / 2) + (H_MATCH / 4) + top_offset
        y_f1_line = y_f1_center + 25
        y_f2_line = y_f2_center + 25

        for p, y_center in [(fighter1, y_f1_center), (fighter2, y_f2_center)]:
            if p:
                name = format_fio_without_patronymic(p['fio'])
                details = f"{p.get('city_name', '')}, {p.get('club_name', '')}".strip(', ').strip()
                draw.text((PAD + 5, y_center - 20), name, font=font, fill='black')
                if details:
                    draw.text((PAD + 5, y_center + 8), details, font=small_font, fill='black')
                draw.line([(PAD, y_center + 25), (x_start_r1, y_center + 25)], fill='black', width=LINE_W)

        # --- Соединительная линия для боя (победитель выходит во 2-й раунд) ---
        y_winner_fight1 = (y_f1_line + y_f2_line) / 2
        draw.line([(x_start_r1, y_f1_line), (x_start_r1, y_f2_line)], fill='black', width=LINE_W)
        draw.line([(x_start_r1, y_winner_fight1), (x_end_r1, y_winner_fight1)], fill='black', width=LINE_W)

        # --- Рисуем участников с "bye" (они начинают со 2-го раунда) ---
        bye_line_positions = []
        bye_slots = [0, 2, 4]  # Слоты, из которых участники проходят без боя
        for i, p in enumerate(bye_participants):
            slot_index = bye_slots[i]
            # y-координата участника "bye" берется по его исходной позиции в сетке
            y_center = (slot_index * H_MATCH / 2) + (H_MATCH / 4) + top_offset
            y_line = y_center + 25  # Линия для bye проходит там, где была бы линия боксера
            bye_line_positions.append(y_line)
            if p:
                name = format_fio_without_patronymic(p['fio'])
                details = f"{p.get('city_name', '')}, {p.get('club_name', '')}".strip(', ').strip()
                # Рисуем их сразу во второй колонке
                draw.text((x_start_r1 + 5, y_center - 20), name, font=font, fill='black')
                if details:
                    draw.text((x_start_r1 + 5, y_center + 8), details, font=small_font, fill='black')
                # Линия "bye" во второй раунд
                draw.line([(x_start_r1, y_line), (x_end_r1, y_line)], fill='black', width=LINE_W)

        # --- Соединительные линии для 2-го раунда ---
        # Бой bye1 vs bye2
        y_winner_fight2 = (bye_line_positions[0] + bye_line_positions[1]) / 2
        draw.line([(x_start_r2, bye_line_positions[0]), (x_start_r2, bye_line_positions[1])], fill='black',
                  width=LINE_W)
        draw.line([(x_start_r2, y_winner_fight2), (x_end_r2, y_winner_fight2)], fill='black', width=LINE_W)

        # Бой bye3 vs winner(fighter1, fighter2)
        y_winner_fight3 = (bye_line_positions[2] + y_winner_fight1) / 2
        draw.line([(x_start_r2, bye_line_positions[2]), (x_start_r2, y_winner_fight1)], fill='black', width=LINE_W)
        draw.line([(x_start_r2, y_winner_fight3), (x_end_r2, y_winner_fight3)], fill='black', width=LINE_W)

        # --- Финальная соединительная линия (3-й раунд) ---
        y_final_mid = (y_winner_fight2 + y_winner_fight3) / 2
        draw.line([(x_start_r3, y_winner_fight2), (x_start_r3, y_winner_fight3)], fill='black', width=LINE_W)
        draw.line([(x_start_r3, y_final_mid), (x_end_r3, y_final_mid)], fill='black', width=LINE_W)

        img.save(file_path)
        return

    # --- СПЕЦИАЛЬНЫЙ СЛУЧАЙ ДЛЯ 7 УЧАСТНИКОВ ---
    elif num_participants == 7 and bracket_size == 8 and seeded_participants[1] is None:
        # Этот блок сработает для расстановки [p0, None, p1, p2, p3, p4, p5, p6]
        bye_participant = seeded_participants[0]
        fights = [
            (seeded_participants[2], seeded_participants[3]),
            (seeded_participants[4], seeded_participants[5]),
            (seeded_participants[6], seeded_participants[7])
        ]
        fight_slots = [(2, 3), (4, 5), (6, 7)]

        x_start_r1 = PAD + W_NAME
        x_end_r1 = x_start_r1 + W_ROUND
        x_start_r2 = x_end_r1
        x_end_r2 = x_start_r2 + W_ROUND
        x_start_r3 = x_end_r2
        x_end_r3 = x_start_r3 + W_ROUND

        # --- Рисуем участника с "bye" СПЕРЕДИ и ВЫШЕ ---
        y_bye_line = (((0 * H_MATCH / 2) + (H_MATCH / 4) + top_offset + 25) +
                      ((1 * H_MATCH / 2) + (H_MATCH / 4) + top_offset + 25)) / 2
        y_bye_center = y_bye_line - (H_MATCH / 4)  # Центр для текста

        if bye_participant:
            name = format_fio_without_patronymic(bye_participant['fio'])
            details = f"{bye_participant.get('city_name', '')}, {bye_participant.get('club_name', '')}".strip(
                ', ').strip()
            draw.text((x_start_r1 + 5, y_bye_center - 14), name, font=font, fill='black')
            if details:
                draw.text((x_start_r1 + 5, y_bye_center + 14), details, font=small_font, fill='black')
            draw.line([(x_start_r1, y_bye_line), (x_end_r1, y_bye_line)], fill='black', width=LINE_W)

        # --- Рисуем 3 боя в 1-м раунде ---
        r1_winner_lines_y = []
        for i, fight in enumerate(fights):
            fighter1, fighter2 = fight
            slot1, slot2 = fight_slots[i]

            y_f1_center = (slot1 * H_MATCH / 2) + (H_MATCH / 4) + top_offset
            y_f2_center = (slot2 * H_MATCH / 2) + (H_MATCH / 4) + top_offset

            for p, y_center in [(fighter1, y_f1_center), (fighter2, y_f2_center)]:
                if p:
                    name = format_fio_without_patronymic(p['fio'])
                    details = f"{p.get('city_name', '')}, {p.get('club_name', '')}".strip(', ').strip()
                    draw.text((PAD + 5, y_center - 20), name, font=font, fill='black')
                    if details:
                        draw.text((PAD + 5, y_center + 8), details, font=small_font, fill='black')
                    draw.line([(PAD, y_center + 25), (x_start_r1, y_center + 25)], fill='black', width=LINE_W)

            y_mid_fight = (y_f1_center + 25 + y_f2_center + 25) / 2
            r1_winner_lines_y.append(y_mid_fight)
            draw.line([(x_start_r1, y_f1_center + 25), (x_start_r1, y_f2_center + 25)], fill='black', width=LINE_W)
            draw.line([(x_start_r1, y_mid_fight), (x_end_r1, y_mid_fight)], fill='black', width=LINE_W)

        # --- Соединительные линии для 2-го раунда (полуфиналы) ---
        y_winner_fight2_1 = (y_bye_line + r1_winner_lines_y[0]) / 2
        draw.line([(x_start_r2, y_bye_line), (x_start_r2, r1_winner_lines_y[0])], fill='black', width=LINE_W)
        draw.line([(x_start_r2, y_winner_fight2_1), (x_end_r2, y_winner_fight2_1)], fill='black', width=LINE_W)

        y_winner_fight2_2 = (r1_winner_lines_y[1] + r1_winner_lines_y[2]) / 2
        draw.line([(x_start_r2, r1_winner_lines_y[1]), (x_start_r2, r1_winner_lines_y[2])], fill='black', width=LINE_W)
        draw.line([(x_start_r2, y_winner_fight2_2), (x_end_r2, y_winner_fight2_2)], fill='black', width=LINE_W)

        # --- Финальная соединительная линия (3-й раунд) ---
        y_final_mid = (y_winner_fight2_1 + y_winner_fight2_2) / 2
        draw.line([(x_start_r3, y_winner_fight2_1), (x_start_r3, y_winner_fight2_2)], fill='black', width=LINE_W)
        draw.line([(x_start_r3, y_final_mid), (x_end_r3, y_final_mid)], fill='black', width=LINE_W)

        img.save(file_path)
        return

    # --- СПЕЦИАЛЬНЫЙ СЛУЧАЙ ДЛЯ 9 УЧАСТНИКОВ ---
    elif num_participants == 9 and bracket_size == 16:
        # Этот блок сработает для расстановки [p2, None, ..., p8, None, p0, p1]
        fighter1 = seeded_participants[14]
        fighter2 = seeded_participants[15]
        bye_participants = [
            seeded_participants[0], seeded_participants[2], seeded_participants[4],
            seeded_participants[6], seeded_participants[8], seeded_participants[10],
            seeded_participants[12]
        ]

        x_start_r1 = PAD + W_NAME
        x_end_r1 = x_start_r1 + W_ROUND

        # --- Рисуем бой в 1-м раунде (снизу) ---
        y_f1_center = (14 * H_MATCH / 2) + (H_MATCH / 4) + top_offset
        y_f2_center = (15 * H_MATCH / 2) + (H_MATCH / 4) + top_offset

        for p, y_center in [(fighter1, y_f1_center), (fighter2, y_f2_center)]:
            if p:
                name = format_fio_without_patronymic(p['fio'])
                details = f"{p.get('city_name', '')}, {p.get('club_name', '')}".strip(', ').strip()
                draw.text((PAD + 5, y_center - 20), name, font=font, fill='black')
                if details:
                    draw.text((PAD + 5, y_center + 8), details, font=small_font, fill='black')
                draw.line([(PAD, y_center + 25), (x_start_r1, y_center + 25)], fill='black', width=LINE_W)

        # --- Соединительная линия для боя (победитель выходит во 2-й раунд) ---
        y_winner_fight1 = (y_f1_center + 25 + y_f2_center + 25) / 2
        draw.line([(x_start_r1, y_f1_center + 25), (x_start_r1, y_f2_center + 25)], fill='black', width=LINE_W)
        draw.line([(x_start_r1, y_winner_fight1), (x_end_r1, y_winner_fight1)], fill='black', width=LINE_W)

        # --- Рисуем 7 участников с "bye" (они начинают со 2-го раунда) ---
        r2_y_coords = []
        bye_slots = [0, 2, 4, 6, 8, 10, 12]
        for i, p in enumerate(bye_participants):
            slot1, slot2 = bye_slots[i], bye_slots[i] + 1
            y1 = (slot1 * H_MATCH / 2) + (H_MATCH / 4) + top_offset + 25
            y2 = (slot2 * H_MATCH / 2) + (H_MATCH / 4) + top_offset + 25
            y_mid = (y1 + y2) / 2
            y_center = y_mid - (H_MATCH / 4)
            r2_y_coords.append(y_mid)

            if p:
                name = format_fio_without_patronymic(p['fio'])
                details = f"{p.get('city_name', '')}, {p.get('club_name', '')}".strip(', ').strip()
                draw.text((x_start_r1 + 5, y_center - 14), name, font=font, fill='black')
                if details:
                    draw.text((x_start_r1 + 5, y_center + 14), details, font=small_font, fill='black')
                draw.line([(x_start_r1, y_mid), (x_end_r1, y_mid)], fill='black', width=LINE_W)

        # Добавляем линию победителя из R1 в список линий для R2
        r2_y_coords.append(y_winner_fight1)

        # --- Соединительные линии для последующих раундов ---
        y_coords_by_round = [r2_y_coords]
        for r in range(1, num_rounds):
            x_start = PAD + W_NAME + r * W_ROUND
            x_end = x_start + W_ROUND
            prev_y_coords = y_coords_by_round[r - 1]
            current_y_coords = []

            for i in range(0, len(prev_y_coords), 2):
                y1, y2 = prev_y_coords[i], prev_y_coords[i + 1]
                y_mid = (y1 + y2) / 2
                current_y_coords.append(y_mid)
                draw.line([(x_start, y1), (x_start, y2)], fill='black', width=LINE_W)
                draw.line([(x_start, y_mid), (x_end, y_mid)], fill='black', width=LINE_W)
            y_coords_by_round.append(current_y_coords)

        img.save(file_path)
        return

    # --- СТАНДАРТНАЯ ЛОГИКА ДЛЯ ВСЕХ ОСТАЛЬНЫХ СЛУЧАЕВ ---
    y_coords_by_round = []

    r1_y_lines = []
    for i, participant in enumerate(seeded_participants):
        y_center = (i * H_MATCH / 2) + (H_MATCH / 4) + top_offset
        line_y = y_center + 25

        if participant:
            name = format_fio_without_patronymic(participant['fio'])
            city = participant.get('city_name') or ''
            club = participant.get('club_name') or ''
            details = f"{city}, {club}".strip(', ').strip()

            draw.text((PAD + 5, y_center - 20), name, font=font, fill='black')
            if details:
                draw.text((PAD + 5, y_center + 8), details, font=small_font, fill='black')

            draw.line([(PAD, line_y), (PAD + W_NAME, line_y)], fill='black', width=LINE_W)

        r1_y_lines.append(line_y)

    r2_y_coords = []
    x_start_r1 = PAD + W_NAME
    x_end_r1 = x_start_r1 + W_ROUND

    for i in range(0, bracket_size, 2):
        p1 = seeded_participants[i]
        p2 = seeded_participants[i + 1]
        y1, y2 = r1_y_lines[i], r1_y_lines[i + 1]

        if p1 and p2:
            y_mid = (y1 + y2) / 2
            r2_y_coords.append(y_mid)
            draw.line([(x_start_r1, y1), (x_start_r1, y2)], fill='black', width=LINE_W)
            draw.line([(x_start_r1, y_mid), (x_end_r1, y_mid)], fill='black', width=LINE_W)
        elif p1 or p2:
            y_bye = y1 if p1 else y2
            r2_y_coords.append(y_bye)
            draw.line([(x_start_r1, y_bye), (x_end_r1, y_bye)], fill='black', width=LINE_W)
        else:
            y_mid = (y1 + y2) / 2
            r2_y_coords.append(y_mid)

    y_coords_by_round.append(r2_y_coords)

    for r in range(1, num_rounds):
        x_start = PAD + W_NAME + r * W_ROUND
        x_end = x_start + W_ROUND
        prev_y_coords = y_coords_by_round[r - 1]
        current_y_coords = []

        for i in range(0, len(prev_y_coords), 2):
            y1, y2 = prev_y_coords[i], prev_y_coords[i + 1]
            y_mid = (y1 + y2) / 2
            current_y_coords.append(y_mid)
            draw.line([(x_start, y1), (x_start, y2)], fill='black', width=LINE_W)
            draw.line([(x_start, y_mid), (x_end, y_mid)], fill='black', width=LINE_W)
        y_coords_by_round.append(current_y_coords)

    img.save(file_path)


def draw_pair_image(pair: list, file_path: str, page_info: str, header_info: dict):
    """
    Рисует изображение для одной пары участников в стиле турнирной сетки.
    """
    # --- Константы ---
    HEADER_HEIGHT = 120
    H_MATCH = 150  # Высота одного "матча" в сетке, используем для отступов
    W_NAME = 400   # Ширина блока с именами
    PAD = 30
    LINE_W = 2
    IMG_WIDTH = 1200
    # Высота рассчитывается под 2-х участников + заголовок + отступы
    IMG_HEIGHT = int(H_MATCH + PAD * 2 + HEADER_HEIGHT)


    # --- Шрифты (как в draw_bracket_image) ---
    font_path = os.path.join("fonts", "DejaVuSans.ttf")
    try:
        font = ImageFont.truetype(font_path, 18)
        small_font = ImageFont.truetype(font_path, 14)
    except IOError:
        print(f"ПРЕДУПРЕЖДЕНИЕ: Шрифт не найден. Кириллица может отображаться некорректно.")
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    img = Image.new('RGB', (IMG_WIDTH, IMG_HEIGHT), 'white')
    draw = ImageDraw.Draw(img)

    # --- Отрисовка заголовка (аналогично draw_bracket_image) ---
    if header_info:
        y_cursor = PAD
        line1 = header_info.get("line1", "")
        if line1:
            draw.multiline_text((IMG_WIDTH / 2, y_cursor), line1, font=small_font, fill='black', anchor="ma", align="center")
            y_cursor += 45

        draw.text((PAD, y_cursor), header_info.get("line2", ""), font=font, fill='black', anchor="ls")
        draw.text((IMG_WIDTH / 2, y_cursor), header_info.get("line3", ""), font=font, fill='black', anchor="ms")
        draw.text((IMG_WIDTH - PAD, y_cursor), header_info.get("line4", ""), font=font, fill='black', anchor="rs")

    # --- Отрисовка пары ---
    top_offset = PAD + HEADER_HEIGHT
    y_lines = []

    for i, participant in enumerate(pair):
        # Рассчитываем y-координаты как для первых двух участников в сетке
        y_center = (i * H_MATCH / 2) + (H_MATCH / 4) + top_offset
        line_y = y_center + 25

        # Блок с именем и информацией
        if participant:
            name = format_fio_without_patronymic(participant['fio'])
            city = participant.get('city_name') or ''
            club = participant.get('club_name') or ''
            details = f"{city}, {club}".strip(', ').strip()

            draw.text((PAD + 5, y_center - 20), name, font=font, fill='black')
            if details:
                # Рисуем детали под именем
                draw.text((PAD + 5, y_center + 8), details, font=small_font, fill='black')
        else:
            name = "BYE" # Если в паре нет второго участника
            draw.text((PAD + 5, y_center), name, font=font, fill='black')

        # Линия под именем
        draw.line([(PAD, line_y), (PAD + W_NAME, line_y)], fill='black', width=LINE_W)
        y_lines.append(line_y)

    # Вертикальная и горизонтальная линии, соединяющие пару
    if len(y_lines) == 2:
        y1, y2 = y_lines
        y_mid = (y1 + y2) / 2
        x_start = PAD + W_NAME
        x_end = x_start + 100 # Короткая линия вправо

        draw.line([(x_start, y1), (x_start, y2)], fill='black', width=LINE_W)
        draw.line([(x_start, y_mid), (x_end, y_mid)], fill='black', width=LINE_W)

    # --- Информация о странице (внизу, по центру) ---
    draw.text((IMG_WIDTH / 2, IMG_HEIGHT - PAD), page_info, font=small_font, fill='black', anchor="ms")

    img.save(file_path)