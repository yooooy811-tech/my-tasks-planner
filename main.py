import flet as ft
from datetime import datetime, timedelta

def main(page: ft.Page):
    page.title = "Мой Планировщик Целей"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # Данные: список больших целей (каждая — словарь с subgoals и weight)
    goals = []

    # Контейнер для отображения списка целей
    goals_container = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    progress_text = ft.Text("Прогресс: 0 из 0", size=14, color=ft.Colors.GREY_300)

    def update_progress():
        total = len(goals)
        completed = sum(1 for g in goals if g["completed"])
        progress_text.value = f"Прогресс: {completed} из {total}"
        page.update()

    # Рекурсивный расчёт прогресса (0.0–1.0)
    def calculate_progress(goal):
        subgoals = goal.get("subgoals", [])
        if not subgoals:
            return 1.0 if goal["completed"] else 0.0
        
        total_weight = sum(s.get("weight", 1.0) for s in subgoals)
        if total_weight == 0:
            return 0.0
        
        weighted_progress = sum(
            calculate_progress(s) * s.get("weight", 1.0) for s in subgoals
        )
        return weighted_progress / total_weight

    # Создание карточки цели (с ProgressBar и кнопкой "Подцели")
    def create_goal_card(goal_data, index):
        def toggle_completed(e):
            goal_data["completed"] = e.control.value
            update_progress()
            page.update()  # Обновляем карточку, чтобы прогресс изменился

        def delete_goal(e):
            nonlocal goals
            if index < len(goals):
                del goals[index]
                refresh_goals()
                update_progress()

        def open_subgoals(e):
            show_subgoals(goal_data)

        checkbox = ft.Checkbox(
            value=goal_data["completed"],
            on_change=toggle_completed,
            shape=ft.RoundedRectangleBorder(radius=4),
        )

        delete_btn = ft.IconButton(
            icon=ft.Icons.DELETE_OUTLINE,
            icon_color=ft.Colors.RED_400,
            icon_size=20,
            tooltip="Удалить",
            on_click=delete_goal,
        )

        # Кнопка "Подцели"
        subgoals_btn = ft.IconButton(
            icon=ft.Icons.LIST_ALT,
            icon_color=ft.Colors.BLUE_400,
            icon_size=20,
            tooltip="Подцели",
            on_click=open_subgoals,
        )

        # Прогресс-бар
        progress = calculate_progress(goal_data)
        progress_bar = ft.ProgressBar(
            value=progress,
            width=200,
            color=ft.Colors.GREEN_400 if progress > 0.8 else ft.Colors.BLUE_400,
            bgcolor=ft.Colors.GREY_700,
        )

        # Дедлайн
        deadline_str = "Без срока"
        deadline_color = ft.Colors.GREY_400
        if goal_data.get("deadline"):
            deadline_str = goal_data["deadline"].strftime("%d.%m.%Y %H:%M")
            if goal_data["deadline"] < datetime.now() and not goal_data["completed"]:
                deadline_color = ft.Colors.RED_400
                deadline_str = "Просрочено! " + deadline_str

        return ft.Container(
            content=ft.Row(
                [
                    checkbox,
                    ft.Column(
                        [
                            ft.Text(goal_data["name"], size=16),
                            ft.Text(deadline_str, size=12, color=deadline_color),
                            progress_bar,
                        ],
                        spacing=4,
                        expand=True,
                    ),
                    subgoals_btn,
                    delete_btn,
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=12,
            bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.BLUE_GREY_800),
            border_radius=12,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_700),
        )

    def refresh_goals():
        goals_container.controls.clear()
        for i, goal in enumerate(goals):
            card = create_goal_card(goal, i)
            goals_container.controls.append(card)
        page.update()

    # Отображение подцелей для конкретной цели
    def show_subgoals(parent_goal):
        subgoals_container = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

        def add_subgoal_click(e):
            name = subgoal_input.value.strip()
            if not name:
                return

            weight = float(weight_input.value or 1.0)  # По умолчанию 1.0
            new_subgoal = {
                "name": name,
                "completed": False,
                "deadline": None,
                "subgoals": [],
                "weight": weight,
            }
            parent_goal["subgoals"].append(new_subgoal)
            subgoal_input.value = ""
            weight_input.value = "1.0"
            refresh_subgoals()
            page.update()

        subgoal_input = ft.TextField(hint_text="Название подцели", expand=True)
        weight_input = ft.TextField(
            hint_text="Вес (по умолчанию 1.0)", value="1.0", width=100
        )

        add_sub_btn = ft.ElevatedButton("Добавить", on_click=add_subgoal_click)

        def refresh_subgoals():
            subgoals_container.controls.clear()
            for i, subgoal in enumerate(parent_goal["subgoals"]):
                sub_card = create_goal_card(subgoal, i)  # Используем ту же функцию!
                subgoals_container.controls.append(sub_card)
            page.update()

        refresh_subgoals()

        dialog = ft.AlertDialog(
            title=ft.Text(f"Подцели: {parent_goal['name']}"),
            content=ft.Column(
                [
                    ft.Row([subgoal_input, weight_input, add_sub_btn]),
                    subgoals_container,
                ],
                spacing=12,
                expand=True,
            ),
            actions=[ft.TextButton("Закрыть", on_click=lambda _: page.close(dialog))],
            modal=True,
        )
        page.open(dialog)

    # Поле ввода новой большой цели
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
        if e.control.value:
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

        new_goal = {
            "name": text,
            "completed": False,
            "deadline": selected_deadline,
            "subgoals": [],  # ← Подцели
            "weight": 1.0,   # ← Вес в родителе
        }
        goals.append(new_goal)

        index = len(goals) - 1
        card = create_goal_card(new_goal, index)
        goals_container.controls.append(card)

        new_goal_input.value = ""
        selected_deadline = None
        deadline_input.value = "Не установлен"
        update_progress()
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
        content=ft.Column(
            [
                ft.Text("Планировщик целей", size=28, weight=ft.FontWeight.BOLD),
                ft.Text("Разбивайте большие задачи на маленькие шаги", size=14, color=ft.Colors.GREY_400),
                ft.Container(height=16),
                progress_text,
                ft.Container(height=8),
                input_area,
                ft.Container(height=16),
                goals_container,
            ],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        ),
        bgcolor=ft.Colors.BLACK12,
        expand=True,
        padding=20,
    )

    page.add(main_container)
    update_progress()

ft.app(target=main)