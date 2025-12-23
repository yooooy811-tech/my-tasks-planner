import flet as ft

def main(page: ft.Page):
    page.title = "Мой Планировщик Целей"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # Список, где будут храниться все добавленные цели (пока просто строки)
    goals = []                   # ← это обычный python-список

    # Контрол, который будет показывать список целей на экране
    goals_view = ft.Column(spacing=12)

    # Поле для ввода новой цели
    new_goal = ft.TextField(
        hint_text="Введите название большой цели...",
        autofocus=True,              # сразу фокус при запуске
        expand=True,                 # растягивается по ширине
        border_radius=12,
        height=48,
        on_submit=lambda e: add_goal(e),  # Enter тоже добавляет
    )

    # Функция, которая добавляет новую цель
    def add_goal(e):
        goal_text = new_goal.value.strip()  # убираем лишние пробелы
        if not goal_text:                   # ничего не делаем, если пусто
            return

        # Создаём визуальный элемент для цели (Checkbox + текст)
        goal_item = ft.Checkbox(
            label=goal_text,
            value=False,
        )

        # Добавляем в список на экране
        goals_view.controls.append(goal_item)

        # Сохраняем в наш python-список (позже пригодится)
        goals.append({"name": goal_text, "completed": False})

        # Очищаем поле ввода и обновляем интерфейс
        new_goal.value = ""
        page.update()

        # Возвращаем фокус в поле (удобно продолжать вводить)
        new_goal.focus()

    # Кнопка добавления
    add_button = ft.ElevatedButton(
        "Добавить цель",
        icon=ft.Icons.ADD,
        on_click=add_goal,
        height=48,
    )

    # Верхняя панель ввода (поле + кнопка в ряд)
    input_row = ft.Row(
        [new_goal, add_button],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # Собираем весь интерфейс
    page.add(
        ft.Column(
            [
                ft.Text("Планировщик больших целей", size=28, weight=ft.FontWeight.BOLD),
                ft.Text("Добавляйте цели, которые хотите достичь", size=14, color=ft.Colors.GREY_400),
                ft.Container(height=20),  # отступ
                input_row,
                ft.Container(height=16),
                goals_view,               # здесь будут появляться цели
            ],
            spacing=16,
            scroll=ft.ScrollMode.AUTO,    # прокрутка, если целей много
            expand=True,                  # занимает всё доступное место
        )
    )

ft.app(target=main)