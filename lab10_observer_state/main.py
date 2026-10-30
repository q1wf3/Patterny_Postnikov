import tkinter as tk
from tkinter import messagebox
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
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


class StateObserver(ABC):
    @abstractmethod
    def on_state_changed(self, event, info=None):
        pass


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
        self._observers = []
        self._load()

    def subscribe(self, observer):
        if observer not in self._observers:
            self._observers.append(observer)

    def unsubscribe(self, observer):
        if observer in self._observers:
            self._observers.remove(observer)

    def _notify(self, event, info=None):
        for observer in list(self._observers):
            observer.on_state_changed(event, info)

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
        self._notify("password_created", sequence)

    def verify_password(self, sequence):
        if not self.has_password():
            return False
        return hash_sequence(sequence) == self.password_hash

    def reset_password(self):
        self.password_hash = None
        if os.path.exists(self.filename):
            os.remove(self.filename)
        self._notify("password_reset")


class AppState(ABC):
    @abstractmethod
    def get_name(self):
        pass

    @abstractmethod
    def get_color(self):
        pass

    @abstractmethod
    def can_login(self):
        pass

    @abstractmethod
    def can_create(self):
        pass

    @abstractmethod
    def get_primary_text(self, mode):
        pass

    @abstractmethod
    def get_status_text(self):
        pass


class NoPasswordState(AppState):
    def get_name(self):
        return "Нет пароля"

    def get_color(self):
        return "#ffaa00"

    def can_login(self):
        return False

    def can_create(self):
        return True

    def get_primary_text(self, mode):
        return "Создать пароль"

    def get_status_text(self):
        return "Пароль не установлен. Сначала создайте пароль."


class PasswordSetState(AppState):
    def get_name(self):
        return "Пароль установлен"

    def get_color(self):
        return "#4caf50"

    def can_login(self):
        return True

    def can_create(self):
        return True

    def get_primary_text(self, mode):
        if mode == "login":
            return "Войти"
        return "Сохранить пароль"

    def get_status_text(self):
        return "Пароль установлен. Можно войти или перезаписать."


class BlockedState(AppState):
    def __init__(self, until_time):
        self.until_time = until_time

    def get_name(self):
        return "Заблокировано"

    def get_color(self):
        return "#ff4444"

    def can_login(self):
        return False

    def can_create(self):
        return False

    def get_primary_text(self, mode):
        remaining = max(0, int((self.until_time - datetime.now()).total_seconds()))
        return f"Заблокировано ({remaining} с)"

    def get_status_text(self):
        remaining = max(0, int((self.until_time - datetime.now()).total_seconds()))
        return f"Слишком много неверных попыток. Подождите {remaining} с."


class AppWindow(StateObserver):
    MAX_ATTEMPTS = 5
    BLOCK_SECONDS = 30

    def __init__(self, root):
        self.root = root
        self.root.title("Графический пароль — Наблюдатель + Состояние")
        self.root.geometry("540x920")
        self.root.resizable(False, False)

        self.bg_color = "#2b2b2b"
        self.fg_color = "white"

        self.root.configure(bg=self.bg_color)

        self.mode = "login"
        self.selected = []
        self.button_coords = {}
        self.cell_rects = {}
        self.canvas = None

        self.password_manager = PasswordManager()
        self.password_manager.subscribe(self)

        self.failed_attempts = 0

        if not self.password_manager.has_password():
            self.state = NoPasswordState()
        else:
            self.state = PasswordSetState()

        self._build_ui()
        self._update_view()

    def on_state_changed(self, event, info=None):
        if event == "password_created":
            self.state = PasswordSetState()
            self.failed_attempts = 0
        elif event == "password_reset":
            self.state = NoPasswordState()
            self.failed_attempts = 0
        self._update_view()

    def _build_ui(self):
        tk.Label(self.root, text="Графический пароль",
                 font=("Segoe UI", 16, "bold"),
                 bg=self.bg_color, fg=self.fg_color).pack(pady=(12, 4))

        self.state_badge = tk.Label(
            self.root,
            text="",
            font=("Segoe UI", 10, "bold"),
            bg=self.bg_color, fg="#4caf50"
        )
        self.state_badge.pack(pady=2)

        self.canvas_frame = tk.Frame(self.root, bg=self.bg_color)
        self.canvas_frame.pack(pady=4)

        self.canvas = tk.Canvas(self.canvas_frame, width=280, height=280,
                                 bg=self.bg_color, highlightthickness=0)
        self.canvas.pack()

        self._draw_grid_buttons()

        self.seq_label = tk.Label(self.root, text="", font=("Segoe UI", 13),
                                   bg=self.bg_color, fg=self.fg_color)
        self.seq_label.pack(pady=4)

        self.attempts_label = tk.Label(self.root, text="", font=("Segoe UI", 9),
                                        bg=self.bg_color, fg="#a0a0a0")
        self.attempts_label.pack(pady=2)

        self.primary_btn = RoundedButton(
            self.root, text="Войти", command=self._primary_action,
            width=240, height=42, radius=12,
            bg="#4a90d9", fg="white",
            hover_bg="#357abd", active_bg="#2c6aa0",
            font=("Segoe UI", 12, "bold"), parent_bg=self.bg_color
        )
        self.primary_btn.pack(pady=3)

        self.clear_btn = RoundedButton(
            self.root, text="Очистить", command=self._clear_selection,
            width=240, height=42, radius=12,
            bg="#4a4a4a", fg="white",
            hover_bg="#5a5a5a", active_bg="#6a6a6a",
            font=("Segoe UI", 12), parent_bg=self.bg_color
        )
        self.clear_btn.pack(pady=3)

        mode_frame = tk.Frame(self.root, bg=self.bg_color)
        mode_frame.pack(pady=6)

        self.login_mode_btn = RoundedButton(
            mode_frame, text="Вход",
            command=lambda: self._set_mode("login"),
            width=140, height=38, radius=10,
            bg="#6a6a6a", fg="white",
            hover_bg="#7a7a7a", active_bg="#8a8a8a",
            font=("Segoe UI", 11), parent_bg=self.bg_color
        )
        self.login_mode_btn.pack(side=tk.LEFT, padx=4)

        self.create_mode_btn = RoundedButton(
            mode_frame, text="Создать пароль",
            command=lambda: self._set_mode("create"),
            width=160, height=38, radius=10,
            bg="#4a4a4a", fg="white",
            hover_bg="#5a5a5a", active_bg="#6a6a6a",
            font=("Segoe UI", 11), parent_bg=self.bg_color
        )
        self.create_mode_btn.pack(side=tk.LEFT, padx=4)

        self.reset_btn = RoundedButton(
            self.root, text="Сбросить сохранённый пароль",
            command=self._reset_password,
            width=260, height=36, radius=10,
            bg="#3a3a3a", fg="#a0a0a0",
            hover_bg="#4a4a4a", active_bg="#5a5a5a",
            font=("Segoe UI", 10), parent_bg=self.bg_color
        )
        self.reset_btn.pack(pady=10)

        self.status_label = tk.Label(self.root, text="", font=("Segoe UI", 10),
                                      bg=self.bg_color, fg=self.fg_color,
                                      wraplength=480)
        self.status_label.pack(pady=3)

    def _draw_grid_buttons(self):
        self.canvas.delete("all")
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

            rect = rounded_rect(self.canvas, x1, y1, x2, y2, r=12,
                                 fill="#4a4a4a", outline="")
            self.canvas.create_text(cx, cy, text=str(i),
                                     fill="white",
                                     font=("Segoe UI", 18, "bold"))

            self.cell_rects[i] = rect

            tag = f"btn_{i}"
            self.canvas.itemconfig(rect, tags=(tag,))
            self.canvas.tag_bind(tag, "<Button-1>",
                                  lambda e, num=i: self._select_cell(num))

    def _select_cell(self, num):
        if not self.state.can_login() and not self.state.can_create():
            self.status_label.config(text="Доступ заблокирован.", fg="#ff4444")
            return
        if num in self.selected:
            self.status_label.config(text="Эта ячейка уже выбрана.", fg="#ffaa00")
            return
        if len(self.selected) >= 9:
            self.status_label.config(text="Максимальная длина — 9.", fg="#ffaa00")
            return
        self.selected.append(num)
        self._update_ui()

    def _update_ui(self):
        for i, rect_id in self.cell_rects.items():
            color = "#6a6a6a" if i in self.selected else "#4a4a4a"
            self.canvas.itemconfig(rect_id, fill=color)
        seq_str = " → ".join(map(str, self.selected))
        self.seq_label.config(text=seq_str)
        self._update_view()

    def _update_view(self):
        self.state_badge.config(
            text=f"Состояние: {self.state.get_name()}",
            fg=self.state.get_color()
        )

        self.primary_btn.set_text(self.state.get_primary_text(self.mode))

        if self.state.can_login() or self.state.can_create():
            self.status_label.config(text=self.state.get_status_text(), fg="#808080")
        else:
            self.status_label.config(text=self.state.get_status_text(), fg="#ff4444")

        if self.failed_attempts > 0:
            self.attempts_label.config(
                text=f"Неудачных попыток: {self.failed_attempts}/{self.MAX_ATTEMPTS}",
                fg="#ffaa00"
            )
        else:
            self.attempts_label.config(text="")

        if self.mode == "login":
            self.login_mode_btn.set_colors("#6a6a6a", "#7a7a7a", "#8a8a8a")
            self.create_mode_btn.set_colors("#4a4a4a", "#5a5a5a", "#6a6a6a")
        else:
            self.login_mode_btn.set_colors("#4a4a4a", "#5a5a5a", "#6a6a6a")
            self.create_mode_btn.set_colors("#6a6a6a", "#7a7a7a", "#8a8a8a")

    def _clear_selection(self):
        self.selected = []
        self._update_ui()
        self._update_view()

    def _set_mode(self, mode):
        if not (self.state.can_login() or self.state.can_create()):
            self.status_label.config(text="Доступ заблокирован.", fg="#ff4444")
            return
        if mode == "login" and not self.state.can_login():
            self.status_label.config(text="Пароль не установлен — войти нельзя.", fg="#ffaa00")
            return
        if mode == "create" and not self.state.can_create():
            self.status_label.config(text="Создание пароля недоступно.", fg="#ffaa00")
            return
        self.mode = mode
        self.selected = []
        self._update_ui()
        self._update_view()

    def _primary_action(self):
        if isinstance(self.state, BlockedState):
            remaining = max(0, int((self.state.until_time - datetime.now()).total_seconds()))
            if remaining > 0:
                self.status_label.config(
                    text=f"Заблокировано ещё на {remaining} с.", fg="#ff4444"
                )
                return
            self.state = PasswordSetState() if self.password_manager.has_password() else NoPasswordState()

        if not self.password_manager.has_password():
            self._create_password()
            return
        if self.mode == "login":
            self._login()
        else:
            self._create_password()

    def _create_password(self):
        if not self.state.can_create():
            self.status_label.config(text="Создание пароля недоступно.", fg="#ff4444")
            return
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
        self.password_manager.create_password(self.selected)
        messagebox.showinfo("Успех", "Графический пароль успешно создан.")
        self._clear_selection()

    def _login(self):
        if not self.state.can_login():
            self.status_label.config(text="Вход недоступен.", fg="#ff4444")
            return
        if not self.selected:
            self.status_label.config(text="Введите последовательность.", fg="#ffaa00")
            return
        ok, msg = validate_sequence(self.selected)
        if not ok:
            self.status_label.config(text=msg, fg="#ff4444")
            return
        if self.password_manager.verify_password(self.selected):
            self.failed_attempts = 0
            self.state = PasswordSetState()
            messagebox.showinfo("Успех", "Пароль верный. Доступ разрешён.")
            self._clear_selection()
        else:
            self.failed_attempts += 1
            if self.failed_attempts >= self.MAX_ATTEMPTS:
                until = datetime.now() + timedelta(seconds=self.BLOCK_SECONDS)
                self.state = BlockedState(until)
                messagebox.showerror(
                    "Блокировка",
                    f"Слишком много неверных попыток. Блокировка на {self.BLOCK_SECONDS} секунд."
                )
            else:
                messagebox.showerror(
                    "Ошибка",
                    f"Пароль неверный. Попытка {self.failed_attempts}/{self.MAX_ATTEMPTS}."
                )
            self._clear_selection()

    def _reset_password(self):
        if not self.password_manager.has_password():
            self.status_label.config(text="Пароль не установлен.", fg="#ffaa00")
            return
        if messagebox.askyesno("Подтверждение",
                                "Удалить сохранённый графический пароль?"):
            self.password_manager.reset_password()
            messagebox.showinfo("Успех", "Пароль удалён.")
            self._clear_selection()


if __name__ == "__main__":
    root = tk.Tk()
    app = AppWindow(root)
    root.mainloop()