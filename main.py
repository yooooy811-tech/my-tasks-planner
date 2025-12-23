import flet as ft
from datetime import datetime, timedelta

def main(page: ft.Page):
    page.title = "Мой Планировщик Целей"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # Данные: список словарей с целями
    goals = []

    # Контроллер для отображения списка целей
    goals_container = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    # Текстовые поля для статистики
    progress_text = ft.Text("Прогресс: 0 из 0", size=14, color=ft.Colors.GREY_300)

    def update_progress():
        total = len(goals)
        completed = sum(1 for g in goals if g["completed"])
        progress_text.value = f"Прогресс: {completed} из {total}"
        page.update()

    # Функция создания визуальной карточки для одной цели
    def create_goal_card(goal_data, index):
        def toggle_completed(e):
            goal_data["completed"] = e.control.value
            update_progress()

        def delete_goal(e):
            nonlocal goals
            if index < len(goals):
                del goals[index]
                refresh_goals()
                update_progress()

        checkbox = ft.Checkbox(
            value=goal_data["completed"],
            on_change=toggle_completed,
            shape=ft.RoundedRectangleBorder(radius=4),
        )

        delete_btn = ft.IconButton(
            icon=ft.Icons.DELETE_OUTLINE,
            icon_color=ft.Colors.RED_400,
            icon_size=20,
            tooltip="Удалить цель",
            on_click=delete_goal,
        )

        # Отображаем дедлайн, если он есть
        deadline_str = "Без срока"
        is_overdue = False 
        warning_icon=None
        # deadline_widget = None
        # card_bg = None
        deadline_color = ft.Colors.GREY_400
        if goal_data.get("deadline"):
            deadline_str = goal_data["deadline"].strftime("%d.%m.%Y %H:%M")
            if goal_data["deadline"]<datetime.now() and goal_data["completed"]==False:
                is_overdue = True
                deadline_color=ft.Colors.RED_400
                deadline_str="Просрочено! " + deadline_str
                
        if is_overdue:
            warning_icon = ft.Icon(
                ft.Icons.WARNING_AMBER, 
                size=14, 
                color=ft.Colors.RED_400)
            card_bg=ft.Colors.with_opacity(0.15, ft.Colors.RED_600)
            deadline_widget=ft.Row([warning_icon, ft.Text(deadline_str, color=deadline_color)])
        else:
            card_bg=ft.Colors.with_opacity(0.15, ft.Colors.BLUE_GREY_800)
            deadline_widget = ft.Text(deadline_str, color=deadline_color)
        

        return ft.Container(
            content=ft.Row(
                [
                    checkbox,
                    ft.Column(
                        [
                            ft.Text(goal_data["name"], size=16),
                            deadline_widget

                        ],
                        spacing=2,
                        expand=True,
                    ),
                    delete_btn,
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=12,
            bgcolor=card_bg,
            border_radius=12,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_700),
        )

    # Обновление всего списка целей на экране
    def refresh_goals():
        goals_container.controls.clear()
        for i, goal in enumerate(goals):
            card = create_goal_card(goal, i)
            goals_container.controls.append(card)
        page.update()

    # Поле ввода новой цели
    new_goal_input = ft.TextField(
        hint_text="Введите название большой цели...",
        autofocus=True,
        expand=True,
        border_radius=12,
        height=48,
        on_submit=lambda e: add_new_goal(e),
    )

    selected_deadline = None  # здесь будет datetime или None

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
            selected_deadline = e.control.value  # это datetime
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
            "deadline": selected_deadline  # datetime или None
        }
        goals.append(new_goal)

        index = len(goals) - 1
        card = create_goal_card(new_goal, index)
        goals_container.controls.append(card)

        # Сброс после добавления
        new_goal_input.value = ""
        selected_deadline = None
        deadline_input.value = "Не установлен"
        update_progress()
        page.update()
        new_goal_input.focus()

    # Кнопка добавления
    add_btn = ft.ElevatedButton(
        "Добавить",
        icon=ft.Icons.ADD,
        on_click=add_new_goal,
        height=48,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.BLUE_700,
            color=ft.Colors.WHITE,
        ),
    )

    # Область ввода
    input_area = ft.Column(
        [
            ft.Row([new_goal_input, add_btn], spacing=12),
            ft.Row([deadline_input, deadline_btn], spacing=12),
        ],
        spacing=12,
    )

    # Основной контейнер
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