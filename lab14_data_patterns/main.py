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


class PasswordRecord:
    def __init__(self, password_hash, created_at=None, attempts=0):
        self.password_hash = password_hash
        self.created_at = created_at or ""
        self.attempts = attempts

    def to_dict(self):
        return {
            "password_hash": self.password_hash,
            "created_at": self.created_at,
            "attempts": self.attempts,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            password_hash=data.get("password_hash"),
            created_at=data.get("created_at", ""),
            attempts=data.get("attempts", 0),
        )


class PasswordRepository:
    def __init__(self, filename="graphical_password.json"):
        self.filename = filename
        self._record = None
        self._load()

    def _load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "password_hash" in data:
                    self._record = PasswordRecord.from_dict(data)
            except (json.JSONDecodeError, OSError):
                self._record = None

    def _save(self):
        if self._record is None:
            if os.path.exists(self.filename):
                os.remove(self.filename)
            return
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(self._record.to_dict(), f, ensure_ascii=False, indent=4)

    def find(self):
        return self._record

    def exists(self):
        return self._record is not None

    def save(self, record):
        self._record = record
        self._save()
        return record

    def delete(self):
        self._record = None
        self._save()

    def increment_attempts(self):
        if self._record is None:
            return
        self._record.attempts += 1
        self._save()

    def reset_attempts(self):
        if self._record is None:
            return
        self._record.attempts = 0
        self._save()


class PasswordService:
    def __init__(self, repository=None):
        self.repository = repository or PasswordRepository()

    def has_password(self):
        return self.repository.exists()

    def status(self):
        record = self.repository.find()
        if record is None:
            return False, "Пароль не создан.", {"has_password": False, "attempts": 0}
        return True, "OK", {
            "has_password": True,
            "attempts": record.attempts,
            "created_at": record.created_at,
        }

    def create(self, sequence):
        if self.repository.exists():
            return False, "Пароль уже существует.", None
        record = PasswordRecord(
            password_hash=hash_sequence(sequence),
            created_at=__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        self.repository.save(record)
        return True, "Пароль сохранён.", record.password_hash

    def verify(self, sequence):
        record = self.repository.find()
        if record is None:
            return False, "Пароль не создан.", None
        if hash_sequence(sequence) == record.password_hash:
            self.repository.reset_attempts()
            return True, "Пароль верный. Доступ разрешён.", None
        self.repository.increment_attempts()
        return False, "Пароль неверный. Доступ запрещён.", None

    def reset(self):
        self.repository.delete()
        return True, "Пароль удалён.", None


class PasswordController:
    def __init__(self, root):
        self.root = root
        self.root.title("Графический пароль — Repository")
        self.root.geometry("560x980")
        self.root.resizable(False, False)

        self.bg_color = "#2b2b2b"
        self.fg_color = "white"
        self.root.configure(bg=self.bg_color)

        self.mode = "login"
        self.selected = []
        self.cell_rects = {}
        self.service = PasswordService()

        self._build_ui()
        self._refresh()

    def _build_ui(self):
        tk.Label(self.root, text="Графический пароль",
                 font=("Segoe UI", 16, "bold"),
                 bg=self.bg_color, fg=self.fg_color).pack(pady=(12, 4))

        self.attempts_label = tk.Label(
            self.root, text="", font=("Segoe UI", 10, "bold"),
            bg=self.bg_color, fg="#4caf50"
        )
        self.attempts_label.pack(pady=2)

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
        self.seq_label.config(text=" → ".join(map(str, self.selected)))

        if self.mode == "login":
            self.primary_btn.set_text("Войти")
            self.login_mode_btn.set_colors("#6a6a6a", "#7a7a7a", "#8a8a8a")
            self.create_mode_btn.set_colors("#4a4a4a", "#5a5a5a", "#6a6a6a")
        else:
            self.primary_btn.set_text("Сохранить пароль")
            self.login_mode_btn.set_colors("#4a4a4a", "#5a5a5a", "#6a6a6a")
            self.create_mode_btn.set_colors("#6a6a6a", "#7a7a7a", "#8a8a8a")

        ok, _, data = self.service.status()
        if ok and data.get("has_password"):
            self.attempts_label.config(
                text=f"Пароль создан. Неудачных попыток: {data['attempts']}",
                fg="#4caf50" if data["attempts"] == 0 else "#ffaa00"
            )
        else:
            self.attempts_label.config(text="Пароль не создан", fg="#a0a0a0")

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
        ok, msg = validate_sequence(self.selected)
        if not ok:
            self.status_label.config(text=msg, fg="#ff4444")
            return
        if self.service.has_password():
            if not messagebox.askyesno("Подтверждение",
                                        "Пароль уже существует. Перезаписать?"):
                return
            self.service.reset()
        success, message, _ = self.service.create(self.selected)
        self._show_result(success, message)
        if success:
            self.selected = []
        self._refresh()

    def _login(self):
        if not self.selected:
            self.status_label.config(text="Введите последовательность.", fg="#ffaa00")
            return
        ok, msg = validate_sequence(self.selected)
        if not ok:
            self.status_label.config(text=msg, fg="#ff4444")
            return
        success, message, _ = self.service.verify(self.selected)
        self._show_result(success, message)
        if success:
            self.selected = []
        self._refresh()

    def _reset_password(self):
        success, message, _ = self.service.reset()
        self._show_result(success, message)
        self.selected = []
        self._refresh()

    def _show_result(self, success, message):
        if success:
            self.status_label.config(text=message, fg="#4caf50")
            messagebox.showinfo("Успех", message)
        else:
            self.status_label.config(text=message, fg="#ff4444")
            messagebox.showerror("Ошибка", message)


if __name__ == "__main__":
    root = tk.Tk()
    app = PasswordController(root)
    root.mainloop()