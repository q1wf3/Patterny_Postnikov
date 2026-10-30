import tkinter as tk
from tkinter import messagebox
from abc import ABC, abstractmethod
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


class HashingStrategy(ABC):
    @abstractmethod
    def hash(self, sequence):
        pass

    @abstractmethod
    def get_name(self):
        pass


class SHA256Strategy(HashingStrategy):
    def hash(self, sequence):
        data = "".join(map(str, sequence))
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    def get_name(self):
        return "SHA-256"


class MD5Strategy(HashingStrategy):
    def hash(self, sequence):
        data = "".join(map(str, sequence))
        return hashlib.md5(data.encode('utf-8')).hexdigest()

    def get_name(self):
        return "MD5"


class LengthStrategy(HashingStrategy):
    def hash(self, sequence):
        return f"len:{len(sequence)}:sum:{sum(sequence)}"

    def get_name(self):
        return "Length+Sum"


class PasswordResult:
    def __init__(self, success, message, hash_value=None):
        self.success = success
        self.message = message
        self.hash_value = hash_value


class PasswordOperation(ABC):
    def __init__(self, manager):
        self.manager = manager

    def execute(self, sequence):
        ok, msg = self.validate(sequence)
        if not ok:
            return PasswordResult(False, msg)

        prepared = self.prepare(sequence)
        hash_value = self.do_hash(prepared)

        save_result = self.save(sequence, hash_value)
        if not save_result.success:
            return save_result

        self.after_save(sequence, hash_value)
        return PasswordResult(True, self.success_message(), hash_value)

    def validate(self, sequence):
        return validate_sequence(sequence)

    def prepare(self, sequence):
        return list(sequence)

    @abstractmethod
    def do_hash(self, sequence):
        pass

    @abstractmethod
    def save(self, sequence, hash_value):
        pass

    def after_save(self, sequence, hash_value):
        pass

    @abstractmethod
    def success_message(self):
        pass


class CreatePasswordOperation(PasswordOperation):
    def do_hash(self, sequence):
        return self.manager.strategy.hash(sequence)

    def save(self, sequence, hash_value):
        self.manager.password_hash = hash_value
        self.manager.save_to_file()
        return PasswordResult(True, "")

    def after_save(self, sequence, hash_value):
        self.manager.notify_strategy_used(self.manager.strategy.get_name())

    def success_message(self):
        return "Графический пароль успешно создан."


class VerifyPasswordOperation(PasswordOperation):
    def do_hash(self, sequence):
        return self.manager.strategy.hash(sequence)

    def save(self, sequence, hash_value):
        if not self.manager.has_password():
            return PasswordResult(False, "Пароль не установлен.")
        if hash_value == self.manager.password_hash:
            return PasswordResult(True, "")
        return PasswordResult(False, "Пароль неверный. Доступ запрещён.")

    def success_message(self):
        return "Пароль верный. Доступ разрешён."


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
        self.strategy = SHA256Strategy()
        self.last_strategy_used = None
        self._load()

    def set_strategy(self, strategy):
        self.strategy = strategy

    def notify_strategy_used(self, name):
        self.last_strategy_used = name

    def _load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.password_hash = data.get("password_hash")
                    self.last_strategy_used = data.get("strategy", "SHA-256")
            except (json.JSONDecodeError, FileNotFoundError):
                self.password_hash = None
        else:
            self.password_hash = None

    def save_to_file(self):
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump({
                "password_hash": self.password_hash,
                "strategy": self.strategy.get_name()
            }, f, ensure_ascii=False, indent=4)

    def has_password(self):
        return self.password_hash is not None

    def reset_password(self):
        self.password_hash = None
        self.last_strategy_used = None
        if os.path.exists(self.filename):
            os.remove(self.filename)


class AppWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Графический пароль — Стратегия + Шаблонный метод")
        self.root.geometry("540x960")
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

        self.create_operation = CreatePasswordOperation(self.password_manager)
        self.verify_operation = VerifyPasswordOperation(self.password_manager)

        self.strategies = [SHA256Strategy(), MD5Strategy(), LengthStrategy()]
        self.strategy_index = 0
        self.password_manager.set_strategy(self.strategies[0])

        self._build_ui()
        self._update_strategy_label()

    def _build_ui(self):
        tk.Label(self.root, text="Графический пароль",
                 font=("Segoe UI", 16, "bold"),
                 bg=self.bg_color, fg=self.fg_color).pack(pady=(12, 4))

        self.canvas_frame = tk.Frame(self.root, bg=self.bg_color)
        self.canvas_frame.pack(pady=4)

        self.canvas = tk.Canvas(self.canvas_frame, width=280, height=280,
                                 bg=self.bg_color, highlightthickness=0)
        self.canvas.pack()

        self._draw_grid_buttons()

        self.seq_label = tk.Label(self.root, text="", font=("Segoe UI", 13),
                                   bg=self.bg_color, fg=self.fg_color)
        self.seq_label.pack(pady=4)

        strategy_frame = tk.Frame(self.root, bg=self.bg_color)
        strategy_frame.pack(pady=4)

        tk.Label(strategy_frame, text="Стратегия хэширования:",
                 font=("Segoe UI", 10),
                 bg=self.bg_color, fg="#a0a0a0").pack()

        self.strategy_label = tk.Label(strategy_frame, text="",
                                        font=("Segoe UI", 11, "bold"),
                                        bg=self.bg_color, fg="#4a90d9")
        self.strategy_label.pack(pady=2)

        strategy_btn_frame = tk.Frame(self.root, bg=self.bg_color)
        strategy_btn_frame.pack(pady=4)

        self.strategy_btn = RoundedButton(
            strategy_btn_frame, text="Сменить стратегию",
            command=self._next_strategy,
            width=240, height=36, radius=10,
            bg="#4a4a4a", fg="white",
            hover_bg="#5a5a5a", active_bg="#6a6a6a",
            font=("Segoe UI", 11), parent_bg=self.bg_color
        )
        self.strategy_btn.pack()

        self.hash_label = tk.Label(self.root, text="", font=("Consolas", 9),
                                    bg=self.bg_color, fg="#808080",
                                    wraplength=480)
        self.hash_label.pack(pady=2)

        self.primary_btn = RoundedButton(
            self.root, text="Войти", command=self._primary_action,
            width=240, height=42, radius=12,
            bg="#4a90d9", fg="white",
            hover_bg="#357abd", active_bg="#2c6aa0",
            font=("Segoe UI", 12, "bold"), parent_bg=self.bg_color
        )
        self.primary_btn.pack(pady=4)

        self.clear_btn = RoundedButton(
            self.root, text="Очистить", command=self._clear_selection,
            width=240, height=42, radius=12,
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
        if self.selected:
            current_hash = self.password_manager.strategy.hash(self.selected)
            self.hash_label.config(
                text=f"{self.password_manager.strategy.get_name()}: {current_hash[:40]}..."
            )
        else:
            self.hash_label.config(text="")

    def _update_strategy_label(self):
        self.strategy_label.config(
            text=self.password_manager.strategy.get_name()
        )

    def _next_strategy(self):
        self.strategy_index = (self.strategy_index + 1) % len(self.strategies)
        new_strategy = self.strategies[self.strategy_index]
        self.password_manager.set_strategy(new_strategy)
        self._update_strategy_label()
        self._update_ui()
        self.status_label.config(
            text=f"Стратегия изменена на: {new_strategy.get_name()}",
            fg="#4a90d9"
        )

    def _clear_selection(self):
        self.selected = []
        self._update_ui()
        self.status_label.config(text="")

    def _set_mode(self, mode):
        self.mode = mode
        self.selected = []
        self._update_ui()
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
        if self.password_manager.has_password():
            if not messagebox.askyesno("Подтверждение",
                                        "Пароль уже существует. Перезаписать?"):
                return
        result = self.create_operation.execute(self.selected)
        if result.success:
            messagebox.showinfo(
                "Успех",
                f"{result.message}\n\nСтратегия: {self.password_manager.strategy.get_name()}\n"
                f"Хэш: {result.hash_value[:40]}..."
            )
            self._clear_selection()
        else:
            self.status_label.config(text=result.message, fg="#ff4444")
            messagebox.showerror("Ошибка", result.message)

    def _login(self):
        if not self.password_manager.has_password():
            messagebox.showwarning("Внимание",
                                    "Пароль не создан. Сначала создайте пароль.")
            return
        if not self.selected:
            self.status_label.config(text="Введите последовательность.", fg="#ffaa00")
            return
        result = self.verify_operation.execute(self.selected)
        if result.success:
            messagebox.showinfo("Успех", result.message)
            self._clear_selection()
        else:
            messagebox.showerror("Ошибка", result.message)
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