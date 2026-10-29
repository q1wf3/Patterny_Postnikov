import tkinter as tk
from tkinter import messagebox
from abc import ABC, abstractmethod
import hashlib
import json
import os


def hash_sequence(sequence):
    seq_str = "".join(map(str, sequence))
    return hashlib.sha256(seq_str.encode('utf-8')).hexdigest()


def validate_sequence(sequence):
    if not isinstance(sequence, list):
        return False, "Последовательность должна быть списком."
    if len(sequence) < 4:
        return False, "Слишком короткая: минимум 4 ячейки."
    if len(sequence) > 9:
        return False, "Слишком длинная: максимум 9 ячеек."
    if len(set(sequence)) != len(sequence):
        return False, "Есть повторяющиеся ячейки."
    if not all(isinstance(x, int) and 1 <= x <= 9 for x in sequence):
        return False, "Ячейка вне диапазона 1–9."
    return True, ""


def rounded_rect(canvas, x1, y1, x2, y2, r=10, **kwargs):
    points = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


class RoundedButton(tk.Canvas):
    def __init__(self, parent, text="", command=None, width=220, height=44,
                 radius=10, bg="#4a4a4a", fg="white",
                 hover_bg="#5a5a5a", active_bg="#7a7a7a",
                 font=("Segoe UI", 11), parent_bg="#2b2b2b"):
        super().__init__(parent, width=width, height=height,
                         bg=parent_bg, highlightthickness=0, bd=0)
        self.command = command
        self.radius = radius
        self.font = font
        self.text = text
        self.color_normal = bg
        self.color_hover = hover_bg
        self.color_active = active_bg
        self.color_fg = fg
        self._current_bg = bg
        self._width = width
        self._height = height
        self._draw()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _draw(self):
        self.delete("all")
        rounded_rect(self, 0, 0, self._width, self._height, r=self.radius,
                     fill=self._current_bg, outline="")
        self.create_text(self._width / 2, self._height / 2, text=self.text,
                         fill=self.color_fg, font=self.font)

    def _on_enter(self, _):
        self._current_bg = self.color_hover
        self._draw()

    def _on_leave(self, _):
        self._current_bg = self.color_normal
        self._draw()

    def _on_press(self, _):
        self._current_bg = self.color_active
        self._draw()

    def _on_release(self, _):
        self._current_bg = self.color_hover
        self._draw()
        if self.command:
            self.command()

    def set_text(self, text):
        self.text = text
        self._draw()

    def set_colors(self, bg, hover=None, active=None):
        self.color_normal = bg
        self.color_hover = hover or bg
        self.color_active = active or bg
        self._current_bg = bg
        self._draw()


class SequenceMemento:
    def __init__(self, selected, mode):
        self._selected = list(selected)
        self._mode = mode

    def get_state(self):
        return list(self._selected), self._mode


class SequenceCaretaker:
    def __init__(self):
        self._history = []

    def save(self, memento):
        self._history.append(memento)

    def undo(self):
        if len(self._history) > 1:
            self._history.pop()
            return self._history[-1]
        if len(self._history) == 1:
            return self._history[0]
        return None

    def current(self):
        if not self._history:
            return None
        return self._history[-1]

    def clear(self):
        self._history.clear()

    def count(self):
        return len(self._history)


class UIMediator:
    def __init__(self):
        self.components = {}
        self.app = None

    def register(self, name, component):
        self.components[name] = component

    def set_app(self, app):
        self.app = app

    def get(self, name):
        return self.components.get(name)

    def notify(self, sender, event, data=None):
        if event == "cell_clicked":
            self._handle_cell_clicked(data)
        elif event == "mode_changed":
            self._handle_mode_changed(data)
        elif event == "clear":
            self._handle_clear()
        elif event == "primary_action":
            self._handle_primary_action()
        elif event == "undo":
            self._handle_undo()
        elif event == "pattern_clicked":
            self._handle_pattern_clicked(data)
        elif event == "reset_password":
            self._handle_reset_password()

    def _handle_cell_clicked(self, number):
        if self.app is None:
            return
        if number in self.app.selected:
            self._set_status("Эта ячейка уже выбрана.", "#ffaa00")
            return
        if len(self.app.selected) >= 9:
            self._set_status("Максимальная длина — 9.", "#ffaa00")
            return
        self.app.selected.append(number)
        self._save_state()
        self._refresh_all()

    def _handle_mode_changed(self, mode):
        if self.app is None:
            return
        self.app.mode = mode
        self.app.selected = []
        self._save_state()
        self._refresh_all()

    def _handle_clear(self):
        if self.app is None:
            return
        self.app.selected = []
        self._save_state()
        self._refresh_all()
        self._set_status("", "#ffffff")

    def _handle_primary_action(self):
        if self.app is None:
            return
        if self.app.mode == "login":
            self.app.login()
        else:
            self.app.create_password()

    def _handle_undo(self):
        if self.app is None:
            return
        memento = self.app.caretaker.undo()
        if memento is None:
            self._set_status("Нечего отменять.", "#ffaa00")
            return
        selected, mode = memento.get_state()
        self.app.selected = selected
        self.app.mode = mode
        self._refresh_all()
        self._set_status("Действие отменено.", "#4a90d9")

    def _handle_pattern_clicked(self, pattern):
        if self.app is None:
            return
        self.app.selected = list(pattern.sequence)
        self._save_state()
        self._refresh_all()
        self._set_status(f"Применён шаблон: {pattern.name}", "#4a90d9")

    def _handle_reset_password(self):
        if self.app is None:
            return
        if not self.app.password_manager.has_password():
            self._set_status("Пароль не установлен.", "#ffaa00")
            return
        if messagebox.askyesno("Подтверждение",
                               "Удалить сохранённый графический пароль?"):
            self.app.password_manager.reset_password()
            messagebox.showinfo("Успех", "Пароль удалён.")
            self._set_status("Пароль удалён.", "#4a90d9")

    def _save_state(self):
        memento = SequenceMemento(self.app.selected, self.app.mode)
        self.app.caretaker.save(memento)

    def _refresh_all(self):
        grid = self.get("grid")
        seq_label = self.get("sequence_label")
        login_btn = self.get("login_mode_btn")
        create_btn = self.get("create_mode_btn")
        primary_btn = self.get("primary_btn")

        if grid is not None:
            grid.refresh(self.app.selected)

        if seq_label is not None:
            seq_str = " → ".join(map(str, self.app.selected))
            seq_label.config(text=seq_str)

        if self.app.mode == "login":
            if primary_btn is not None:
                primary_btn.set_text("Войти")
            if login_btn is not None:
                login_btn.set_colors("#6a6a6a", "#7a7a7a", "#8a8a8a")
            if create_btn is not None:
                create_btn.set_colors("#4a4a4a", "#5a5a5a", "#6a6a6a")
        else:
            if primary_btn is not None:
                primary_btn.set_text("Сохранить пароль")
            if login_btn is not None:
                login_btn.set_colors("#4a4a4a", "#5a5a5a", "#6a6a6a")
            if create_btn is not None:
                create_btn.set_colors("#6a6a6a", "#7a7a7a", "#8a8a8a")

    def _set_status(self, text, color):
        status = self.get("status_label")
        if status is not None:
            status.config(text=text, fg=color)


class GridComponent(tk.Canvas):
    def __init__(self, parent, mediator, parent_bg="#2b2b2b"):
        super().__init__(parent, width=280, height=280,
                         bg=parent_bg, highlightthickness=0)
        self.mediator = mediator
        self.parent_bg = parent_bg
        self.button_coords = {}
        self.cell_rects = {}
        self._draw_buttons()

    def _draw_buttons(self):
        self.delete("all")
        self.button_coords = {}
        self.cell_rects = {}

        start_x, start_y = 25, 25
        step = 80
        size = 60

        for i in range(1, 10):
            row = (i - 1) // 3
            col = (i - 1) % 3
            x1 = start_x + col * step
            y1 = start_y + row * step
            x2 = x1 + size
            y2 = y1 + size
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2

            self.button_coords[i] = (cx, cy)

            rect = rounded_rect(self, x1, y1, x2, y2, r=12,
                                 fill="#4a4a4a", outline="")
            self.create_text(cx, cy, text=str(i),
                             fill="white",
                             font=("Segoe UI", 18, "bold"))

            self.cell_rects[i] = rect

            tag = f"btn_{i}"
            self.itemconfig(rect, tags=(tag,))
            self.tag_bind(tag, "<Button-1>",
                          lambda e, num=i: self.mediator.notify(self, "cell_clicked", num))

    def refresh(self, selected):
        for i, rect_id in self.cell_rects.items():
            color = "#6a6a6a" if i in selected else "#4a4a4a"
            self.itemconfig(rect_id, fill=color)


class PasswordPattern:
    def __init__(self, name, sequence):
        self.name = name
        self.sequence = sequence


class PasswordManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.password_hash = None
        self.filename = "graphical_password.json"
        self._load()

    def _load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.password_hash = data.get("password_hash")
            except (json.JSONDecodeError, FileNotFoundError):
                self.password_hash = None
        else:
            self.password_hash = None

    def _save(self):
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump({"password_hash": self.password_hash}, f,
                      ensure_ascii=False, indent=4)

    def has_password(self):
        return self.password_hash is not None

    def create_password(self, sequence):
        self.password_hash = hash_sequence(sequence)
        self._save()
        return True

    def verify_password(self, sequence):
        if not self.has_password():
            return False
        return hash_sequence(sequence) == self.password_hash

    def reset_password(self):
        self.password_hash = None
        if os.path.exists(self.filename):
            os.remove(self.filename)


class AppWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Графический пароль — Посредник + Снимок")
        self.root.geometry("540x920")
        self.root.resizable(False, False)

        self.bg_color = "#2b2b2b"
        self.fg_color = "white"

        self.root.configure(bg=self.bg_color)

        self.mode = "login"
        self.selected = []
        self.password_manager = PasswordManager()

        self.caretaker = SequenceCaretaker()
        self.mediator = UIMediator()
        self.mediator.set_app(self)

        self.patterns = [
            PasswordPattern("Крест", [2, 5, 8, 4, 6]),
            PasswordPattern("Квадрат", [1, 2, 3, 6, 9, 8, 7, 4]),
            PasswordPattern("Зигзаг", [1, 2, 4, 3, 5, 7, 6, 8, 9]),
        ]

        self._build_ui()
        self.caretaker.save(SequenceMemento(self.selected, self.mode))

    def _build_ui(self):
        tk.Label(self.root, text="Графический пароль",
                 font=("Segoe UI", 16, "bold"),
                 bg=self.bg_color, fg=self.fg_color).pack(pady=(12, 6))

        grid_frame = tk.Frame(self.root, bg=self.bg_color)
        grid_frame.pack(pady=4)

        grid = GridComponent(grid_frame, self.mediator, parent_bg=self.bg_color)
        grid.pack()
        self.mediator.register("grid", grid)

        self.seq_label = tk.Label(self.root, text="", font=("Segoe UI", 13),
                                   bg=self.bg_color, fg=self.fg_color)
        self.seq_label.pack(pady=4)
        self.mediator.register("sequence_label", self.seq_label)

        primary_btn = RoundedButton(
            self.root, text="Войти",
            command=lambda: self.mediator.notify(self, "primary_action"),
            width=240, height=42, radius=12,
            bg="#4a90d9", fg="white",
            hover_bg="#357abd", active_bg="#2c6aa0",
            font=("Segoe UI", 12, "bold"), parent_bg=self.bg_color
        )
        primary_btn.pack(pady=3)
        self.mediator.register("primary_btn", primary_btn)

        clear_btn = RoundedButton(
            self.root, text="Очистить",
            command=lambda: self.mediator.notify(self, "clear"),
            width=240, height=42, radius=12,
            bg="#4a4a4a", fg="white",
            hover_bg="#5a5a5a", active_bg="#6a6a6a",
            font=("Segoe UI", 12), parent_bg=self.bg_color
        )
        clear_btn.pack(pady=3)

        undo_btn = RoundedButton(
            self.root, text="↶ Отменить (снимок)",
            command=lambda: self.mediator.notify(self, "undo"),
            width=240, height=40, radius=10,
            bg="#4a4a4a", fg="white",
            hover_bg="#5a5a5a", active_bg="#6a6a6a",
            font=("Segoe UI", 11), parent_bg=self.bg_color
        )
        undo_btn.pack(pady=3)

        mode_frame = tk.Frame(self.root, bg=self.bg_color)
        mode_frame.pack(pady=6)

        login_mode_btn = RoundedButton(
            mode_frame, text="Вход",
            command=lambda: self.mediator.notify(self, "mode_changed", "login"),
            width=140, height=38, radius=10,
            bg="#6a6a6a", fg="white",
            hover_bg="#7a7a7a", active_bg="#8a8a8a",
            font=("Segoe UI", 11), parent_bg=self.bg_color
        )
        login_mode_btn.pack(side=tk.LEFT, padx=4)
        self.mediator.register("login_mode_btn", login_mode_btn)

        create_mode_btn = RoundedButton(
            mode_frame, text="Создать пароль",
            command=lambda: self.mediator.notify(self, "mode_changed", "create"),
            width=160, height=38, radius=10,
            bg="#4a4a4a", fg="white",
            hover_bg="#5a5a5a", active_bg="#6a6a6a",
            font=("Segoe UI", 11), parent_bg=self.bg_color
        )
        create_mode_btn.pack(side=tk.LEFT, padx=4)
        self.mediator.register("create_mode_btn", create_mode_btn)

        tk.Label(self.root, text="Шаблоны:",
                 font=("Segoe UI", 11, "bold"),
                 bg=self.bg_color, fg=self.fg_color).pack(pady=(8, 2))

        cards_frame = tk.Frame(self.root, bg=self.bg_color)
        cards_frame.pack(pady=2)

        for i, pattern in enumerate(self.patterns):
            card = self._make_pattern_card(cards_frame, pattern)
            row = i // 2
            col = i % 2
            card.grid(row=row, column=col, padx=4, pady=3)

        reset_btn = RoundedButton(
            self.root, text="Сбросить сохранённый пароль",
            command=lambda: self.mediator.notify(self, "reset_password"),
            width=260, height=34, radius=10,
            bg="#3a3a3a", fg="#a0a0a0",
            hover_bg="#4a4a4a", active_bg="#5a5a5a",
            font=("Segoe UI", 10), parent_bg=self.bg_color
        )
        reset_btn.pack(pady=8)

        self.status_label = tk.Label(self.root, text="", font=("Segoe UI", 10),
                                      bg=self.bg_color, fg=self.fg_color,
                                      wraplength=480)
        self.status_label.pack(pady=3)
        self.mediator.register("status_label", self.status_label)

        history_label = tk.Label(
            self.root,
            text="История снимков: 1",
            font=("Segoe UI", 9),
            bg=self.bg_color, fg="#808080"
        )
        history_label.pack(pady=2)
        self.mediator.register("history_label", history_label)

    def _make_pattern_card(self, parent, pattern):
        card = tk.Canvas(parent, width=250, height=58,
                          bg=self.bg_color, highlightthickness=0, bd=0)
        rounded_rect(card, 0, 0, 250, 58, r=10,
                     fill="#4a4a4a", outline="", tags=("card",))
        card.create_text(15, 20, text=pattern.name, anchor="w",
                          fill="white", font=("Segoe UI", 11, "bold"),
                          tags=("card",))
        seq_str = " → ".join(map(str, pattern.sequence))
        card.create_text(15, 38, text=seq_str, anchor="w",
                          fill="#b0b0b0", font=("Segoe UI", 9),
                          tags=("card",))

        card.tag_bind("card", "<Button-1>",
                      lambda e, p=pattern: self.mediator.notify(self, "pattern_clicked", p))
        return card

    def create_password(self):
        if not self.selected:
            self.status_label.config(text="Выберите последовательность.", fg="#ffaa00")
            return
        ok, msg = validate_sequence(self.selected)
        if not ok:
            self.status_label.config(text=msg, fg="#ff4444")
            messagebox.showerror("Ошибка валидации", msg)
            return
        if self.password_manager.has_password():
            if not messagebox.askyesno("Подтверждение",
                                        "Пароль уже существует. Перезаписать?"):
                return
            self.password_manager.reset_password()
        self.password_manager.create_password(self.selected)
        messagebox.showinfo("Успех", "Графический пароль успешно создан.")
        self.mediator.notify(self, "clear")

    def login(self):
        if not self.password_manager.has_password():
            messagebox.showwarning("Внимание",
                                    "Пароль не создан. Сначала создайте пароль.")
            return
        if not self.selected:
            self.status_label.config(text="Введите последовательность.", fg="#ffaa00")
            return
        ok, msg = validate_sequence(self.selected)
        if not ok:
            self.status_label.config(text=msg, fg="#ff4444")
            messagebox.showerror("Ошибка валидации", msg)
            return
        if self.password_manager.verify_password(self.selected):
            messagebox.showinfo("Успех", "Пароль верный. Доступ разрешён.")
            self.mediator.notify(self, "clear")
        else:
            messagebox.showerror("Ошибка", "Пароль неверный. Доступ запрещён.")
            self.mediator.notify(self, "clear")


if __name__ == "__main__":
    root = tk.Tk()
    app = AppWindow(root)
    root.mainloop()