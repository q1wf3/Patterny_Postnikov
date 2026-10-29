import tkinter as tk
from tkinter import messagebox
from abc import ABC, abstractmethod
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


class Command(ABC):
    @abstractmethod
    def execute(self):
        pass

    @abstractmethod
    def undo(self):
        pass


class SelectCellCommand(Command):
    def __init__(self, app, number):
        self.app = app
        self.number = number

    def execute(self):
        self.app.selected.append(self.number)

    def undo(self):
        if self.number in self.app.selected:
            self.app.selected.remove(self.number)


class ClearSelectionCommand(Command):
    def __init__(self, app):
        self.app = app
        self.previous = None

    def execute(self):
        self.previous = list(self.app.selected)
        self.app.selected = []

    def undo(self):
        if self.previous is not None:
            self.app.selected = list(self.previous)


class ApplyPatternCommand(Command):
    def __init__(self, app, pattern):
        self.app = app
        self.pattern = pattern
        self.previous = None

    def execute(self):
        self.previous = list(self.app.selected)
        self.app.selected = list(self.pattern.sequence)

    def undo(self):
        if self.previous is not None:
            self.app.selected = list(self.previous)


class CommandInvoker:
    def __init__(self):
        self._history = []
        self._redo_stack = []

    def execute(self, command):
        command.execute()
        self._history.append(command)
        self._redo_stack.clear()

    def undo(self):
        if not self._history:
            return False
        cmd = self._history.pop()
        cmd.undo()
        self._redo_stack.append(cmd)
        return True

    def redo(self):
        if not self._redo_stack:
            return False
        cmd = self._redo_stack.pop()
        cmd.execute()
        self._history.append(cmd)
        return True

    def can_undo(self):
        return len(self._history) > 0

    def can_redo(self):
        return len(self._redo_stack) > 0

    def clear(self):
        self._history.clear()
        self._redo_stack.clear()


class PatternIterator(ABC):
    @abstractmethod
    def has_next(self):
        pass

    @abstractmethod
    def next(self):
        pass

    @abstractmethod
    def has_previous(self):
        pass

    @abstractmethod
    def previous(self):
        pass

    @abstractmethod
    def current(self):
        pass

    @abstractmethod
    def index(self):
        pass

    @abstractmethod
    def total(self):
        pass


class PatternCollectionIterator(PatternIterator):
    def __init__(self, patterns):
        self._patterns = list(patterns)
        self._index = 0

    def has_next(self):
        return self._index < len(self._patterns) - 1

    def next(self):
        if self.has_next():
            self._index += 1
        return self.current()

    def has_previous(self):
        return self._index > 0

    def previous(self):
        if self.has_previous():
            self._index -= 1
        return self.current()

    def current(self):
        if not self._patterns:
            return None
        return self._patterns[self._index]

    def index(self):
        return self._index + 1 if self._patterns else 0

    def total(self):
        return len(self._patterns)


class PatternCollection:
    def __init__(self, patterns):
        self._patterns = list(patterns)

    def create_iterator(self):
        return PatternCollectionIterator(self._patterns)

    def __len__(self):
        return len(self._patterns)


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


class AppWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Графический пароль — Команда + Итератор")
        self.root.geometry("540x900")
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
        self.invoker = CommandInvoker()

        self.patterns = PatternCollection([
            PasswordPattern("Крест", [2, 5, 8, 4, 6]),
            PasswordPattern("Квадрат", [1, 2, 3, 6, 9, 8, 7, 4]),
            PasswordPattern("Зигзаг", [1, 2, 4, 3, 5, 7, 6, 8, 9]),
        ])
        self.iterator = self.patterns.create_iterator()

        self._build_ui()
        self._update_mode()
        self._update_iterator_label()

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

        self.primary_btn = RoundedButton(
            self.root, text="Войти", command=self._primary_action,
            width=240, height=40, radius=12,
            bg="#4a90d9", fg="white",
            hover_bg="#357abd", active_bg="#2c6aa0",
            font=("Segoe UI", 12, "bold"), parent_bg=self.bg_color
        )
        self.primary_btn.pack(pady=3)

        self.clear_btn = RoundedButton(
            self.root, text="Очистить", command=self._command_clear,
            width=240, height=40, radius=12,
            bg="#4a4a4a", fg="white",
            hover_bg="#5a5a5a", active_bg="#6a6a6a",
            font=("Segoe UI", 12), parent_bg=self.bg_color
        )
        self.clear_btn.pack(pady=3)

        cmd_frame = tk.Frame(self.root, bg=self.bg_color)
        cmd_frame.pack(pady=4)

        self.undo_btn = RoundedButton(
            cmd_frame, text="↶ Отменить", command=self._command_undo,
            width=130, height=36, radius=10,
            bg="#4a4a4a", fg="white",
            hover_bg="#5a5a5a", active_bg="#6a6a6a",
            font=("Segoe UI", 11), parent_bg=self.bg_color
        )
        self.undo_btn.pack(side=tk.LEFT, padx=4)

        self.redo_btn = RoundedButton(
            cmd_frame, text="↷ Повторить", command=self._command_redo,
            width=130, height=36, radius=10,
            bg="#4a4a4a", fg="white",
            hover_bg="#5a5a5a", active_bg="#6a6a6a",
            font=("Segoe UI", 11), parent_bg=self.bg_color
        )
        self.redo_btn.pack(side=tk.LEFT, padx=4)

        mode_frame = tk.Frame(self.root, bg=self.bg_color)
        mode_frame.pack(pady=4)

        self.login_mode_btn = RoundedButton(
            mode_frame, text="Вход",
            command=lambda: self._set_mode("login"),
            width=140, height=36, radius=10,
            bg="#6a6a6a", fg="white",
            hover_bg="#7a7a7a", active_bg="#8a8a8a",
            font=("Segoe UI", 11), parent_bg=self.bg_color
        )
        self.login_mode_btn.pack(side=tk.LEFT, padx=4)

        self.create_mode_btn = RoundedButton(
            mode_frame, text="Создать пароль",
            command=lambda: self._set_mode("create"),
            width=160, height=36, radius=10,
            bg="#4a4a4a", fg="white",
            hover_bg="#5a5a5a", active_bg="#6a6a6a",
            font=("Segoe UI", 11), parent_bg=self.bg_color
        )
        self.create_mode_btn.pack(side=tk.LEFT, padx=4)

        iter_frame = tk.Frame(self.root, bg=self.bg_color)
        iter_frame.pack(pady=6)

        self.iter_prev_btn = RoundedButton(
            iter_frame, text="◀", command=self._iterator_previous,
            width=44, height=36, radius=10,
            bg="#4a4a4a", fg="white",
            hover_bg="#5a5a5a", active_bg="#6a6a6a",
            font=("Segoe UI", 12), parent_bg=self.bg_color
        )
        self.iter_prev_btn.pack(side=tk.LEFT, padx=3)

        self.iter_label = tk.Label(iter_frame, text="", font=("Segoe UI", 11),
                                    bg=self.bg_color, fg=self.fg_color,
                                    width=20, anchor="center")
        self.iter_label.pack(side=tk.LEFT, padx=3)

        self.iter_next_btn = RoundedButton(
            iter_frame, text="▶", command=self._iterator_next,
            width=44, height=36, radius=10,
            bg="#4a4a4a", fg="white",
            hover_bg="#5a5a5a", active_bg="#6a6a6a",
            font=("Segoe UI", 12), parent_bg=self.bg_color
        )
        self.iter_next_btn.pack(side=tk.LEFT, padx=3)

        apply_frame = tk.Frame(self.root, bg=self.bg_color)
        apply_frame.pack(pady=3)

        self.apply_pattern_btn = RoundedButton(
            apply_frame, text="Применить шаблон",
            command=self._command_apply_pattern,
            width=240, height=36, radius=10,
            bg="#4a4a4a", fg="white",
            hover_bg="#5a5a5a", active_bg="#6a6a6a",
            font=("Segoe UI", 11), parent_bg=self.bg_color
        )
        self.apply_pattern_btn.pack()

        self.reset_btn = RoundedButton(
            self.root, text="Сбросить сохранённый пароль",
            command=self._reset_password,
            width=260, height=34, radius=10,
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
        self.invoker.execute(SelectCellCommand(self, num))
        self._update_ui()

    def _command_clear(self):
        if not self.selected:
            self.status_label.config(text="Последовательность уже пуста.", fg="#a0a0a0")
            return
        self.invoker.execute(ClearSelectionCommand(self))
        self._update_ui()

    def _command_undo(self):
        if self.invoker.undo():
            self._update_ui()
            self.status_label.config(text="Действие отменено.", fg="#4a90d9")
        else:
            self.status_label.config(text="Нечего отменять.", fg="#ffaa00")

    def _command_redo(self):
        if self.invoker.redo():
            self._update_ui()
            self.status_label.config(text="Действие повторено.", fg="#4a90d9")
        else:
            self.status_label.config(text="Нечего повторять.", fg="#ffaa00")

    def _command_apply_pattern(self):
        pattern = self.iterator.current()
        if pattern is None:
            self.status_label.config(text="Шаблон не выбран.", fg="#ffaa00")
            return
        if not validate_sequence(pattern.sequence):
            self.status_label.config(
                text=f"Шаблон «{pattern.name}» не подходит (длина или повторы).",
                fg="#ffaa00"
            )
            return
        self.invoker.execute(ApplyPatternCommand(self, pattern))
        self._update_ui()
        self.status_label.config(
            text=f"Применён шаблон: {pattern.name}",
            fg="#4a90d9"
        )
        messagebox.showinfo(
            "Шаблон применён",
            f"Использован шаблон: «{pattern.name}»\n"
            f"Последовательность: {' → '.join(map(str, pattern.sequence))}"
        )

    def _iterator_previous(self):
        self.iterator.previous()
        self._update_iterator_label()

    def _iterator_next(self):
        self.iterator.next()
        self._update_iterator_label()

    def _update_iterator_label(self):
        pattern = self.iterator.current()
        if pattern is None:
            self.iter_label.config(text="Шаблоны отсутствуют")
            return
        self.iter_label.config(
            text=f"{pattern.name} ({self.iterator.index()}/{self.iterator.total()})"
        )

    def _update_ui(self):
        for i, rect_id in self.cell_rects.items():
            color = "#6a6a6a" if i in self.selected else "#4a4a4a"
            self.canvas.itemconfig(rect_id, fill=color)
        seq_str = " → ".join(map(str, self.selected))
        self.seq_label.config(text=seq_str)

    def _clear_selection(self):
        self.selected = []
        self.invoker.clear()
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
        if not validate_sequence(self.selected):
            self.status_label.config(text="Некорректная длина. Нужно от 4 до 9.", fg="#ffaa00")
            return
        if self.password_manager.has_password():
            if not messagebox.askyesno("Подтверждение",
                                        "Пароль уже существует. Перезаписать?"):
                return
            self.password_manager.reset_password()
        try:
            self.password_manager.create_password(self.selected)
            messagebox.showinfo("Успех", "Графический пароль успешно создан.")
            self._clear_selection()
        except ValueError as e:
            self.status_label.config(text=str(e), fg="#ff4444")

    def _login(self):
        if not self.password_manager.has_password():
            messagebox.showwarning("Внимание",
                                    "Пароль не создан. Сначала создайте пароль.")
            return
        if not self.selected:
            self.status_label.config(text="Введите последовательность.", fg="#ffaa00")
            return
        if not validate_sequence(self.selected):
            self.status_label.config(text="Некорректная последовательность.", fg="#ffaa00")
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