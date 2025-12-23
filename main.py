import flet as ft

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

        return ft.Container(
            content=ft.Row(
                [
                    checkbox,
                    ft.Text(goal_data["name"], size=16, expand=True),
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

    def add_new_goal(e):
        text = new_goal_input.value.strip()
        if not text:
            return

        new_goal = {"name": text, "completed": False}
        goals.append(new_goal)

        index = len(goals) - 1
        card = create_goal_card(new_goal, index)
        goals_container.controls.append(card)

        new_goal_input.value = ""
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

    input_area = ft.Row(
        [new_goal_input, add_btn],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # Вот здесь основной фон приложения
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
        bgcolor=ft.Colors.BLACK12,           # ← меняй здесь (рекомендую начать с GREY_800 или BLUE_GREY_800)
        expand=True,
        padding=20,
    )

    page.add(main_container)

    update_progress()   # ← инициализация прогресса

ft.app(target=main)