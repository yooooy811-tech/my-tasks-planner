import flet as ft
from datetime import datetime, timedelta


def main(page: ft.Page):
    current_goal = None
    navigation_stack = []

    page.title = "Мой Планировщик Целей"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # Данные: список больших целей
    goals = []

    content_area = ft.Column(
    spacing=16,
    expand=True,
    )

    def render_view():
        content_area.controls.clear()

        # -------- ROOT: список больших целей --------
        if current_goal is None:
            content_area.controls.extend([
                ft.Text(
                    "Планировщик целей",
                    size=28,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Text(
                    "Разбивайте большие задачи на маленькие шаги",
                    size=14,
                    color=ft.Colors.GREY_400,
                ),
                ft.Container(height=16),
                progress_text,
                ft.Container(height=8),
                input_area,
                ft.Container(height=16),
            ])

            for goal in goals:
                content_area.controls.append(create_goal_card(goal))

            return


        # -------- FOCUS: мы внутри цели --------

        # Заголовок
        content_area.controls.append(
            ft.Row(
                [
                    ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        on_click=go_back,
                        tooltip="Назад",
                    ),

                    ft.Text(
                        current_goal["name"],
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER,
                        expand=True,
                    ),

                    # Пустышка, чтобы центр был честным
                    ft.Container(width=40),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            )
        )


        # Общий прогресс
        content_area.controls.append(
            ft.ProgressBar(
                value=calculate_progress(current_goal),
                height=12,
            )
        )

        # Подцели
        for sub in current_goal.get("subgoals", []):
            content_area.controls.append(
                create_goal_card(sub)
            )

    def create_goal_card(goal_data):
        def open_goal(e):
            nonlocal current_goal
            navigation_stack.append(current_goal)
            current_goal = goal_data
            render_view()
            page.update()

        return ft.Container(
            padding=16,
            border_radius=12,
            bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.BLUE_GREY_800),
            on_click=open_goal,
            content=ft.Column(
                [
                    ft.Text(goal_data["name"], size=16),
                    ft.ProgressBar(value=calculate_progress(goal_data)),
                ],
                spacing=8,
            ),
    )
    def go_back(e):
        nonlocal current_goal
        current_goal = navigation_stack.pop()
        render_view()
        page.update()


    progress_text = ft.Text("Прогресс: 0 из 0", size=14, color=ft.Colors.GREY_300)

    def update_progress():
        total = len(goals)
        completed = sum(1 for g in goals if calculate_progress(g) >= 0.999)
        progress_text.value = f"Прогресс: {completed} из {total}"
        page.update()

    # ---------------- ПАТЧ: корректный рекурсивный расчёт ----------------
    def calculate_progress(goal):
        subgoals = goal.get("subgoals", [])

        # если есть подцели — считаем ТОЛЬКО по ним
        if subgoals:
            progress = 0.0
            for s in subgoals:
                progress += calculate_progress(s) * s.get("weight", 0.0)
            return min(progress, 1.0)

        # если подцелей нет — обычная галочка
        return 1.0 if goal["completed"] else 0.0

    # ---------------- ПАТЧ: глобальный пересчёт ВСЕГО ----------------
    def recalc_all_progress():
        def update_goal(goal):
            progress = calculate_progress(goal)

            if "progress_bar" in goal:
                goal["progress_bar"].value = progress
                goal["progress_bar"].color = ft.Colors.BLUE_300

            if "progress_label" in goal:
                goal["progress_label"].value = f"Прогресс: {int(progress * 100)}%"

            for s in goal.get("subgoals", []):
                update_goal(s)

        for g in goals:
            update_goal(g)

        update_progress()
        page.update()

    # Рекурсивная отметка всех подцелей выполненными
    def mark_all_completed(goal):
        goal["completed"] = True
        for subgoal in goal.get("subgoals", []):
            mark_all_completed(subgoal)

    # Нормализация весов подцелей
    def normalize_weights(subgoals):
        total_weight = sum(s.get("weight", 1.0) for s in subgoals)
        if total_weight > 1.0:
            for s in subgoals:
                s["weight"] = s.get("weight", 1.0) / total_weight

    def force_equal_weights(subgoals):
        if not subgoals:
            return
        w = 1.0 / len(subgoals)
        for s in subgoals:
            s["weight"] = w

    

    def get_max_allowed_weight(subgoals, current_goal):
        used = 0.0
        for s in subgoals:
            if s is not current_goal:
                used += s["weight"]
        remaining = 1.0 - used
        return max(remaining, 0.0)


    new_goal_input = ft.TextField(
        hint_text="Введите название большой цели...",
        autofocus=True,
        expand=True,
        border_radius=12,
        height=48,
        on_submit=lambda e: add_new_goal(e),
    )

    selected_deadline = None

    deadline_input = ft.TextField(
        hint_text="Дедлайн (дд.мм.гггг чч:мм)",
        value="Не установлен",
        read_only=True,
        expand=True,
        border_radius=12,
        height=48,
    )

    def handle_deadline_change(e):
        nonlocal selected_deadline
        selected_deadline = e.control.value
        deadline_input.value = selected_deadline.strftime("%d.%m.%Y %H:%M")
        page.update()

    deadline_btn = ft.ElevatedButton(
        text="Выбрать дату и время",
        icon=ft.Icons.CALENDAR_MONTH,
        on_click=lambda e: page.open(
            ft.CupertinoBottomSheet(
                ft.CupertinoDatePicker(
                    date_picker_mode=ft.CupertinoDatePickerMode.DATE_AND_TIME,
                    on_change=handle_deadline_change,
                ),
                height=216,
                padding=ft.padding.only(top=6),
            )
        ),
    )

    def add_new_goal(e):
        nonlocal selected_deadline
        text = new_goal_input.value.strip()
        if not text:
            return

        goals.append(
            {
                "name": text,
                "completed": False,
                "deadline": selected_deadline,
                "subgoals": [],
                "weight": 1.0,
                "manual_weights": False,
            }
        )

        new_goal_input.value = ""
        selected_deadline = None
        deadline_input.value = "Не установлен"
        render_view()
        page.update()
        new_goal_input.focus()

    add_btn = ft.ElevatedButton(
        "Добавить большую цель",
        icon=ft.Icons.ADD,
        on_click=add_new_goal,
        height=48,
        style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
    )

    input_area = ft.Column(
        [
            ft.Row([new_goal_input, add_btn], spacing=12),
            ft.Row([deadline_input, deadline_btn], spacing=12),
        ],
        spacing=12,
    )

    main_container = ft.Container(
        content=content_area,
        bgcolor=ft.Colors.BLACK12,
        expand=True,
        padding=20,
    )

    page.add(main_container)
    render_view()
    recalc_all_progress()


ft.app(target=main)
