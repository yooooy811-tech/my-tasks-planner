import flet as ft
from datetime import datetime, timedelta
import asyncio


def main(page: ft.Page):
    current_goal = None
    navigation_stack = []

    page.title = "Мой Планировщик Целей"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    goals = []

    content_column = ft.Column(
        spacing=16,
        expand=True,
    )

    content_container = ft.Container(
        content=content_column,
        expand=True,
        animate_opacity=300,
        opacity=1.0,
    )

    def render_view():
        content_column.controls.clear()

        if current_goal is None:
            content_column.controls.extend([
                ft.Text("Планировщик целей", size=28, weight=ft.FontWeight.BOLD),
                ft.Text("Разбивайте большие задачи на маленькие шаги", size=14, color=ft.Colors.GREY_400),
                ft.Container(height=16),
                progress_text,
                ft.Container(height=8),
                input_area,
                ft.Container(height=16),
            ])

            for goal in goals:
                content_column.controls.append(create_goal_card(goal))

            return

        content_column.controls.append(
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
                    ft.Container(width=40),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            )
        )

        content_column.controls.append(
            ft.ProgressBar(
                value=calculate_progress(current_goal),
                height=12,
            )
        )

        # Форма добавления подцели
        sub_deadline_input = ft.TextField(
            value="Не установлен",
            read_only=True,
            expand=True,
        )

        selected_sub_deadline = None

        def handle_subgoal_deadline_change(ev):
            nonlocal selected_sub_deadline
            selected_sub_deadline = ev.control.value
            if selected_sub_deadline:
                sub_deadline_input.value = selected_sub_deadline.strftime("%d.%m.%Y %H:%M")
            else:
                sub_deadline_input.value = "Не установлен"
            page.update()

        deadline_btn = ft.ElevatedButton(
            text="Выбрать дедлайн",
            icon=ft.Icons.CALENDAR_MONTH,
            on_click=lambda ev: page.open(
                ft.CupertinoBottomSheet(
                    ft.CupertinoDatePicker(
                        date_picker_mode=ft.CupertinoDatePickerMode.DATE_AND_TIME,
                        on_change=handle_subgoal_deadline_change,
                    ),
                    height=216,
                    padding=ft.padding.only(top=6),
                )
            ),
        )

        content_column.controls.append(
            ft.Row(
                [
                    new_subgoal_input,
                    add_subgoal_btn,
                ],
                spacing=12,
            )
        )

        content_column.controls.append(
            ft.Row([sub_deadline_input, deadline_btn], spacing=12)
        )

        for sub in current_goal.get("subgoals", []):
            content_column.controls.append(create_goal_card(sub))

    def create_goal_card(goal_data):
        def open_goal(e):
            async def transition():
                nonlocal current_goal
                content_container.opacity = 0
                page.update()
                await asyncio.sleep(0.25)

                navigation_stack.append(current_goal)
                current_goal = goal_data
                render_view()
                page.update()

                await asyncio.sleep(0.05)
                content_container.opacity = 1
                page.update()

            page.run_task(transition)

        def toggle_completed(e):
            goal_data["completed"] = e.control.value
            recalc_all_progress()

        def delete_goal(e):
            if current_goal and current_goal.get("subgoals"):
                current_goal["subgoals"].remove(goal_data)
            else:
                goals.remove(goal_data)
            render_view()
            recalc_all_progress()

        def open_edit_goal_dialog(goal):
            print(f"DEBUG: open_edit_goal_dialog called for {goal.get('name')}")
            name_input = ft.TextField(value=goal["name"], label="Название цели")
            # weight only for subgoals (not for top-level goals)
            weight_input = None
            is_top_level = goal in goals
            if not is_top_level:
                weight_input = ft.TextField(
                    value=str(goal.get("weight", 1.0)),
                    label="Вес подцели (0 < w ≤ 1)",
                    keyboard_type=ft.KeyboardType.NUMBER,
                )
            deadline_input = ft.TextField(
                value=goal.get("deadline").strftime("%d.%m.%Y %H:%M") if goal.get("deadline") else "Не установлен",
                label="Дедлайн (дд.мм.гггг чч:мм)",
                read_only=True,
                expand=True
            )

            selected_deadline = goal.get("deadline")

            def handle_deadline_change(e):
                nonlocal selected_deadline
                selected_deadline = e.control.value
                if selected_deadline:
                    deadline_input.value = selected_deadline.strftime("%d.%m.%Y %H:%M")
                else:
                    deadline_input.value = "Не установлен"
                page.update()

            deadline_btn = ft.ElevatedButton(
                text="Выбрать дату",
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

            def save_edit(e):
                print(f"DEBUG: saving edit for {goal.get('name')}")
                goal["name"] = name_input.value.strip() or goal["name"]
                if weight_input is not None:
                    try:
                        w = float(weight_input.value)
                        goal["weight"] = max(0.01, min(1.0, w))
                    except:
                        goal["weight"] = goal.get("weight", 1.0)
                # update deadline
                goal["deadline"] = selected_deadline
                # normalize weights among siblings if this is a subgoal
                parent = find_parent(goal)
                if parent and parent.get("subgoals"):
                    normalize_weights(parent.get("subgoals", []))
                render_view()
                recalc_all_progress()
                try:
                    dialog.open = False
                except Exception:
                    pass
                page.update()

            dialog = ft.AlertDialog(
                title=ft.Text("Редактировать цель/подцель"),
                content=ft.Column([
                    name_input,
                    *( [weight_input] if weight_input is not None else [] ),
                    ft.Row([deadline_input, deadline_btn], spacing=12)
                ], spacing=12),
                actions=[
                    ft.ElevatedButton("Принять", on_click=save_edit),
                    ft.TextButton("Отмена", on_click=lambda e: setattr(dialog, "open", False) or page.update())
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            print("DEBUG: edit dialog created")
            page.dialog = dialog
            dialog.open = True
            print("DEBUG: edit dialog opened")
            page.update()

            # Inline fallback for edit dialog (in case AlertDialog actions are not delivered)
            accept_btn = ft.ElevatedButton("Принять")
            cancel_btn = ft.TextButton("Отмена")

            def _remove_inline():
                try:
                    content_column.controls.remove(inline_panel)
                except Exception:
                    pass
                page.update()

            def _inline_accept(ev):
                print(f"DEBUG: inline edit accept for {goal.get('name')}")
                _remove_inline()
                try:
                    save_edit(ev)
                except Exception as ex:
                    print("DEBUG: error in save_edit from inline:", ex)

            def _inline_cancel(ev):
                print(f"DEBUG: inline edit cancel for {goal.get('name')}")
                _remove_inline()
                try:
                    setattr(dialog, "open", False)
                    page.update()
                except Exception as ex:
                    print("DEBUG: error closing dialog from inline:", ex)

            accept_btn.on_click = _inline_accept
            cancel_btn.on_click = _inline_cancel

            inline_panel = ft.Container(
                content=ft.Column([
                    name_input,
                    *( [weight_input] if weight_input is not None else [] ),
                    ft.Row([deadline_input, deadline_btn], spacing=12),
                    ft.Row([accept_btn, cancel_btn], spacing=12),
                ], spacing=8),
                padding=12,
                border_radius=8,
                bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.BLUE_GREY_800),
            )

            content_column.controls.append(inline_panel)
            page.update()

        def on_edit_click(e):
            open_edit_goal_dialog(goal_data)

        edit_btn = ft.IconButton(
            icon=ft.Icons.EDIT,
            tooltip="Редактировать цель",
            on_click=lambda e: open_edit_goal_dialog(goal_data),
        )

        delete_btn = ft.IconButton(
            icon=ft.Icons.DELETE,
            tooltip="Удалить цель",
            on_click=delete_goal,
        )

        checkbox = ft.Checkbox(
            value=goal_data.get("completed", False),
            on_change=toggle_completed
        )

        left_column_controls = [ft.Text(goal_data["name"], size=16)]
        if "weight" in goal_data:
            left_column_controls.append(
                ft.Text(f"Вес: {goal_data['weight']:.2f}", size=12, color=ft.Colors.CYAN_200)
            )
        if goal_data.get("deadline"):
            now = datetime.now()
            days_left = (goal_data["deadline"] - now).days
            if days_left < 0:
                color = ft.Colors.RED_400
            elif days_left <= 3:
                color = ft.Colors.ORANGE_400
            else:
                color = ft.Colors.GREEN_400

            left_column_controls.append(
                ft.Text(
                    f"Дедлайн: {goal_data['deadline'].strftime('%d.%m.%Y %H:%M')}",
                    size=12,
                    color=color
                )
            )

        left_column = ft.GestureDetector(
            content=ft.Column(left_column_controls, expand=True),
            on_tap=open_goal
        )

        progress = calculate_progress(goal_data)
        progress_bar = ft.ProgressBar(value=progress, height=8, color=ft.Colors.GREEN_400)
        goal_data["progress_bar"] = progress_bar
        progress_label = ft.Text(f"Выполнено: {int(progress*100)}%", size=12, color=ft.Colors.GREY_400)
        goal_data["progress_label"] = progress_label

        return ft.Container(
            padding=16,
            border_radius=12,
            bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.BLUE_GREY_800),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(left_column, expand=True),
                            checkbox,
                            edit_btn,
                            delete_btn,
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                    progress_bar,
                    progress_label,
                ],
                spacing=6,
            )
        )

    def go_back(e):
        async def transition():
            nonlocal current_goal
            content_container.opacity = 0
            page.update()
            await asyncio.sleep(0.25)

            current_goal = navigation_stack.pop()
            render_view()
            page.update()

            await asyncio.sleep(0.05)
            content_container.opacity = 1
            page.update()

        page.run_task(transition)

    progress_text = ft.Text("Прогресс: 0 из 0", size=14, color=ft.Colors.GREY_300)

    def update_progress():
        total = len(goals)
        completed = sum(1 for g in goals if calculate_progress(g) >= 0.999)
        progress_text.value = f"Прогресс: {completed} из {total}"
        page.update()

    def calculate_progress(goal):
        subgoals = goal.get("subgoals", [])

        if subgoals:
            total = 0.0
            for s in subgoals:
                w = max(0.01, s.get("weight", 1.0))
                total += calculate_progress(s) * w
            return min(total, 1.0)

        return 1.0 if goal.get("completed", False) else 0.0

    def recalc_all_progress():
        def update_goal(goal):
            progress = calculate_progress(goal)

            if "progress_bar" in goal:
                goal["progress_bar"].value = progress
                goal["progress_bar"].color = ft.Colors.GREEN_400

            if "progress_label" in goal:
                goal["progress_label"].value = f"Выполнено: {int(progress * 100)}%"

            for s in goal.get("subgoals", []):
                update_goal(s)

        for g in goals:
            update_goal(g)

        update_progress()
        page.update()

    def normalize_weights(subs):
        if not subs:
            return
        total = 0.0
        for s in subs:
            w = max(0.01, float(s.get("weight", 1.0)))
            total += w
        if total == 0:
            # distribute equally
            n = len(subs)
            for s in subs:
                s["weight"] = 1.0 / n
            return
        for s in subs:
            w = max(0.01, float(s.get("weight", 1.0)))
            s["weight"] = w / total

    def find_parent(target, nodes=None):
        if nodes is None:
            nodes = goals
        for g in nodes:
            subs = g.get("subgoals", [])
            if target in subs:
                return g
            parent = find_parent(target, subs)
            if parent:
                return parent
        return None

    new_goal_input = ft.TextField(
        hint_text="Введите название большой цели...",
        autofocus=True,
        expand=True,
        border_radius=12,
        height=48,
        on_submit=lambda e: add_new_goal(e),
    )

    new_subgoal_input = ft.TextField(
        hint_text="Введите подцель...",
        expand=True,
        border_radius=12,
        height=48,
    )

    add_subgoal_btn = ft.ElevatedButton(
        "Добавить подцель",
        icon=ft.Icons.ADD,
        height=48,
    )

    def add_subgoal(e):
        try:
            print("DEBUG: add_subgoal clicked")
            print(f"DEBUG: current_goal is {current_goal.get('name') if current_goal else None}")
        except Exception as ex:
            print("DEBUG: error printing current_goal:", ex)

        text = new_subgoal_input.value.strip()
        if not text or current_goal is None:
            return

        selected_subgoal_deadline = None

        sub_deadline_input = ft.TextField(
            value="Не установлен",
            read_only=True,
            expand=True,
        )

        def handle_subgoal_deadline_change(ev):
            nonlocal selected_subgoal_deadline
            selected_subgoal_deadline = ev.control.value
            if selected_subgoal_deadline:
                sub_deadline_input.value = selected_subgoal_deadline.strftime("%d.%m.%Y %H:%M")
            else:
                sub_deadline_input.value = "Не установлен"
            page.update()

        deadline_btn = ft.ElevatedButton(
            text="Выбрать дедлайн",
            icon=ft.Icons.CALENDAR_MONTH,
            on_click=lambda ev: page.open(
                ft.CupertinoBottomSheet(
                    ft.CupertinoDatePicker(
                        date_picker_mode=ft.CupertinoDatePickerMode.DATE_AND_TIME,
                        on_change=handle_subgoal_deadline_change,
                    ),
                    height=216,
                    padding=ft.padding.only(top=6),
                )
            ),
        )

        add_btn = ft.ElevatedButton("Добавить")
        cancel_btn = ft.TextButton("Отмена")

        def _on_dialog_add(ev):
            print(f"DEBUG: dialog add button clicked (text='{text}')")
            add_subgoal_to_goal(dialog, text, selected_subgoal_deadline)

        def _on_dialog_cancel(ev):
            setattr(dialog, "open", False)
            page.update()

        add_btn.on_click = _on_dialog_add
        print("DEBUG: add_btn.on_click assigned")
        cancel_btn.on_click = _on_dialog_cancel
        print("DEBUG: cancel_btn.on_click assigned")

        dialog = ft.AlertDialog(
            title=ft.Text("Создать подцель"),
            content=ft.Column([
                ft.Text(text),
                ft.Row([sub_deadline_input, deadline_btn], spacing=12),
            ], spacing=12),
            actions=[add_btn, cancel_btn],
        )

        print("DEBUG: subgoal dialog created")
        page.dialog = dialog
        dialog.open = True
        print("DEBUG: subgoal dialog opened")
        page.update()

        # Inline fallback: also render a temporary inline panel in case dialog actions aren't delivered
        inline_panel = ft.Container(
            content=ft.Column([
                ft.Text(f"Добавить подцель: {text}"),
                ft.Row([sub_deadline_input, deadline_btn], spacing=12),
                ft.Row([add_btn, cancel_btn], spacing=12),
            ], spacing=8),
            padding=12,
            border_radius=8,
            bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.BLUE_GREY_800),
        )

        # Append inline panel and provide handlers to remove it on cancel/add
        content_column.controls.append(inline_panel)
        page.update()

        def _remove_inline_panel():
            try:
                content_column.controls.remove(inline_panel)
            except Exception:
                pass
            page.update()

        # wrap existing handlers to also remove inline panel
        old_add = add_btn.on_click

        def _inline_add_wrap(ev):
            print("DEBUG: inline add clicked")
            _remove_inline_panel()
            # call original
            try:
                old_add(ev)
            except Exception as ex:
                print("DEBUG: error in old_add:", ex)

        add_btn.on_click = _inline_add_wrap

        old_cancel = cancel_btn.on_click

        def _inline_cancel_wrap(ev):
            print("DEBUG: inline cancel clicked")
            _remove_inline_panel()
            try:
                old_cancel(ev)
            except Exception as ex:
                print("DEBUG: error in old_cancel:", ex)

        cancel_btn.on_click = _inline_cancel_wrap

    def add_subgoal_to_goal(dialog, text, selected_subgoal_deadline):
        try:
            print(f"DEBUG: add_subgoal_to_goal: adding '{text}' to {current_goal.get('name') if current_goal else None}")
        except Exception:
            print("DEBUG: add_subgoal_to_goal: current_goal is None")

        current_goal.setdefault("subgoals", []).append(
            {
                "name": text,
                "completed": False,
                "deadline": selected_subgoal_deadline,
                "subgoals": [],
                "weight": 1.0,
            }
        )
        normalize_weights(current_goal["subgoals"])
        # close dialog if provided (None when using inline fallback)
        try:
            if dialog:
                dialog.open = False
        except Exception:
            pass
        new_subgoal_input.value = ""
        render_view()
        recalc_all_progress()
        page.update()

    add_subgoal_btn.on_click = add_subgoal

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
        content=content_container,
        bgcolor=ft.Colors.BLACK12,
        expand=True,
        padding=20,
    )

    page.add(main_container)
    render_view()
    recalc_all_progress()


ft.app(target=main)