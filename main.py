import flet as ft
from datetime import datetime, timedelta


def main(page: ft.Page):
    page.title = "Мой Планировщик Целей"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # Данные: список больших целей
    goals = []

    goals_container = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

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
            total_weight = sum(s.get("weight", 1.0) for s in subgoals)
            if total_weight == 0:
                return 0.0

            weighted_progress = sum(
                calculate_progress(s) * s.get("weight", 1.0)
                for s in subgoals
            )
            return min(weighted_progress / total_weight, 1.0)

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



    # ---------------- СОЗДАНИЕ КАРТОЧКИ ЦЕЛИ ----------------
    def create_goal_card(goal_data, parent=None, level=0):
        subgoals_container = ft.Column(spacing=8)

        progress = calculate_progress(goal_data)
        progress_bar = ft.ProgressBar(
            value=progress,
            width=200,
            color=ft.Colors.BLUE_300,
            bgcolor=ft.Colors.BLUE_GREY_800,
        )

        progress_label = ft.Text(
            f"Прогресс: {int(progress * 100)}%",
            size=12,
            color=ft.Colors.GREY_300,
            weight=ft.FontWeight.W_500,
        )

        def toggle_completed(e):
            goal_data["completed"] = e.control.value

            # если отметили цель с подцелями — проталкиваем вниз
            if goal_data.get("subgoals"):
                for s in goal_data["subgoals"]:
                    mark_all_completed(s)

            recalc_all_progress()

        def delete_goal(e):
            if parent:
                parent["subgoals"].remove(goal_data)
                parent["completed"] = False
            else:
                goals.remove(goal_data)

            refresh_goals()
            recalc_all_progress()

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

        deadline_str = "Без срока"
        deadline_color = ft.Colors.GREY_400
        if goal_data.get("deadline"):
            deadline_str = goal_data["deadline"].strftime("%d.%m.%Y %H:%M")
            if goal_data["deadline"] < datetime.now() and not goal_data["completed"]:
                deadline_color = ft.Colors.RED_400
                deadline_str = "Просрочено! " + deadline_str

        name_text = ft.Text(
            f"{goal_data['name']} (вес: {goal_data.get('weight', 1.0):.2f})"
            if level > 0 else goal_data["name"],
            size=16,
        )

        def on_weight_change(e):
            try:
                new_weight = float(e.control.value)
            except:
                return

            siblings = parent["subgoals"] if parent else []
            max_allowed = get_max_allowed_weight(siblings, goal_data)

            goal_data["weight"] = min(max(new_weight, 0.0001), max_allowed)
            redistribute_equal_weights(siblings, locked_goal=goal_data)
            recalc_all_progress()

        current_weight_input = ft.TextField(
            value=str(goal_data.get("weight", 1.0)),
            width=80,
            on_change=on_weight_change,
            )

        subgoal_input = ft.TextField(hint_text="Название подцели", expand=True)


        weight_input = ft.TextField(
            hint_text="Вес (по умолчанию 1.0)",
            value=str(goal_data.get("weight", 1.0)),
            width=100,
            #on_change=on_weight_change,
        )

        selected_sub_deadline = None

        sub_deadline_input = ft.TextField(
            hint_text="Дедлайн подцели (дд.мм.гггг чч:мм)",
            value="Не установлен",
            read_only=True,
            expand=True,
            border_radius=12,
            height=48,
        )

        def handle_sub_deadline_change(e):
            nonlocal selected_sub_deadline
            selected_sub_deadline = e.control.value
            sub_deadline_input.value = selected_sub_deadline.strftime("%d.%m.%Y %H:%M")
            page.update()

        sub_deadline_btn = ft.ElevatedButton(
            text="Выбрать дату и время",
            icon=ft.Icons.CALENDAR_MONTH,
            on_click=lambda e: page.open(
                ft.CupertinoBottomSheet(
                    ft.CupertinoDatePicker(
                        date_picker_mode=ft.CupertinoDatePickerMode.DATE_AND_TIME,
                        on_change=handle_sub_deadline_change,
                    ),
                    height=216,
                    padding=ft.padding.only(top=6),
                )
            ),
        )

        def add_subgoal_click(e):
            nonlocal selected_sub_deadline
            name = subgoal_input.value.strip()
            if not name:
                return

            try:
                weight = float(weight_input.value)
                if weight <= 0:
                    weight = None
            except:
                weight = None

            new_subgoal = {
                "name": name,
                "completed": False,
                "deadline": selected_sub_deadline,
                "subgoals": [],
                "weight": 1.0,  # временно
            }

            goal_data["subgoals"].append(new_subgoal)

            # 1. СНАЧАЛА — всегда честно делим по количеству
            force_equal_weights(goal_data["subgoals"])

            # 2. ЕСЛИ пользователь задал вес — применяем его ПОСЛЕ
            if weight is not None:
                max_allowed = get_max_allowed_weight(goal_data["subgoals"], new_subgoal)
                new_subgoal["weight"] = min(weight, max_allowed)

                # остальные перерасчитываем
                remaining = 1.0 - new_subgoal["weight"]
                others = [s for s in goal_data["subgoals"] if s is not new_subgoal]
                if others:
                    eq = remaining / len(others)
                    for s in others:
                        s["weight"] = eq


            goal_data["completed"] = False

            subgoal_input.value = ""
            weight_input.value = "1.0"
            selected_sub_deadline = None
            sub_deadline_input.value = "Не установлен"

            refresh_subgoals()
            recalc_all_progress()



        def refresh_subgoals():
            subgoals_container.controls.clear()
            for s in goal_data["subgoals"]:
                subgoals_container.controls.append(
                    create_goal_card(s, parent=goal_data, level=level + 1)
                )
            page.update()

        refresh_subgoals()

        goal_data["progress_bar"] = progress_bar
        goal_data["progress_label"] = progress_label
        goal_data["parent"] = parent

        return ft.ExpansionTile(
            title=ft.Row(
                [
                    checkbox,
                    current_weight_input if level > 0 else ft.Container(),
                    ft.Column(
                        [
                            name_text,
                            ft.Text(deadline_str, size=12, color=deadline_color),
                            progress_bar,
                            progress_label,
                        ],
                        spacing=4,
                        expand=True,
                    ),
                    delete_btn,
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            controls=[
                subgoals_container,
                ft.Column(
                    [
                        ft.Row(
                            [
                                subgoal_input,
                                weight_input,
                                ft.ElevatedButton("Добавить", on_click=add_subgoal_click)
                            ],
                            spacing=12,
                        ),
                        ft.Row([sub_deadline_input, sub_deadline_btn], spacing=12),
                    ],
                    spacing=12,
                ),
            ],
            maintain_state=True,
            bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.BLUE_GREY_800),
            shape=ft.RoundedRectangleBorder(radius=12),
        )

    # ---------------- ОБНОВЛЕНИЕ ----------------
    def refresh_goals():
        goals_container.controls.clear()
        for goal in goals:
            goals_container.controls.append(create_goal_card(goal))
        recalc_all_progress()

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
            }
        )

        new_goal_input.value = ""
        selected_deadline = None
        deadline_input.value = "Не установлен"
        refresh_goals()
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
    recalc_all_progress()


ft.app(target=main)
