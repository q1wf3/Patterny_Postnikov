import tkinter as tk
from tkinter import messagebox
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


class PasswordModel:
    def __init__(self):
        self._filename = "graphical_password.json"
        self._selected = []
        self._password_hash = None
        self._load()

    def _load(self):
        if os.path.exists(self._filename):
            try:
                with open(self._filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._password_hash = data.get("password_hash")
            except (json.JSONDecodeError, FileNotFoundError):
                self._password_hash = None

    def _save(self):
        with open(self._filename, 'w', encoding='utf-8') as f:
            json.dump({"password_hash": self._password_hash}, f,
                      ensure_ascii=False, indent=4)

    def get_selected(self):
        return list(self._selected)

    def select_cell(self, number):
        if number in self._selected:
            return False, "Эта ячейка уже выбрана."
        if len(self._selected) >= 9:
            return False, "Максимальная длина — 9."
        self._selected.append(number)
        return True, ""

    def clear(self):
        self._selected = []

    def has_password(self):
        return self._password_hash is not None

    def create_password(self):
        ok, msg = validate_sequence(self._selected)
        if not ok:
            return False, msg
        self._password_hash = hash_sequence(self._selected)
        self._save()
        return True, "Графический пароль успешно создан."

    def verify_password(self):
        if not self.has_password():
            return False, "Пароль не создан. Сначала создайте пароль."
        ok, msg = validate_sequence(self._selected)
        if not ok:
            return False, msg
        if hash_sequence(self._selected) == self._password_hash:
            return True, "Пароль верный. Доступ разрешён."
        return False, "Пароль неверный. Доступ запрещён."

    def reset_password(self):
        self._password_hash = None
        if os.path.exists(self._filename):
            os.remove(self._filename)


class PasswordView:
    def __init__(self, root, parent_bg="#2b2b2b"):
        self.root = root
        self.parent_bg = parent_bg
        self.fg_color = "white"
        self.canvas = None
        self.cell_rects = {}
        self.seq_label = None
        self.status_label = None
        self.primary_btn = None
        self.login_mode_btn = None
        self.create_mode_btn = None
        self.controller = None

    def set_controller(self, controller):
        self.controller = controller

    def build(self):
        self.root.title("Графический пароль — MVC")
        self.root.geometry("540x900")
        self.root.resizable(False, False)
        self.root.configure(bg=self.parent_bg)

        tk.Label(self.root, text="Графический пароль",
                 font=("Segoe UI", 16, "bold"),
                 bg=self.parent_bg, fg=self.fg_color).pack(pady=(12, 6))

        canvas_frame = tk.Frame(self.root, bg=self.parent_bg)
        canvas_frame.pack(pady=4)

        self.canvas = tk.Canvas(canvas_frame, width=280, height=280,
                                 bg=self.parent_bg, highlightthickness=0)
        self.canvas.pack()

        self._draw_grid()

        self.seq_label = tk.Label(self.root, text="", font=("Segoe UI", 13),
                                   bg=self.parent_bg, fg=self.fg_color)
        self.seq_label.pack(pady=4)

        self.primary_btn = RoundedButton(
            self.root, text="Войти",
            command=lambda: self.controller.on_primary_action(),
            width=240, height=42, radius=12,
            bg="#4a90d9", fg="white",
            hover_bg="#357abd", active_bg="#2c6aa0",
            font=("Segoe UI", 12, "bold"), parent_bg=self.parent_bg
        )
        self.primary_btn.pack(pady=3)

        clear_btn = RoundedButton(
            self.root, text="Очистить",
            command=lambda: self.controller.on_clear(),
            width=240, height=42, radius=12,
            bg="#4a4a4a", fg="white",
            hover_bg="#5a5a5a", active_bg="#6a6a6a",
            font=("Segoe UI", 12), parent_bg=self.parent_bg
        )
        clear_btn.pack(pady=3)

        mode_frame = tk.Frame(self.root, bg=self.parent_bg)
        mode_frame.pack(pady=6)

        self.login_mode_btn = RoundedButton(
            mode_frame, text="Вход",
            command=lambda: self.controller.on_mode_changed("login"),
            width=140, height=38, radius=10,
            bg="#6a6a6a", fg="white",
            hover_bg="#7a7a7a", active_bg="#8a8a8a",
            font=("Segoe UI", 11), parent_bg=self.parent_bg
        )
        self.login_mode_btn.pack(side=tk.LEFT, padx=4)

        self.create_mode_btn = RoundedButton(
            mode_frame, text="Создать пароль",
            command=lambda: self.controller.on_mode_changed("create"),
            width=160, height=38, radius=10,
            bg="#4a4a4a", fg="white",
            hover_bg="#5a5a5a", active_bg="#6a6a6a",
            font=("Segoe UI", 11), parent_bg=self.parent_bg
        )
        self.create_mode_btn.pack(side=tk.LEFT, padx=4)

        reset_btn = RoundedButton(
            self.root, text="Сбросить сохранённый пароль",
            command=lambda: self.controller.on_reset_password(),
            width=260, height=36, radius=10,
            bg="#3a3a3a", fg="#a0a0a0",
            hover_bg="#4a4a4a", active_bg="#5a5a5a",
            font=("Segoe UI", 10), parent_bg=self.parent_bg
        )
        reset_btn.pack(pady=10)

        self.status_label = tk.Label(self.root, text="", font=("Segoe UI", 10),
                                      bg=self.parent_bg, fg=self.fg_color,
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
                                  lambda e, num=i: self.controller.on_cell_clicked(num))

    def render(self, selected, mode, status_text="", status_color="#ffffff"):
        for i, rect_id in self.cell_rects.items():
            color = "#6a6a6a" if i in selected else "#4a4a4a"
            self.canvas.itemconfig(rect_id, fill=color)

        seq_str = " → ".join(map(str, selected))
        self.seq_label.config(text=seq_str)

        if mode == "login":
            self.primary_btn.set_text("Войти")
            self.login_mode_btn.set_colors("#6a6a6a", "#7a7a7a", "#8a8a8a")
            self.create_mode_btn.set_colors("#4a4a4a", "#5a5a5a", "#6a6a6a")
        else:
            self.primary_btn.set_text("Сохранить пароль")
            self.login_mode_btn.set_colors("#4a4a4a", "#5a5a5a", "#6a6a6a")
            self.create_mode_btn.set_colors("#6a6a6a", "#7a7a7a", "#8a8a8a")

        self.status_label.config(text=status_text, fg=status_color)

    def show_info(self, title, message):
        messagebox.showinfo(title, message)

    def show_error(self, title, message):
        messagebox.showerror(title, message)

    def show_warning(self, title, message):
        messagebox.showwarning(title, message)

    def ask_yes_no(self, title, message):
        return messagebox.askyesno(title, message)


class PasswordController:
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.mode = "login"
        self.view.set_controller(self)

    def start(self):
        self.view.build()
        self._refresh()

    def _refresh(self, status_text="", status_color="#ffffff"):
        self.view.render(
            self.model.get_selected(),
            self.mode,
            status_text,
            status_color
        )

    def on_cell_clicked(self, number):
        ok, msg = self.model.select_cell(number)
        if ok:
            self._refresh()
        else:
            self._refresh(msg, "#ffaa00")

    def on_clear(self):
        self.model.clear()
        self._refresh()

    def on_mode_changed(self, mode):
        self.mode = mode
        self.model.clear()
        self._refresh()

    def on_primary_action(self):
        if self.mode == "login":
            self._login()
        else:
            self._create_password()

    def _create_password(self):
        if not self.model.get_selected():
            self._refresh("Выберите последовательность.", "#ffaa00")
            return
        ok, msg = validate_sequence(self.model.get_selected())
        if not ok:
            self._refresh(msg, "#ff4444")
            self.view.show_error("Ошибка валидации", msg)
            return
        if self.model.has_password():
            if not self.view.ask_yes_no("Подтверждение",
                                        "Пароль уже существует. Перезаписать?"):
                return
            self.model.reset_password()
        ok, msg = self.model.create_password()
        if ok:
            self.view.show_info("Успех", msg)
            self.model.clear()
            self._refresh()
        else:
            self._refresh(msg, "#ff4444")
            self.view.show_error("Ошибка", msg)

    def _login(self):
        if not self.model.get_selected():
            self._refresh("Введите последовательность.", "#ffaa00")
            return
        ok, msg = self.model.verify_password()
        if ok:
            self.view.show_info("Успех", msg)
            self.model.clear()
            self._refresh()
        else:
            self.view.show_error("Ошибка", msg)
            self.model.clear()
            self._refresh()

    def on_reset_password(self):
        if not self.model.has_password():
            self._refresh("Пароль не установлен.", "#ffaa00")
            return
        if self.view.ask_yes_no("Подтверждение",
                                "Удалить сохранённый графический пароль?"):
            self.model.reset_password()
            self.view.show_info("Успех", "Пароль удалён.")
            self.model.clear()
            self._refresh()


if __name__ == "__main__":
    root = tk.Tk()
    model = PasswordModel()
    view = PasswordView(root)
    controller = PasswordController(model, view)
    controller.start()
    root.mainloop()