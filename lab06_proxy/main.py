import tkinter as tk
from tkinter import messagebox
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import hashlib
import json
import os


def validate_sequence(sequence):
    if not isinstance(sequence, list):
        return False
    if not (4 <= len(sequence) <= 9):
        return False
    if len(set(sequence)) != len(sequence):
        return False
    if not all(isinstance(x, int) and 1 <= x <= 9 for x in sequence):
        return False
    return True


def hash_sequence(sequence):
    seq_str = "".join(map(str, sequence))
    return hashlib.sha256(seq_str.encode('utf-8')).hexdigest()


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


class PasswordService(ABC):
    @abstractmethod
    def has_password(self):
        pass

    @abstractmethod
    def create_password(self, sequence):
        pass

    @abstractmethod
    def verify_password(self, sequence):
        pass

    @abstractmethod
    def reset_password(self):
        pass


class PasswordManager(PasswordService):
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
        if not validate_sequence(sequence):
            raise ValueError("Некорректная последовательность.")
        self.password_hash = hash_sequence(sequence)
        self._save()
        return True

    def verify_password(self, sequence):
        if not self.has_password():
            return False
        if not validate_sequence(sequence):
            return False
        return hash_sequence(sequence) == self.password_hash

    def reset_password(self):
        self.password_hash = None
        if os.path.exists(self.filename):
            os.remove(self.filename)


class PasswordManagerProxy(PasswordService):
    MAX_ATTEMPTS = 5
    BLOCK_SECONDS = 30

    def __init__(self):
        self._real_service = None
        self._log = []
        self._failed_attempts = 0
        self._blocked_until = None
        self._log_action("INFO", "Прокси создан (реальный сервис ещё не загружен)")

    def _get_service(self):
        if self._real_service is None:
            self._log_action("INFO", "Ленивая инициализация PasswordManager")
            self._real_service = PasswordManager()
        return self._real_service

    def _log_action(self, level, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._log.append((timestamp, level, message))

    def _is_blocked(self):
        if self._blocked_until is None:
            return False
        if datetime.now() < self._blocked_until:
            return True
        self._blocked_until = None
        self._failed_attempts = 0
        self._log_action("INFO", "Блокировка снята")
        return False

    def has_password(self):
        return self._get_service().has_password()

    def create_password(self, sequence):
        if self._is_blocked():
            self._log_action("BLOCK", "Создание заблокировано")
            return False, "Доступ временно заблокирован"
        if not validate_sequence(sequence):
            self._log_action("FAIL", "Некорректная последовательность")
            return False, "Некорректная последовательность. Длина от 4 до 9, без повторов."
        try:
            self._get_service().create_password(sequence)
            self._log_action("OK", "Пароль создан")
            self._failed_attempts = 0
            return True, "Графический пароль успешно создан."
        except ValueError as e:
            self._log_action("FAIL", f"Ошибка: {e}")
            return False, str(e)

    def verify_password(self, sequence):
        if self._is_blocked():
            remaining = int((self._blocked_until - datetime.now()).total_seconds())
            self._log_action("BLOCK", f"Вход при блокировке ({remaining} с)")
            return False, f"Доступ заблокирован на {remaining} секунд"
        if not validate_sequence(sequence):
            self._log_action("FAIL", "Некорректная последовательность")
            return False, "Некорректная последовательность."
        result = self._get_service().verify_password(sequence)
        if result:
            self._failed_attempts = 0
            self._log_action("OK", "Успешный вход")
            return True, "Пароль верный. Доступ разрешён."
        self._failed_attempts += 1
        self._log_action("FAIL", f"Неверный пароль (попытка {self._failed_attempts})")
        if self._failed_attempts >= self.MAX_ATTEMPTS:
            self._blocked_until = datetime.now() + timedelta(seconds=self.BLOCK_SECONDS)
            self._log_action("BLOCK", f"Блокировка на {self.BLOCK_SECONDS} с")
            return False, f"Слишком много неверных попыток. Блокировка на {self.BLOCK_SECONDS} секунд."
        return False, f"Пароль неверный. Попытка {self._failed_attempts}/{self.MAX_ATTEMPTS}."

    def reset_password(self):
        self._get_service().reset_password()
        self._failed_attempts = 0
        self._blocked_until = None
        self._log_action("INFO", "Пароль сброшен")

    def get_log(self):
        return list(self._log)

    def get_failed_attempts(self):
        return self._failed_attempts

    def clear_log(self):
        self._log.clear()


class AppWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Графический пароль — Заместитель")
        self.root.geometry("540x920")
        self.root.resizable(False, False)

        self.bg_color = "#2b2b2b"
        self.fg_color = "white"
        self.accent_color = "#4a90d9"

        self.root.configure(bg=self.bg_color)

        self.mode = "login"
        self.selected = []
        self.button_coords = {}
        self.cell_rects = {}
        self.canvas = None

        self.service = PasswordManagerProxy()

        self._build_ui()
        self._update_mode()

    def _build_ui(self):
        tk.Label(self.root, text="Графический пароль",
                 font=("Segoe UI", 16, "bold"),
                 bg=self.bg_color, fg=self.fg_color).pack(pady=(10, 5))

        self.canvas_frame = tk.Frame(self.root, bg=self.bg_color)
        self.canvas_frame.pack(pady=5)

        self.canvas = tk.Canvas(self.canvas_frame, width=320, height=320,
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
            width=240, height=44, radius=12,
            bg="#4a90d9", fg="white",
            hover_bg="#357abd", active_bg="#2c6aa0",
            font=("Segoe UI", 12, "bold"), parent_bg=self.bg_color
        )
        self.primary_btn.pack(pady=4)

        self.clear_btn = RoundedButton(
            self.root, text="Очистить", command=self._clear_selection,
            width=240, height=44, radius=12,
            bg="#4a4a4a", fg="white",
            hover_bg="#5a5a5a", active_bg="#6a6a6a",
            font=("Segoe UI", 12), parent_bg=self.bg_color
        )
        self.clear_btn.pack(pady=4)

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

        log_frame = tk.Frame(self.root, bg=self.bg_color)
        log_frame.pack(pady=10)

        self.log_btn = RoundedButton(
            log_frame, text="Показать лог прокси",
            command=self._show_log,
            width=200, height=38, radius=10,
            bg="#4a4a4a", fg="white",
            hover_bg="#5a5a5a", active_bg="#6a6a6a",
            font=("Segoe UI", 11), parent_bg=self.bg_color
        )
        self.log_btn.pack(side=tk.LEFT, padx=4)

        self.reset_btn = RoundedButton(
            self.root, text="Сбросить сохранённый пароль",
            command=self._reset_password,
            width=260, height=36, radius=10,
            bg="#3a3a3a", fg="#a0a0a0",
            hover_bg="#4a4a4a", active_bg="#5a5a5a",
            font=("Segoe UI", 10), parent_bg=self.bg_color
        )
        self.reset_btn.pack(pady=6)

        self.status_label = tk.Label(self.root, text="", font=("Segoe UI", 10),
                                      bg=self.bg_color, fg=self.fg_color)
        self.status_label.pack(pady=3)

    def _draw_grid_buttons(self):
        self.canvas.delete("all")
        self.button_coords = {}
        self.cell_rects = {}

        start_x, start_y = 35, 35
        step = 85
        size = 70

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
                                     font=("Segoe UI", 20, "bold"))

            self.cell_rects[i] = rect

            tag = f"btn_{i}"
            self.canvas.itemconfig(rect, tags=(tag,))
            self.canvas.tag_bind(tag, "<Button-1>",
                                  lambda e, num=i: self._select_cell(num))

    def _select_cell(self, num):
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
        self._update_attempts_label()

    def _update_attempts_label(self):
        failed = self.service.get_failed_attempts()
        if failed > 0:
            self.attempts_label.config(
                text=f"Неудачных попыток: {failed}/{self.service.MAX_ATTEMPTS}",
                fg="#ffaa00"
            )
        else:
            self.attempts_label.config(text="")

    def _clear_selection(self):
        self.selected = []
        self._update_ui()
        self.status_label.config(text="")

    def _set_mode(self, mode):
        self.mode = mode
        self._clear_selection()
        self._update_mode()

    def _update_mode(self):
        if self.mode == "login":
            self.primary_btn.set_text("Войти")
            self.login_mode_btn.set_colors("#6a6a6a", "#7a7a7a", "#8a8a8a")
            self.create_mode_btn.set_colors("#4a4a4a", "#5a5a5a", "#6a6a6a")
        else:
            self.primary_btn.set_text("Сохранить пароль")
            self.login_mode_btn.set_colors("#4a4a4a", "#5a5a5a", "#6a6a6a")
            self.create_mode_btn.set_colors("#6a6a6a", "#7a7a7a", "#8a8a8a")

    def _primary_action(self):
        if self.mode == "login":
            self._login()
        else:
            self._create_password()

    def _create_password(self):
        if not self.selected:
            self.status_label.config(text="Выберите последовательность.", fg="#ffaa00")
            return
        if self.service.has_password():
            if not messagebox.askyesno("Подтверждение",
                                        "Пароль уже существует. Перезаписать?"):
                return
            self.service.reset_password()
        result, message = self.service.create_password(self.selected)
        if result:
            messagebox.showinfo("Успех", message)
            self._clear_selection()
        else:
            self.status_label.config(text=message, fg="#ffaa00")

    def _login(self):
        if not self.selected:
            self.status_label.config(text="Введите последовательность.", fg="#ffaa00")
            return
        result, message = self.service.verify_password(self.selected)
        if result:
            messagebox.showinfo("Успех", message)
            self._clear_selection()
        else:
            messagebox.showerror("Ошибка", message)
            self._clear_selection()

    def _reset_password(self):
        if not self.service.has_password():
            self.status_label.config(text="Пароль не установлен.", fg="#ffaa00")
            return
        if messagebox.askyesno("Подтверждение",
                                "Удалить сохранённый графический пароль?"):
            self.service.reset_password()
            messagebox.showinfo("Успех", "Пароль удалён.")
            self._clear_selection()

    def _show_log(self):
        log = self.service.get_log()
        if not log:
            messagebox.showinfo("Лог прокси", "Лог пока пуст.")
            return
        lines = []
        for timestamp, level, message in log[-20:]:
            lines.append(f"[{timestamp}] {level}: {message}")
        text = "\n".join(lines)
        if len(log) > 20:
            text = f"...(показаны последние 20 из {len(log)})\n\n" + text
        messagebox.showinfo("Лог прокси", text)


if __name__ == "__main__":
    root = tk.Tk()
    app = AppWindow(root)
    root.mainloop()