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
        w = self._width
        h = self._height
        rounded_rect(self, 0, 0, w, h, r=self.radius,
                     fill=self._current_bg, outline="")
        self.create_text(w / 2, h / 2, text=self.text,
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


class SequenceTarget(ABC):
    @abstractmethod
    def get_sequence_string(self) -> str:
        pass

    @abstractmethod
    def set_sequence_from_string(self, data: str):
        pass


class ListAdaptee:
    def __init__(self, sequence: list):
        self._sequence = sequence

    def get_list(self) -> list:
        return self._sequence

    def set_list(self, seq: list):
        self._sequence = seq


class SequenceAdapter(SequenceTarget):
    def __init__(self, adaptee: ListAdaptee):
        self._adaptee = adaptee

    def get_sequence_string(self) -> str:
        return "-".join(map(str, self._adaptee.get_list()))

    def set_sequence_from_string(self, data: str):
        if not data:
            self._adaptee.set_list([])
            return
        parts = data.split("-")
        self._adaptee.set_list([int(p) for p in parts])


class GridRenderer(ABC):
    @abstractmethod
    def draw_connection(self, canvas, p1, p2, color):
        pass

    @abstractmethod
    def clear_connections(self, canvas):
        pass


class SimpleRenderer(GridRenderer):
    def draw_connection(self, canvas, p1, p2, color):
        pass

    def clear_connections(self, canvas):
        pass


class LineRenderer(GridRenderer):
    def __init__(self):
        self.lines = []

    def draw_connection(self, canvas, p1, p2, color):
        line = canvas.create_line(p1[0], p1[1], p2[0], p2[1],
                                   fill=color, width=4, arrow=tk.LAST)
        self.lines.append(line)

    def clear_connections(self, canvas):
        for line in self.lines:
            canvas.delete(line)
        self.lines.clear()


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
    def __init__(self, root, renderer: GridRenderer):
        self.root = root
        self.renderer = renderer
        self.root.title("Графический пароль — Мост + Адаптер")
        self.root.geometry("520x920")
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

        self.adaptee = ListAdaptee(self.selected)
        self.adapter = SequenceAdapter(self.adaptee)

        self._build_ui()
        self._update_mode()

    def _build_ui(self):
        tk.Label(self.root, text="Графический пароль",
                 font=("Segoe UI", 16, "bold"),
                 bg=self.bg_color, fg=self.fg_color).pack(pady=(15, 10))

        self.canvas_frame = tk.Frame(self.root, bg=self.bg_color)
        self.canvas_frame.pack(pady=5)

        self.canvas = tk.Canvas(self.canvas_frame, width=340, height=340,
                                 bg=self.bg_color, highlightthickness=0)
        self.canvas.pack()

        self._draw_grid_buttons()

        self.seq_label = tk.Label(self.root, text="", font=("Segoe UI", 14),
                                   bg=self.bg_color, fg=self.fg_color)
        self.seq_label.pack(pady=8)

        self.primary_btn = RoundedButton(
            self.root, text="Войти", command=self._primary_action,
            width=240, height=46, radius=12,
            bg="#4a90d9", fg="white",
            hover_bg="#357abd", active_bg="#2c6aa0",
            font=("Segoe UI", 12, "bold"), parent_bg=self.bg_color
        )
        self.primary_btn.pack(pady=4)

        self.clear_btn = RoundedButton(
            self.root, text="Очистить", command=self._clear_selection,
            width=240, height=46, radius=12,
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
            width=140, height=40, radius=10,
            bg="#6a6a6a", fg="white",
            hover_bg="#7a7a7a", active_bg="#8a8a8a",
            font=("Segoe UI", 11), parent_bg=self.bg_color
        )
        self.login_mode_btn.pack(side=tk.LEFT, padx=4)

        self.create_mode_btn = RoundedButton(
            mode_frame, text="Создать пароль",
            command=lambda: self._set_mode("create"),
            width=160, height=40, radius=10,
            bg="#4a4a4a", fg="white",
            hover_bg="#5a5a5a", active_bg="#6a6a6a",
            font=("Segoe UI", 11), parent_bg=self.bg_color
        )
        self.create_mode_btn.pack(side=tk.LEFT, padx=4)

        self.adapter_btn = RoundedButton(
            self.root, text="Показать строку (Адаптер)",
            command=self._show_adapter_string,
            width=260, height=40, radius=10,
            bg="#4a4a4a", fg="white",
            hover_bg="#5a5a5a", active_bg="#6a6a6a",
            font=("Segoe UI", 11), parent_bg=self.bg_color
        )
        self.adapter_btn.pack(pady=10)

        render_label = tk.Label(self.root, text="Режим отрисовки:",
                                 font=("Segoe UI", 11),
                                 bg=self.bg_color, fg="#a0a0a0")
        render_label.pack(pady=(5, 2))

        render_frame = tk.Frame(self.root, bg=self.bg_color)
        render_frame.pack(pady=2)

        self.simple_btn = RoundedButton(
            render_frame, text="Простой",
            command=lambda: self._set_renderer(SimpleRenderer()),
            width=120, height=38, radius=10,
            bg="#4a4a4a", fg="white",
            hover_bg="#5a5a5a", active_bg="#6a6a6a",
            font=("Segoe UI", 11), parent_bg=self.bg_color
        )
        self.simple_btn.pack(side=tk.LEFT, padx=4)

        self.line_btn = RoundedButton(
            render_frame, text="С линиями",
            command=lambda: self._set_renderer(LineRenderer()),
            width=140, height=38, radius=10,
            bg="#4a4a4a", fg="white",
            hover_bg="#5a5a5a", active_bg="#6a6a6a",
            font=("Segoe UI", 11), parent_bg=self.bg_color
        )
        self.line_btn.pack(side=tk.LEFT, padx=4)

        self.reset_btn = RoundedButton(
            self.root, text="Сбросить сохранённый пароль",
            command=self._reset_password,
            width=260, height=38, radius=10,
            bg="#3a3a3a", fg="#a0a0a0",
            hover_bg="#4a4a4a", active_bg="#5a5a5a",
            font=("Segoe UI", 10), parent_bg=self.bg_color
        )
        self.reset_btn.pack(pady=12)

        self.status_label = tk.Label(self.root, text="", font=("Segoe UI", 10),
                                      bg=self.bg_color, fg=self.fg_color)
        self.status_label.pack(pady=3)

    def _draw_grid_buttons(self):
        self.canvas.delete("all")
        self.button_coords = {}
        self.cell_rects = {}

        start_x, start_y = 45, 45
        step = 85
        size = 65

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
            text = self.canvas.create_text(cx, cy, text=str(i),
                                            fill="white",
                                            font=("Segoe UI", 20, "bold"))

            self.cell_rects[i] = rect

            tag = f"btn_{i}"
            self.canvas.itemconfig(rect, tags=(tag,))
            self.canvas.itemconfig(text, tags=(tag,))
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
        self.adaptee.set_list(self.selected)
        self._update_ui()
        self._redraw_lines()

    def _update_ui(self):
        for i, rect_id in self.cell_rects.items():
            color = "#6a6a6a" if i in self.selected else "#4a4a4a"
            self.canvas.itemconfig(rect_id, fill=color)

        seq_str = " → ".join(map(str, self.selected))
        self.seq_label.config(text=seq_str)

    def _redraw_lines(self):
        self.renderer.clear_connections(self.canvas)

        if len(self.selected) > 1:
            for i in range(len(self.selected) - 1):
                p1 = self.button_coords[self.selected[i]]
                p2 = self.button_coords[self.selected[i + 1]]
                self.renderer.draw_connection(self.canvas, p1, p2,
                                               self.accent_color)

    def _clear_selection(self):
        self.selected = []
        self.adaptee.set_list(self.selected)
        self._update_ui()
        self.renderer.clear_connections(self.canvas)
        self.status_label.config(text="")

    def _show_adapter_string(self):
        string_repr = self.adapter.get_sequence_string()
        messagebox.showinfo(
            "Адаптер",
            f"Внутренний список: {self.selected}\n"
            f"После адаптера (строка): {string_repr}"
        )

    def _set_renderer(self, new_renderer):
        self.renderer.clear_connections(self.canvas)
        self.renderer = new_renderer
        self._redraw_lines()
        self.status_label.config(
            text=f"Рендерер: {new_renderer.__class__.__name__}",
            fg="#4a90d9"
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
        if not validate_sequence(self.selected):
            self.status_label.config(text="Некорректная длина. Нужно от 4 до 9.", fg="#ffaa00")
            return
        if self.password_manager.has_password():
            if not messagebox.askyesno("Подтверждение",
                                        "Пароль уже существует. Перезаписать?"):
                return
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
    app = AppWindow(root, SimpleRenderer())
    root.mainloop()