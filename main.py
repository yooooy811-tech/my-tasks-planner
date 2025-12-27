import flet as ft
from datetime import datetime, timedelta
import asyncio
import json
import os
from pathlib import Path
import uuid
import time
import traceback


def main(page: ft.Page):
    current_goal = None
    navigation_stack = []

    page.title = "Мой Планировщик Целей"
    page.window.icon = os.path.abspath("iconforflet.ico")  # Если в подпапке: os.path.abspath("assets/icons/app_icon.ico")
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.AUTO

    goals = []

    # --- Persistence helpers ------------------------------------------------
    def get_data_dir():
        if os.name == 'nt':
            base = os.getenv('APPDATA') or str(Path.home())
        else:
            base = str(Path.home())
        d = Path(base) / ".my_tasks_planner"
        d.mkdir(parents=True, exist_ok=True)
        return d

    STATE_FILE = get_data_dir() / "state.json"

    def to_serializable(o):
        # Convert known simple types and recursively convert dicts/lists.
        if isinstance(o, dict):
            out = {}
            for k, v in o.items():
                # skip UI controls and callables
                try:
                    if isinstance(v, ft.Control) or callable(v):
                        continue
                except Exception:
                    pass
                out[k] = to_serializable(v)
            return out
        if isinstance(o, list):
            return [to_serializable(x) for x in o]
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, (str, int, float, bool)) or o is None:
            return o
        # fallback: for unsupported types, return string representation
        return str(o)

    def from_serializable(o):
        if isinstance(o, dict):
            out = {}
            for k, v in o.items():
                if isinstance(v, str) and k in ("deadline", "last_modified"):
                    try:
                        out[k] = datetime.fromisoformat(v)
                        continue
                    except Exception:
                        pass
                out[k] = from_serializable(v)
            return out
        if isinstance(o, list):
            return [from_serializable(x) for x in o]
        return o

    def load_state():
        if not STATE_FILE.exists():
            return []
        try:
            with STATE_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return from_serializable(data)
        except Exception as ex:
            print("DEBUG: load_state failed:", ex)
            traceback.print_exc()
            return []

    def save_state():
        try:
            tmp = STATE_FILE.with_suffix('.tmp')
            with tmp.open("w", encoding="utf-8") as f:
                json.dump(to_serializable(goals), f, ensure_ascii=False, indent=2)
            tmp.replace(STATE_FILE)
        except Exception as ex:
            print("DEBUG: save_state failed:", ex)
            traceback.print_exc()

    # load existing state (if any)
    _saved = load_state()
    if _saved:
        goals = _saved


        # --- Cloud sync with Supabase using Environment Variables ---------------
    # Теперь credentials берутся из переменных окружения:
    # SUPABASE_URL, SUPABASE_KEY, USER_ID
    # На Render.com задай их в Dashboard → Environment
    # Локально можно задать в терминале: export SUPABASE_URL="https://..." и т.д.
    class SyncClient:
        def __init__(self):
            self.enabled = False
            self.client = None
            self.user_id = os.environ.get('USER_ID', 'default')
            try:
                from supabase import create_client
                url = os.environ.get('SUPABASE_URL')
                key = os.environ.get('SUPABASE_KEY')
                if url and key:
                    self.client = create_client(url, key)
                    self.enabled = True
                    print("DEBUG: Supabase подключён через ENV")
                else:
                    print("DEBUG: Supabase ENV не заданы")
            except Exception as ex:
                print('DEBUG: Supabase не доступен:', ex)

        def push_state(self, user_id=None):
            if not self.enabled or not self.client:
                return False
            uid = user_id or self.user_id
            try:
                state = to_serializable(goals)
                self.client.table('user_states').upsert({
                    'user_id': uid,
                    'state': state,
                    'updated_at': datetime.now().isoformat()
                }).execute()
                return True
            except Exception as ex:
                print('DEBUG: push_state error:', ex)
                return False

        def pull_state(self, user_id=None):
            if not self.enabled or not self.client:
                return None
            uid = user_id or self.user_id
            try:
                r = self.client.table('user_states').select('state').eq('user_id', uid).execute()
                if r.data:
                    return from_serializable(r.data[0]['state'])
            except Exception as ex:
                print('DEBUG: pull_state error:', ex)
            return None

    sync_client = SyncClient()

    # UI sync controls
    sync_status = ft.Text('', size=12, color=ft.Colors.GREY_400)

    def do_sync(e):
        if not sync_client.enabled:
            sync_status.value = 'Синхронизация не настроена.\nЗадайте на Render.com переменные:\nSUPABASE_URL, SUPABASE_KEY, USER_ID'
            page.update()
            return

        sync_status.value = 'Синхронизация...'
        page.update()

        remote = sync_client.pull_state()
        if remote is not None:
            try:
                remote_latest = max((g.get('last_modified') for g in remote if g.get('last_modified')), default=None)
                local_latest = max((g.get('last_modified') for g in goals if g.get('last_modified')), default=None)

                if remote_latest and (not local_latest or remote_latest > local_latest):
                    goals.clear()
                    goals.extend(remote)
                    sync_status.value = 'Данные загружены из облака'
                else:
                    ok = sync_client.push_state()
                    sync_status.value = 'Данные отправлены в облако' if ok else 'Ошибка отправки'
            except Exception as ex:
                sync_status.value = f'Ошибка слияния: {ex}'
        else:
            ok = sync_client.push_state()
            sync_status.value = 'Данные отправлены в облако' if ok else 'Ошибка отправки'

        save_state()
        recalc_all_progress()
        render_view()
        content_container.opacity = 1.0
        page.update()

    sync_btn = ft.ElevatedButton('Синхронизировать', icon=ft.Icons.REFRESH, on_click=do_sync)

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
                ft.Row([sync_btn, sync_status], spacing=12),
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

        progress_val = calculate_progress(current_goal)
        # header progress bar + percent (store on current_goal for live updates)
        header_bar = ft.ProgressBar(value=progress_val, height=12, color=ft.Colors.GREEN_400, expand=True)
        header_label = ft.Text(f"{int(progress_val*100)}%", size=12, color=ft.Colors.GREY_400)
        current_goal["header_progress_bar"] = header_bar
        current_goal["header_progress_label"] = header_label
        content_column.controls.append(
            ft.Row([header_bar, ft.Container(width=12), header_label], vertical_alignment=ft.CrossAxisAlignment.CENTER)
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
            goal_data["last_modified"] = datetime.now()
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
                        # adjust and cap to keep siblings sum <= 1
                        assigned = adjust_weight_on_set(goal, w)
                        if assigned is None:
                            # fallback
                            goal["weight"] = max(0.01, min(1.0, w))
                        else:
                            goal["weight"] = assigned
                    except:
                        goal["weight"] = goal.get("weight", 1.0)
                # update deadline
                goal["deadline"] = selected_deadline
                # mark modified
                goal["last_modified"] = datetime.now()
                # normalize weights among siblings if this is a subgoal
                parent = find_parent(goal)
                if parent and parent.get("subgoals"):
                        # if parent uses automatic equal weights, redistribute
                        normalize_weights_in_parent(parent)
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

        # update header progress for currently opened goal (if any)
        if current_goal is not None:
            try:
                hp = calculate_progress(current_goal)
                if "header_progress_bar" in current_goal:
                    current_goal["header_progress_bar"].value = hp
                if "header_progress_label" in current_goal:
                    current_goal["header_progress_label"].value = f"{int(hp*100)}%"
            except Exception:
                pass

        update_progress()
        # persist state on every recalculation
        try:
            save_state()
        except Exception:
            pass
        page.update()

    def normalize_weights(subs):
        # Legacy compatibility: keep equal distribution behavior if no parent provided
        if not subs:
            return
        # If parent is provided and has manual_weights flag, do nothing here
        total = 0.0
        for s in subs:
            w = float(s.get("weight", 1.0))
            total += w
        # If total is <= 0, distribute equally
        if total <= 0:
            n = len(subs)
            for s in subs:
                s["weight"] = 1.0 / n
            return
        # normalize existing weights to sum to 1.0
        for s in subs:
            w = float(s.get("weight", 1.0))
            s["weight"] = w / total

    def normalize_weights_in_parent(parent):
        """Normalize weights among parent's subgoals equally if parent.manual_weights is False.
        If manual_weights is True, do not change existing weights.
        """
        subs = parent.get("subgoals", [])
        if not subs:
            return
        if parent.get("manual_weights", False):
            # do not redistribute automatically
            return
        # distribute equally
        n = len(subs)
        if n == 0:
            return
        equal = 1.0 / n
        for s in subs:
            s["weight"] = equal

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

    def adjust_weight_on_set(goal, new_weight):
        """Set goal weight capped so siblings sum <= 1. Marks parent.manual_weights = True."""
        parent = find_parent(goal)
        if parent is None:
            # top-level goal: ignore weight
            return None
        subs = parent.get("subgoals", [])
        total_other = 0.0
        for s in subs:
            if s is goal:
                continue
            total_other += float(s.get("weight", 0.0))
        allowed = max(0.0, 1.0 - total_other)
        assigned = min(max(0.0, float(new_weight)), allowed)
        goal["weight"] = assigned
        parent["manual_weights"] = True
        return assigned

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
        # Inline creation panel: name, optional weight, optional deadline
        try:
            print("DEBUG: add_subgoal clicked")
            print(f"DEBUG: current_goal is {current_goal.get('name') if current_goal else None}")
        except Exception as ex:
            print("DEBUG: error printing current_goal:", ex)

        text = new_subgoal_input.value.strip()
        if not text or current_goal is None:
            return

        selected_subgoal_deadline = None

        sub_name_input = ft.TextField(value=text, expand=True)
        weight_input = ft.TextField(hint_text="Вес (опционально)", keyboard_type=ft.KeyboardType.NUMBER)

        sub_deadline_input = ft.TextField(value="Не установлен", read_only=True, expand=True)

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

        def _final_add(ev):
            nm = sub_name_input.value.strip() or text
            w = None
            try:
                if weight_input.value.strip():
                    w = float(weight_input.value)
            except Exception:
                w = None
            add_subgoal_to_goal(None, nm, selected_subgoal_deadline, w)

        def _cancel(ev):
            try:
                content_column.controls.remove(inline_panel)
            except Exception:
                pass
            page.update()

        add_btn_inline = ft.ElevatedButton("Добавить", on_click=_final_add)
        cancel_btn_inline = ft.TextButton("Отмена", on_click=_cancel)

        inline_panel = ft.Container(
            content=ft.Column([
                sub_name_input,
                weight_input,
                ft.Row([sub_deadline_input, deadline_btn], spacing=12),
                ft.Row([add_btn_inline, cancel_btn_inline], spacing=12),
            ], spacing=8),
            padding=12,
            border_radius=8,
            bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.BLUE_GREY_800),
        )

        content_column.controls.append(inline_panel)
        page.update()
        new_subgoal_input.value = ""
        # focus the inline input (safer) and fall back to top-level input on error
        try:
            sub_name_input.focus()
        except Exception:
            try:
                new_subgoal_input.focus()
            except Exception:
                pass

    def add_subgoal_to_goal(dialog, text, selected_subgoal_deadline, weight=None):
        try:
            print(f"DEBUG: add_subgoal_to_goal: adding '{text}' to {current_goal.get('name') if current_goal else None}")
        except Exception:
            print("DEBUG: add_subgoal_to_goal: current_goal is None")

        parent = current_goal
        subs = parent.setdefault("subgoals", [])
        # if user specified a weight on creation, apply it (cap by siblings)
        if weight is not None:
            # append with provisional 0 then adjust
            new = {"id": uuid.uuid4().hex, "name": text, "completed": False, "deadline": selected_subgoal_deadline, "subgoals": [], "weight": 0.0, "last_modified": datetime.now()}
            subs.append(new)
            assigned = adjust_weight_on_set(new, weight)
            # if assigned was 0 and parent was manual, it's allowed
        else:
            # decide initial weight
            if parent.get("manual_weights", False):
                # give remaining weight to new subgoal (could be 0)
                remaining = max(0.0, 1.0 - sum(float(s.get("weight", 0.0)) for s in subs))
                w = remaining
                subs.append({
                    "id": uuid.uuid4().hex,
                    "name": text,
                    "completed": False,
                    "deadline": selected_subgoal_deadline,
                    "subgoals": [],
                    "weight": w,
                    "last_modified": datetime.now(),
                })
            else:
                # automatic equal redistribution among all subgoals
                subs.append({
                    "id": uuid.uuid4().hex,
                    "name": text,
                    "completed": False,
                    "deadline": selected_subgoal_deadline,
                    "subgoals": [],
                    "weight": 0.0,
                    "last_modified": datetime.now(),
                })
                normalize_weights_in_parent(parent)

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
                "id": uuid.uuid4().hex,
                "name": text,
                "completed": False,
                "deadline": selected_deadline,
                "subgoals": [],
                "manual_weights": False,
                "last_modified": datetime.now(),
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


if __name__ == "__main__":
    is_web = os.environ.get("PORT") is not None

    if is_web:
        # Render / iPhone (web)
        ft.app(
            target=main,
            view=ft.WEB_BROWSER,
            host="0.0.0.0",
            port=int(os.environ["PORT"]),
        )
    else:
        # ПК / ноут (desktop)
        ft.app(
            target=main,
            view=ft.FLET_APP,
        )