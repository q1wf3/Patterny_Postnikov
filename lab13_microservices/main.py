import tkinter as tk
from tkinter import messagebox
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import hashlib
import json
import os


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


class ServiceResult:
    def __init__(self, success, message, data=None):
        self.success = success
        self.message = message
        self.data = data

    def __repr__(self):
        return f"ServiceResult(success={self.success}, message={self.message})"


class PasswordService:
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

    def create(self, sequence):
        if self.has_password():
            return ServiceResult(False, "Пароль уже существует.")
        self.password_hash = hash_sequence(sequence)
        self._save()
        return ServiceResult(True, "Пароль сохранён.", self.password_hash)

    def verify(self, sequence):
        if not self.has_password():
            return ServiceResult(False, "Пароль не создан.")
        if hash_sequence(sequence) == self.password_hash:
            return ServiceResult(True, "Пароль верный. Доступ разрешён.")
        return ServiceResult(False, "Пароль неверный. Доступ запрещён.")

    def reset(self):
        self.password_hash = None
        if os.path.exists(self.filename):
            os.remove(self.filename)
        return ServiceResult(True, "Пароль удалён.")

    def status(self):
        return ServiceResult(True, "OK", {"has_password": self.has_password()})


class ValidatorService:
    def validate(self, sequence):
        ok, msg = validate_sequence(sequence)
        if ok:
            return ServiceResult(True, "Валидация пройдена.", sequence)
        return ServiceResult(False, msg)


class CircuitBreaker:
    def __init__(self, failure_threshold=3, recovery_time=10):
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self.failures = 0
        self.opened_at = None

    def is_open(self):
        if self.opened_at is None:
            return False
        if datetime.now() >= self.opened_at + timedelta(seconds=self.recovery_time):
            self.opened_at = None
            self.failures = 0
            return False
        return True

    def remaining(self):
        if self.opened_at is None:
            return 0
        delta = (self.opened_at + timedelta(seconds=self.recovery_time)) - datetime.now()
        return max(0, int(delta.total_seconds()))

    def record_success(self):
        self.failures = 0
        self.opened_at = None

    def record_failure(self):
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.opened_at = datetime.now()


class APIGateway:
    def __init__(self):
        self.password_service = PasswordService()
        self.validator_service = ValidatorService()
        self.breaker = CircuitBreaker(failure_threshold=3, recovery_time=10)
        self.request_log = []

    def _log(self, endpoint, result):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.request_log.append((timestamp, endpoint, result.success, result.message))
        if len(self.request_log) > 20:
            self.request_log.pop(0)

    def _call(self, endpoint, handler):
        if self.breaker.is_open():
            remaining = self.breaker.remaining()
            result = ServiceResult(False, f"Circuit Breaker открыт. Подождите {remaining} с.")
            self._log(endpoint, result)
            return result
        try:
            result = handler()
            if not result.success:
                self.breaker.record_failure()
            else:
                self.breaker.record_success()
            self._log(endpoint, result)
            return result
        except Exception as e:
            self.breaker.record_failure()
            result = ServiceResult(False, f"Ошибка сервиса: {e}")
            self._log(endpoint, result)
            return result

    def validate(self, sequence):
        return self._call("POST /validate", lambda: self.validator_service.validate(sequence))

    def status(self):
        return self._call("GET /status", lambda: self.password_service.status())

    def create(self, sequence):
        return self._call("POST /password", lambda: self.password_service.create(sequence))

    def verify(self, sequence):
        return self._call("POST /login", lambda: self.password_service.verify(sequence))

    def reset(self):
        return self._call("DELETE /password", lambda: self.password_service.reset())

    def get_log(self):
        return list(self.request_log)

    def breaker_state(self):
        if self.breaker.is_open():
            return f"OPEN ({self.breaker.remaining()} с)"
        return "CLOSED"

    def force_failure(self):
        self.breaker.record_failure()
        return self.breaker_state()


class AppWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Графический пароль — API Gateway + Circuit Breaker")
        self.root.geometry("560x980")
        self.root.resizable(False, False)

        self.bg_color = "#2b2b2b"
        self.fg_color = "white"

        self.root.configure(bg=self.bg_color)

        self.mode = "login"
        self.selected = []
        self.cell_rects = {}
        self.canvas = None

        self.gateway = APIGateway()

        self._build_ui()
        self._refresh()

    def _build_ui(self):
        tk.Label(self.root, text="Графический пароль",
                 font=("Segoe UI", 16, "bold"),
                 bg=self.bg_color, fg=self.fg_color).pack(pady=(12, 4))

        self.breaker_label = tk.Label(
            self.root,
            text="",
            font=("Segoe UI", 10, "bold"),
            bg=self.bg_color, fg="#4caf50"
        )
        self.breaker_label.pack(pady=2)

        canvas_frame = tk.Frame(self.root, bg=self.bg_color)
        canvas_frame.pack(pady=4)

        self.canvas = tk.Canvas(canvas_frame, width=280, height=280,
                                 bg=self.bg_color, highlightthickness=0)
        self.canvas.pack()

        self._draw_grid()

        self.seq_label = tk.Label(self.root, text="", font=("Segoe UI", 13),
                                   bg=self.bg_color, fg=self.fg_color)
        self.seq_label.pack(pady=4)

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

        api_frame = tk.Frame(self.root, bg=self.bg_color)
        api_frame.pack(pady=6)

        self.log_btn = RoundedButton(
            api_frame, text="Лог Gateway",
            command=self._show_log,
            width=200, height=36, radius=10,
            bg="#4a4a4a", fg="white",
            hover_bg="#5a5a5a", active_bg="#6a6a6a",
            font=("Segoe UI", 11), parent_bg=self.bg_color
        )
        self.log_btn.pack(side=tk.LEFT, padx=4)

        self.breaker_btn = RoundedButton(
            api_frame, text="Симулировать сбой",
            command=self._simulate_failure,
            width=200, height=36, radius=10,
            bg="#4a4a4a", fg="white",
            hover_bg="#5a5a5a", active_bg="#6a6a6a",
            font=("Segoe UI", 11), parent_bg=self.bg_color
        )
        self.breaker_btn.pack(side=tk.LEFT, padx=4)

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

    def _draw_grid(self):
        self.canvas.delete("all")
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
        if num in self.selected:
            self.status_label.config(text="Эта ячейка уже выбрана.", fg="#ffaa00")
            return
        if len(self.selected) >= 9:
            self.status_label.config(text="Максимальная длина — 9.", fg="#ffaa00")
            return
        self.selected.append(num)
        self._refresh()

    def _refresh(self):
        for i, rect_id in self.cell_rects.items():
            color = "#6a6a6a" if i in self.selected else "#4a4a4a"
            self.canvas.itemconfig(rect_id, fill=color)
        seq_str = " → ".join(map(str, self.selected))
        self.seq_label.config(text=seq_str)

        if self.mode == "login":
            self.primary_btn.set_text("Войти")
            self.login_mode_btn.set_colors("#6a6a6a", "#7a7a7a", "#8a8a8a")
            self.create_mode_btn.set_colors("#4a4a4a", "#5a5a5a", "#6a6a6a")
        else:
            self.primary_btn.set_text("Сохранить пароль")
            self.login_mode_btn.set_colors("#4a4a4a", "#5a5a5a", "#6a6a6a")
            self.create_mode_btn.set_colors("#6a6a6a", "#7a7a7a", "#8a8a8a")

        state = self.gateway.breaker_state()
        if state.startswith("OPEN"):
            self.breaker_label.config(text=f"Circuit Breaker: {state}", fg="#ff4444")
        else:
            self.breaker_label.config(text="Circuit Breaker: CLOSED", fg="#4caf50")

    def _clear_selection(self):
        self.selected = []
        self._refresh()
        self.status_label.config(text="")

    def _set_mode(self, mode):
        self.mode = mode
        self.selected = []
        self._refresh()

    def _primary_action(self):
        if self.mode == "login":
            self._login()
        else:
            self._create_password()

    def _create_password(self):
        if not self.selected:
            self.status_label.config(text="Выберите последовательность.", fg="#ffaa00")
            return
        status = self.gateway.status()
        if not status.success:
            self._show_result(status)
            return
        if status.data.get("has_password"):
            if not messagebox.askyesno("Подтверждение",
                                        "Пароль уже существует. Перезаписать?"):
                return
            self.gateway.reset()
        validate_result = self.gateway.validate(self.selected)
        if not validate_result.success:
            self._show_result(validate_result)
            return
        result = self.gateway.create(self.selected)
        self._show_result(result)
        if result.success:
            self.selected = []
        self._refresh()

    def _login(self):
        if not self.selected:
            self.status_label.config(text="Введите последовательность.", fg="#ffaa00")
            return
        validate_result = self.gateway.validate(self.selected)
        if not validate_result.success:
            self._show_result(validate_result)
            return
        result = self.gateway.verify(self.selected)
        self._show_result(result)
        if result.success:
            self.selected = []
        self._refresh()

    def _reset_password(self):
        result = self.gateway.reset()
        self._show_result(result)
        self.selected = []
        self._refresh()

    def _show_result(self, result):
        if result.success:
            self.status_label.config(text=result.message, fg="#4caf50")
            messagebox.showinfo("Успех", result.message)
        else:
            self.status_label.config(text=result.message, fg="#ff4444")
            messagebox.showerror("Ошибка", result.message)

    def _show_log(self):
        log = self.gateway.get_log()
        if not log:
            messagebox.showinfo("Лог Gateway", "Лог пока пуст.")
            return
        lines = [f"[{ts}] {ep} -> {ok}: {msg}" for ts, ep, ok, msg in log[-15:]]
        messagebox.showinfo("Лог Gateway", "\n".join(lines))

    def _simulate_failure(self):
        state = self.gateway.force_failure()
        self._refresh()
        messagebox.showwarning(
            "Симуляция сбоя",
            f"Зафиксирован сбой. Состояние Circuit Breaker: {state}"
        )


if __name__ == "__main__":
    root = tk.Tk()
    app = AppWindow(root)
    root.mainloop()