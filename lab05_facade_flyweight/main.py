import tkinter as tk
from tkinter import messagebox
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


class CellStyle:
    def __init__(self, bg, fg, font, radius):
        self.bg = bg
        self.fg = fg
        self.font = font
        self.radius = radius


class CellStyleFactory:
    _cache = {}

    @classmethod
    def get(cls, key):
        if key not in cls._cache:
            if key == "normal":
                cls._cache[key] = CellStyle("#4a4a4a", "white", ("Segoe UI", 20, "bold"), 12)
            elif key == "selected":
                cls._cache[key] = CellStyle("#6a6a6a", "white", ("Segoe UI", 20, "bold"), 12)
        return cls._cache[key]

    @classmethod
    def count(cls):
        return len(cls._cache)


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


class PasswordPattern:
    def __init__(self, name, sequence):
        self.name = name
        self.sequence = sequence


class PasswordFacade:
    def __init__(self):
        self._manager = PasswordManager()
        self._patterns = [
            PasswordPattern("Крест", [2, 5, 8, 4, 6]),
            PasswordPattern("Квадрат", [1, 2, 3, 6, 9, 8, 7, 4]),
            PasswordPattern("Зигзаг", [1, 2, 4, 3, 5, 7, 6, 8, 9]),
        ]

    def get_patterns(self):
        return list(self._patterns)

    def find_pattern(self, name):
        for p in self._patterns:
            if p.name == name:
                return list(p.sequence)
        return None

    def has_password(self):
        return self._manager.has_password()

    def create_password(self, sequence):
        if not validate_sequence(sequence):
            return False, "Некорректная последовательность. Длина от 4 до 9, без повторов."
        if self._manager.has_password():
            return None, "Пароль уже существует"
        self._manager.create_password(sequence)
        return True, "Графический пароль успешно создан."

    def verify(self, sequence):
        if not self._manager.has_password():
            return False, "Пароль не создан. Сначала создайте пароль."
        if not validate_sequence(sequence):
            return False, "Некорректная последовательность."
        if self._manager.verify_password(sequence):
            return True, "Пароль верный. Доступ разрешён."
        return False, "Пароль неверный. Доступ запрещён."

    def reset(self):
        self._manager.reset_password()


class AppWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Графический пароль — Фасад + Приспособленец")
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

        self.facade = PasswordFacade()

        self._build_ui()
        self._update_mode()

    def _build_ui(self):
        tk.Label(self.root, text="Графический пароль",
                 font=("Segoe UI", 16, "bold"),
                 bg=self.bg_color, fg=self.fg_color).pack(pady=(12, 5))

        self.canvas_frame = tk.Frame(self.root, bg=self.bg_color)
        self.canvas_frame.pack(pady=5)

        self.canvas = tk.Canvas(self.canvas_frame, width=320, height=320,
                                 bg=self.bg_color, highlightthickness=0)
        self.canvas.pack()

        self._draw_grid_buttons()

        self.seq_label = tk.Label(self.root, text="", font=("Segoe UI", 13),
                                   bg=self.bg_color, fg=self.fg_color)
        self.seq_label.pack(pady=6)

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
        mode_frame.pack(pady=8)

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
                 bg=self.bg_color, fg=self.fg_color).pack(pady=(10, 3))

        cards_frame = tk.Frame(self.root, bg=self.bg_color)
        cards_frame.pack(pady=3)

        for i, pattern in enumerate(self.facade.get_patterns()):
            card = self._make_pattern_card(cards_frame, pattern)
            row = i // 2
            col = i % 2
            card.grid(row=row, column=col, padx=4, pady=3)

        flyweight_btn = RoundedButton(
            self.root, text="Статистика Flyweight",
            command=self._show_flyweight_stats,
            width=260, height=36, radius=10,
            bg="#4a4a4a", fg="white",
            hover_bg="#5a5a5a", active_bg="#6a6a6a",
            font=("Segoe UI", 11), parent_bg=self.bg_color
        )
        flyweight_btn.pack(pady=8)

        self.reset_btn = RoundedButton(
            self.root, text="Сбросить сохранённый пароль",
            command=self._reset_password,
            width=260, height=36, radius=10,
            bg="#3a3a3a", fg="#a0a0a0",
            hover_bg="#4a4a4a", active_bg="#5a5a5a",
            font=("Segoe UI", 10), parent_bg=self.bg_color
        )
        self.reset_btn.pack(pady=4)

        self.status_label = tk.Label(self.root, text="", font=("Segoe UI", 10),
                                      bg=self.bg_color, fg=self.fg_color)
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
            self._apply_pattern(pattern)

        card.tag_bind("card", "<Button-1>", on_click)
        return card

    def _draw_grid_buttons(self):
        self.canvas.delete("all")
        self.button_coords = {}
        self.cell_rects = {}

        start_x, start_y = 35, 35
        step = 85
        size = 70

        style = CellStyleFactory.get("normal")

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

            rect = rounded_rect(self.canvas, x1, y1, x2, y2,
                                 r=style.radius,
                                 fill=style.bg, outline="")
            self.canvas.create_text(cx, cy, text=str(i),
                                     fill=style.fg, font=style.font)

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
        normal_style = CellStyleFactory.get("normal")
        selected_style = CellStyleFactory.get("selected")

        for i, rect_id in self.cell_rects.items():
            style = selected_style if i in self.selected else normal_style
            self.canvas.itemconfig(rect_id, fill=style.bg)

        seq_str = " → ".join(map(str, self.selected))
        self.seq_label.config(text=seq_str)

    def _clear_selection(self):
        self.selected = []
        self._update_ui()
        self.status_label.config(text="")

    def _apply_pattern(self, pattern):
        seq = list(pattern.sequence)
        if not validate_sequence(seq):
            self.status_label.config(
                text=f"Шаблон «{pattern.name}» не подходит.",
                fg="#ffaa00"
            )
            return

        self.selected = seq
        self._update_ui()
        self.status_label.config(
            text=f"Применён шаблон: {pattern.name}",
            fg="#4a90d9"
        )
        messagebox.showinfo(
            "Шаблон применён",
            f"Использован шаблон: «{pattern.name}»\n"
            f"Последовательность: {' → '.join(map(str, seq))}"
        )

    def _show_flyweight_stats(self):
        total_cells = len(self.cell_rects)
        shared_styles = CellStyleFactory.count()
        messagebox.showinfo(
            "Статистика Flyweight",
            f"Всего ячеек на сетке: {total_cells}\n"
            f"Уникальных объектов CellStyle: {shared_styles}\n\n"
            f"Благодаря паттерну «Приспособленец» все ячейки\n"
            f"используют общие объекты стиля вместо создания\n"
            f"{total_cells} отдельных объектов."
        )

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
        if self.facade.has_password():
            if not messagebox.askyesno("Подтверждение",
                                        "Пароль уже существует. Перезаписать?"):
                return
            self.facade.reset()
        result, message = self.facade.create_password(self.selected)
        if result:
            messagebox.showinfo("Успех", message)
            self._clear_selection()
        else:
            self.status_label.config(text=message, fg="#ffaa00")

    def _login(self):
        if not self.selected:
            self.status_label.config(text="Введите последовательность.", fg="#ffaa00")
            return
        result, message = self.facade.verify(self.selected)
        if result:
            messagebox.showinfo("Успех", message)
            self._clear_selection()
        else:
            messagebox.showerror("Ошибка", message)
            self._clear_selection()

    def _reset_password(self):
        if not self.facade.has_password():
            self.status_label.config(text="Пароль не установлен.", fg="#ffaa00")
            return
        if messagebox.askyesno("Подтверждение",
                                "Удалить сохранённый графический пароль?"):
            self.facade.reset()
            messagebox.showinfo("Успех", "Пароль удалён.")
            self._clear_selection()


if __name__ == "__main__":
    root = tk.Tk()
    app = AppWindow(root)
    root.mainloop()