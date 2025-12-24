import flet as ft
from datetime import datetime


def main(page: ft.Page):
    page.title = "Мой Планировщик Целей"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    goals = []
    selected_deadline = None

    goals_container = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
    progress_text = ft.Text("Прогресс: 0 из 0", size=14, color=ft.Colors.GREY_300)

    def update_progress():
        total = len(goals)
        completed = sum(1 for g in goals if g["completed"])
        progress_text.value = f"Прогресс: {completed} из {total}"
        page.update()

    def calculate_progress(goal):
        subgoals = goal.get("subgoals", [])
        if not subgoals:
            return 1.0 if goal["completed"] else 0.0

        total_weight = sum(s.get("weight", 1.0) for s in subgoals)
        if total_weight == 0:
            return 0.0

        weighted_progress = sum(
            calculate_progress(s) * s.get("weight", 1.0)
            for s in subgoals
        )
        return min(weighted_progress / total_weight, 1.0)

    def mark_all_completed(goal):
        goal["completed"] = True
        for subgoal in goal.get("subgoals", []):
            mark_all_completed(subgoal)

    def create_goal_card(goal_data, parent=None, level=0):
        subgoals_container = ft.Column(spacing=8)

        progress = calculate_progress(goal_data)
        progress_bar = ft.ProgressBar(
            value=progress,
            width=200,
            color=ft.Colors.GREEN_400 if progress > 0.8 else ft.Colors.BLUE_400,
            bgcolor=ft.Colors.GREY_700,
        )

        progress_label = ft.Text(
            f"Прогресс: {int(progress * 100)}%",
            size=12,
            color=ft.Colors.GREY_300,
            weight=ft.FontWeight.W_500,
        )

        def toggle_completed(e):
            goal_data["completed"] = e.control.value
            if goal_data["completed"] and level == 0:
                mark_all_completed(goal_data)

            new_progress = calculate_progress(goal_data)
            progress_bar.value = new_progress
            progress_bar.color = (
                ft.Colors.GREEN_400 if new_progress > 0.8 else ft.Colors.BLUE_400
            )
            progress_label.value = f"Прогресс: {int(new_progress * 100)}%"

            current_parent = parent
            while current_parent is not None:
                parent_progress = calculate_progress(current_parent)
                current_parent["progress_bar"].value = parent_progress
                current_parent["progress_label"].value = (
                    f"Прогресс: {int(parent_progress * 100)}%"
                )
                current_parent = current_parent.get("parent")

            page.update()

        def delete_goal(e):
            if parent is not None:
                parent["subgoals"].remove(goal_data)
            else:
                goals.remove(goal_data)
            refresh_goals()

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

        subgoal_input = ft.TextField(hint_text="Название подцели", expand=True)
        weight_input = ft.TextField(
            hint_text="Вес (по умолчанию 1.0)", value="1.0", width=100
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

            weight = float(weight_input.value or 1.0)
            goal_data["subgoals"].append(
                {
                    "name": name,
                    "completed": False,
                    "deadline": selected_sub_deadline,
                    "subgoals": [],
                    "weight": weight,
                }
            )

            subgoal_input.value = ""
            weight_input.value = "1.0"
            selected_sub_deadline = None
            sub_deadline_input.value = "Не установлен"
            refresh_subgoals()
            page.update()

        def refresh_subgoals():
            subgoals_container.controls.clear()
            for subgoal in goal_data["subgoals"]:
                subgoals_container.controls.append(
                    create_goal_card(subgoal, parent=goal_data, level=level + 1)
                )

        refresh_subgoals()

        goal_data["progress_bar"] = progress_bar
        goal_data["progress_label"] = progress_label
        goal_data["parent"] = parent

        return ft.ExpansionTile(
            title=ft.Row(
                [
                    checkbox,
                    ft.Column(
                        [
                            ft.Text(goal_data["name"], size=16),
                            ft.Text(deadline_str, size=12, color=deadline_color),
                            progress_bar,
                            progress_label,
                        ],
                        spacing=4,
                        expand=True,
                    ),
                    delete_btn,
                ]
            ),
            controls=[
                subgoals_container,
                ft.Column(
                    [
                        ft.Row(
                            [
                                subgoal_input,
                                weight_input,
                                ft.ElevatedButton(
                                    "Добавить", on_click=add_subgoal_click
                                ),
                            ],
                            spacing=12,
                        ),
                        ft.Row([sub_deadline_input, sub_deadline_btn], spacing=12),
                    ]
                ),
            ],
            maintain_state=True,
            bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.BLUE_GREY_800),
            shape=ft.RoundedRectangleBorder(radius=12),
        )

    def refresh_goals():
        goals_container.controls.clear()
        for goal in goals:
            goals_container.controls.append(create_goal_card(goal))
        update_progress()
        page.update()

    new_goal_input = ft.TextField(
        hint_text="Введите название большой цели...",
        expand=True,
        on_submit=lambda e: add_new_goal(e),
    )

    deadline_input = ft.TextField(
        value="Не установлен",
        read_only=True,
        expand=True,
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
        deadline_input.value = "Не установлен"
        selected_deadline = None
        refresh_goals()

    page.add(
        ft.Column(
            [
                ft.Text("Планировщик целей", size=28, weight=ft.FontWeight.BOLD),
                progress_text,
                ft.Row(
                    [
                        new_goal_input,
                        ft.ElevatedButton("Добавить", on_click=add_new_goal),
                    ]
                ),
                ft.Row([deadline_input, deadline_btn]),
                goals_container,
            ],
            expand=True,
        )
    )


ft.app(target=main)
