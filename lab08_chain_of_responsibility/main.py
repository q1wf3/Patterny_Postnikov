import tkinter as tk
from tkinter import messagebox
from abc import ABC, abstractmethod
import hashlib
import json
import os


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


class ValidationResult:
    def __init__(self, valid, message=""):
        self.valid = valid
        self.message = message


class SequenceValidator(ABC):
    def __init__(self):
        self._next_handler = None

    def set_next(self, handler):
        self._next_handler = handler
        return handler

    def handle(self, sequence):
        result = self._check(sequence)
        if result is not None:
            return result
        if self._next_handler is not None:
            return self._next_handler.handle(sequence)
        return ValidationResult(True, "")

    @abstractmethod
    def _check(self, sequence):
        pass

    @abstractmethod
    def get_name(self):
        pass


class LengthValidator(SequenceValidator):
    def get_name(self):
        return "Проверка длины"

    def _check(self, sequence):
        if not isinstance(sequence, list):
            return ValidationResult(False, "Последовательность должна быть списком.")
        if len(sequence) < 4:
            return ValidationResult(False, "Слишком короткая: минимум 4 ячейки.")
        if len(sequence) > 9:
            return ValidationResult(False, "Слишком длинная: максимум 9 ячеек.")
        return None


class DuplicateValidator(SequenceValidator):
    def get_name(self):
        return "Проверка повторов"

    def _check(self, sequence):
        if len(set(sequence)) != len(sequence):
            return ValidationResult(False, "Есть повторяющиеся ячейки.")
        return None


class RangeValidator(SequenceValidator):
    def get_name(self):
        return "Проверка диапазона"

    def _check(self, sequence):
        for x in sequence:
            if not isinstance(x, int) or x < 1 or x > 9:
                return ValidationResult(False, f"Ячейка {x} вне диапазона 1–9.")
        return None


class SimplePatternValidator(SequenceValidator):
    def get_name(self):
        return "Проверка простоты"

    def _check(self, sequence):
        if len(sequence) >= 3:
            diffs = [sequence[i+1] - sequence[i] for i in range(len(sequence)-1)]
            if len(set(diffs)) == 1:
                return ValidationResult(
                    False,
                    "Слишком простой пароль: все шаги одинаковые."
                )
        return None


class ValidationChain:
    def __init__(self):
        self._head = None
        self._handlers = []

    def add(self, handler):
        self._handlers.append(handler)
        if self._head is None:
            self._head = handler
        else:
            last = self._handlers[-2]
            last.set_next(handler)
        return self

    def validate(self, sequence):
        if self._head is None:
            return ValidationResult(True, "")
        return self._head.handle(sequence)

    def get_handler_names(self):
        return [h.get_name() for h in self._handlers]


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
        self.root.title("Графический пароль — Цепочка обязанностей")
        self.root.geometry("540x960")
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

        self.password_manager = PasswordManager()

        self.validation_chain = ValidationChain()
        self.validation_chain.add(LengthValidator())
        self.validation_chain.add(DuplicateValidator())
        self.validation_chain.add(RangeValidator())
        self.validation_chain.add(SimplePatternValidator())

        self.patterns = [
            PasswordPattern("Крест", [2, 5, 8, 4, 6]),
            PasswordPattern("Квадрат", [1, 2, 3, 6, 9, 8, 7, 4]),
            PasswordPattern("Зигзаг", [1, 2, 4, 3, 5, 7, 6, 8, 9]),
        ]

        self._build_ui()
        self._update_mode()

    def _build_ui(self):
        tk.Label(self.root, text="Графический пароль",
                 font=("Segoe UI", 16, "bold"),
                 bg=self.bg_color, fg=self.fg_color).pack(pady=(12, 6))

        self.canvas_frame = tk.Frame(self.root, bg=self.bg_color)
        self.canvas_frame.pack(pady=4)

        self.canvas = tk.Canvas(self.canvas_frame, width=280, height=280,
                                 bg=self.bg_color, highlightthickness=0)
        self.canvas.pack()

        self._draw_grid_buttons()

        self.seq_label = tk.Label(self.root, text="", font=("Segoe UI", 13),
                                   bg=self.bg_color, fg=self.fg_color)
        self.seq_label.pack(pady=4)

        self.chain_label = tk.Label(self.root,
                                      text="Цепочка: " + " → ".join(self.validation_chain.get_handler_names()),
                                      font=("Segoe UI", 9),
                                      bg=self.bg_color, fg="#808080",
                                      wraplength=480)
        self.chain_label.pack(pady=2)

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

        validate_btn_frame = tk.Frame(self.root, bg=self.bg_color)
        validate_btn_frame.pack(pady=6)

        self.validate_btn = RoundedButton(
            validate_btn_frame, text="Проверить цепочкой",
            command=self._validate_current,
            width=240, height=38, radius=10,
            bg="#4a90d9", fg="white",
            hover_bg="#357abd", active_bg="#2c6aa0",
            font=("Segoe UI", 11), parent_bg=self.bg_color
        )
        self.validate_btn.pack()

        self.reset_btn = RoundedButton(
            self.root, text="Сбросить сохранённый пароль",
            command=self._reset_password,
            width=260, height=34, radius=10,
            bg="#3a3a3a", fg="#a0a0a0",
            hover_bg="#4a4a4a", active_bg="#5a5a5a",
            font=("Segoe UI", 10), parent_bg=self.bg_color
        )
        self.reset_btn.pack(pady=8)

        self.status_label = tk.Label(self.root, text="", font=("Segoe UI", 10),
                                      bg=self.bg_color, fg=self.fg_color,
                                      wraplength=480)
        self.status_label.pack(pady=3)

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

        def on_click(_):
            self.selected = list(pattern.sequence)
            self._update_ui()
            self.status_label.config(
                text=f"Загружен шаблон: {pattern.name}", fg="#4a90d9"
            )

        card.tag_bind("card", "<Button-1>", on_click)
        return card

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

    def _clear_selection(self):
        self.selected = []
        self._update_ui()
        self.status_label.config(text="")

    def _validate_current(self):
        if not self.selected:
            self.status_label.config(text="Последовательность пуста.", fg="#ffaa00")
            return False
        result = self.validation_chain.validate(self.selected)
        if result.valid:
            self.status_label.config(
                text="Все проверки пройдены — последовательность корректна.",
                fg="#4caf50"
            )
            messagebox.showinfo("Цепочка обязанностей",
                                 "Все обработчики цепочки пропустили запрос.\n"
                                 "Последовательность корректна.")
            return True
        self.status_label.config(text=result.message, fg="#ff4444")
        messagebox.showerror("Цепочка обязанностей",
                              f"Проверка не пройдена:\n{result.message}")
        return False

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
        result = self.validation_chain.validate(self.selected)
        if not result.valid:
            self.status_label.config(text=result.message, fg="#ff4444")
            messagebox.showerror("Цепочка обязанностей",
                                  f"Проверка не пройдена:\n{result.message}")
            return
        if self.password_manager.has_password():
            if not messagebox.askyesno("Подтверждение",
                                        "Пароль уже существует. Перезаписать?"):
                return
            self.password_manager.reset_password()
        self.password_manager.create_password(self.selected)
        messagebox.showinfo("Успех", "Графический пароль успешно создан.")
        self._clear_selection()

    def _login(self):
        if not self.password_manager.has_password():
            messagebox.showwarning("Внимание",
                                    "Пароль не создан. Сначала создайте пароль.")
            return
        if not self.selected:
            self.status_label.config(text="Введите последовательность.", fg="#ffaa00")
            return
        result = self.validation_chain.validate(self.selected)
        if not result.valid:
            self.status_label.config(text=result.message, fg="#ff4444")
            messagebox.showerror("Цепочка обязанностей",
                                  f"Проверка не пройдена:\n{result.message}")
            return
        if self.password_manager.verify_password(self.selected):
            messagebox.showinfo("Успех", "Пароль верный. Доступ разрешён.")
            self._clear_selection()
        else:
            messagebox.showerror("Ошибка", "Пароль неверный. Доступ запрещён.")
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