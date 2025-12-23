import flet as ft

def main(page: ft.Page):
    page.title = "Мой первый планировщик"
    page.theme_mode = ft.ThemeMode.DARK
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.update()

    page.add(
        ft.Column(
            [
                ft.Text("Привет! Это твой планировщик задач", size=24, weight=ft.FontWeight.BOLD),
                ft.Text("Скоро здесь будут цели и прогресс", size=16),
                ft.ElevatedButton("Тестовая кнопка", on_click=lambda e: print("Кнопка нажата!")),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=30,
        )
    )

ft.app(target=main)