import tkinter as tk
from tkinter import messagebox
from abc import ABC, abstractmethod
from copy import deepcopy
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


class PasswordFactory(ABC):
    @abstractmethod
    def create_point(self, parent, number, command, selected=False):
        pass

    @abstractmethod
    def create_button(self, parent, text, command, accent=False):
        pass

    @abstractmethod
    def get_colors(self):
        pass


class DarkPasswordFactory(PasswordFactory):
    def create_point(self, parent, number, command, selected=False):
        bg = "#6a6a6a" if selected else "#4a4a4a"
        relief = tk.SUNKEN if selected else tk.FLAT
        return tk.Button(
            parent,
            text=str(number),
            font=("Segoe UI", 18),
            width=4,
            height=2,
            bg=bg,
            fg="white",
            relief=relief,
            bd=0,
            highlightthickness=0,
            activebackground="#5a5a5a",
            activeforeground="white",
            command=command
        )

    def create_button(self, parent, text, command, accent=False):
        bg = "#4a90d9" if accent else "#4a4a4a"
        active_bg = "#357abd" if accent else "#6a6a6a"
        return tk.Button(
            parent,
            text=text,
            font=("Segoe UI", 12),
            width=22,
            bg=bg,
            fg="white",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            activebackground=active_bg,
            activeforeground="white",
            command=command
        )

    def get_colors(self):
        return {
            "bg": "#2b2b2b",
            "fg": "#ffffff",
            "accent": "#4a90d9",
            "card_bg": "#3a3a3a",
            "card_selected": "#4a90d9",
            "card_fg": "#e0e0e0"
        }


class LightPasswordFactory(PasswordFactory):
    def create_point(self, parent, number, command, selected=False):
        bg = "#4a90d9" if selected else "#ffffff"
        fg = "white" if selected else "#333333"
        relief = tk.SUNKEN if selected else tk.FLAT
        return tk.Button(
            parent,
            text=str(number),
            font=("Segoe UI", 18),
            width=4,
            height=2,
            bg=bg,
            fg=fg,
            relief=relief,
            bd=1,
            highlightthickness=1,
            highlightbackground="#d0d0d0",
            activebackground="#e0e0e0",
            activeforeground="#333333",
            command=command
        )

    def create_button(self, parent, text, command, accent=False):
        bg = "#4a90d9" if accent else "#ffffff"
        fg = "white" if accent else "#333333"
        active_bg = "#357abd" if accent else "#e0e0e0"
        active_fg = "white" if accent else "#333333"
        return tk.Button(
            parent,
            text=text,
            font=("Segoe UI", 12),
            width=22,
            bg=bg,
            fg=fg,
            relief=tk.FLAT,
            bd=1,
            highlightthickness=1,
            highlightbackground="#d0d0d0",
            activebackground=active_bg,
            activeforeground=active_fg,
            command=command
        )

    def get_colors(self):
        return {
            "bg": "#f5f5f5",
            "fg": "#333333",
            "accent": "#4a90d9",
            "card_bg": "#ffffff",
            "card_selected": "#4a90d9",
            "card_fg": "#333333"
        }


class PasswordPattern:
    def __init__(self, name, sequence):
        self.name = name
        self.sequence = sequence

    def clone(self):
        return deepcopy(self)


CROSS_PATTERN = PasswordPattern("Крест", [2, 5, 8, 4, 6])
SQUARE_PATTERN = PasswordPattern("Квадрат", [1, 2, 3, 6, 9, 8, 7, 4])
ZIGZAG_PATTERN = PasswordPattern("Зигзаг", [1, 2, 4, 3, 5, 7, 6, 8, 9])

PATTERNS = [CROSS_PATTERN, SQUARE_PATTERN, ZIGZAG_PATTERN]


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
            json.dump({"password_hash": self.password_hash}, f, ensure_ascii=False, indent=4)

    def has_password(self):
        return self.password_hash is not None

    def create_password(self, sequence):
        if not validate_sequence(sequence):
            raise ValueError("Некорректная последовательность. Длина от 4 до 9, без повторений.")
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


class PatternCard(tk.Frame):
    def __init__(self, parent, pattern, on_click, colors):
        super().__init__(parent, bg=colors["card_bg"], bd=0, highlightthickness=0)
        self.pattern = pattern
        self.on_click = on_click
        self.colors = colors
        self.selected = False

        self.name_label = tk.Label(
            self,
            text=pattern.name,
            font=("Segoe UI", 12, "bold"),
            bg=colors["card_bg"],
            fg=colors["card_fg"],
            anchor="w"
        )
        self.name_label.pack(fill=tk.X, padx=10, pady=(8, 2))

        self.seq_label = tk.Label(
            self,
            text=" → ".join(map(str, pattern.sequence)),
            font=("Segoe UI", 10),
            bg=colors["card_bg"],
            fg="#999999",
            anchor="w"
        )
        self.seq_label.pack(fill=tk.X, padx=10, pady=(0, 8))

        for w in (self, self.name_label, self.seq_label):
            w.bind("<Button-1>", self._click)

    def _click(self, _):
        self.on_click(self.pattern)

    def set_selected(self, selected):
        self.selected = selected
        bg = self.colors["card_selected"] if selected else self.colors["card_bg"]
        fg = "white" if selected else self.colors["card_fg"]
        seq_fg = "#e0e0e0" if selected else "#999999"
        self.config(bg=bg)
        self.name_label.config(bg=bg, fg=fg)
        self.seq_label.config(bg=bg, fg=seq_fg)


class GraphicalPasswordApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Графический пароль — вариант 8")
        self.root.geometry("560x880")
        self.root.resizable(False, False)

        self.factory = DarkPasswordFactory()
        self.password_manager = PasswordManager()

        self.mode = "login"
        self.selected = []
        self.buttons = {}
        self.patterns = [p.clone() for p in PATTERNS]
        self.current_pattern = None
        self.pattern_cards = []

        self._build_ui()
        self._update_mode()
        self._update_sequence()

    def _build_ui(self):
        colors = self.factory.get_colors()
        self.root.configure(bg=colors["bg"])

        self.main_frame = tk.Frame(self.root, bg=colors["bg"])
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.title_label = tk.Label(
            self.main_frame,
            text="Графический пароль",
            font=("Segoe UI", 16, "bold"),
            bg=colors["bg"],
            fg=colors["fg"]
        )
        self.title_label.pack(pady=(15, 5))

        self.grid_frame = tk.Frame(self.main_frame, bg=colors["bg"])
        self.grid_frame.pack(pady=10)

        for i in range(1, 10):
            btn = self.factory.create_point(
                self.grid_frame, i,
                lambda num=i: self._select_cell(num),
                selected=False
            )
            row = (i - 1) // 3
            col = (i - 1) % 3
            btn.grid(row=row, column=col, padx=8, pady=8)
            self.buttons[i] = btn

        self.sequence_label = tk.Label(
            self.main_frame,
            text="",
            font=("Segoe UI", 14),
            bg=colors["bg"],
            fg=colors["fg"]
        )
        self.sequence_label.pack(pady=8)

        btn_frame = tk.Frame(self.main_frame, bg=colors["bg"])
        btn_frame.pack(pady=5)

        self.primary_btn = self.factory.create_button(
            btn_frame, "Войти", self._primary_action, accent=True
        )
        self.primary_btn.pack(pady=4)

        self.clear_btn = self.factory.create_button(
            btn_frame, "Очистить", self._clear_selection
        )
        self.clear_btn.pack(pady=4)

        mode_frame = tk.Frame(self.main_frame, bg=colors["bg"])
        mode_frame.pack(pady=8)

        self.login_mode_btn = self.factory.create_button(
            mode_frame, "Вход", lambda: self._set_mode("login")
        )
        self.login_mode_btn.config(width=14)
        self.login_mode_btn.pack(side=tk.LEFT, padx=5)

        self.create_mode_btn = self.factory.create_button(
            mode_frame, "Создать пароль", lambda: self._set_mode("create")
        )
        self.create_mode_btn.config(width=16)
        self.create_mode_btn.pack(side=tk.LEFT, padx=5)

        patterns_frame = tk.Frame(self.main_frame, bg=colors["bg"])
        patterns_frame.pack(pady=10, fill=tk.X, padx=20)

        tk.Label(
            patterns_frame,
            text="Шаблоны:",
            font=("Segoe UI", 12, "bold"),
            bg=colors["bg"],
            fg=colors["fg"],
            anchor="w"
        ).pack(fill=tk.X)

        self.cards_container = tk.Frame(patterns_frame, bg=colors["bg"])
        self.cards_container.pack(fill=tk.X, pady=5)

        self._refresh_patterns()

        pattern_buttons = tk.Frame(patterns_frame, bg=colors["bg"])
        pattern_buttons.pack(pady=5, fill=tk.X)

        self.apply_btn = self.factory.create_button(
            pattern_buttons, "Применить шаблон", self._apply_pattern
        )
        self.apply_btn.pack(side=tk.LEFT, padx=4, expand=True)

        self.clone_btn = self.factory.create_button(
            pattern_buttons, "Клонировать шаблон", self._clone_pattern
        )
        self.clone_btn.pack(side=tk.LEFT, padx=4, expand=True)

        self.theme_btn = self.factory.create_button(
            self.main_frame, "Сменить тему", self._toggle_theme
        )
        self.theme_btn.pack(pady=10)

        self.status_label = tk.Label(
            self.main_frame,
            text="",
            font=("Segoe UI", 10),
            bg=colors["bg"],
            fg=colors["fg"]
        )
        self.status_label.pack(pady=5)

    def _refresh_patterns(self):
        colors = self.factory.get_colors()
        for card in self.pattern_cards:
            card.destroy()
        self.pattern_cards = []

        for p in self.patterns:
            card = PatternCard(self.cards_container, p, self._on_pattern_click, colors)
            card.pack(fill=tk.X, pady=3)
            self.pattern_cards.append(card)

    def _on_pattern_click(self, pattern):
        self.current_pattern = pattern
        for card in self.pattern_cards:
            card.set_selected(card.pattern is pattern)

        seq_str = " → ".join(map(str, pattern.sequence))
        answer = messagebox.askyesno(
            "Применение шаблона",
            f"Применить шаблон «{pattern.name}»?\n\n"
            f"Последовательность: {seq_str}"
        )
        if answer:
            self._apply_pattern_object(pattern)
        else:
            self.status_label.config(
                text=f"Шаблон «{pattern.name}» выбран (не применён).",
                fg="#ffaa00"
            )

    def _apply_pattern_object(self, pattern):
        self.selected = list(pattern.sequence)
        self._update_sequence()
        self.status_label.config(
            text=f"Использован шаблон: {pattern.name}",
            fg="#4a90d9" if isinstance(self.factory, LightPasswordFactory) else "#6ab0ff"
        )
        messagebox.showinfo(
            "Шаблон применён",
            f"Использован шаблон: «{pattern.name}»\n"
            f"Последовательность: {' → '.join(map(str, pattern.sequence))}"
        )

    def _apply_pattern(self):
        if not self.current_pattern:
            self.status_label.config(text="Сначала выберите шаблон.", fg="#ffaa00")
            return
        self._apply_pattern_object(self.current_pattern)

    def _select_cell(self, number):
        if number in self.selected:
            self.status_label.config(text="Эта ячейка уже выбрана.", fg="#ffaa00")
            return
        if len(self.selected) >= 9:
            self.status_label.config(text="Максимальная длина — 9.", fg="#ffaa00")
            return
        self.selected.append(number)
        self._update_sequence()

    def _update_sequence(self):
        seq_str = " → ".join(map(str, self.selected))
        self.sequence_label.config(text=seq_str)
        for num, btn in self.buttons.items():
            self._update_button_style(num, btn)

    def _update_button_style(self, num, btn):
        is_selected = num in self.selected
        if isinstance(self.factory, LightPasswordFactory):
            btn.config(
                bg="#4a90d9" if is_selected else "#ffffff",
                fg="white" if is_selected else "#333333",
                relief=tk.SUNKEN if is_selected else tk.FLAT
            )
        else:
            btn.config(
                bg="#6a6a6a" if is_selected else "#4a4a4a",
                relief=tk.SUNKEN if is_selected else tk.FLAT
            )

    def _clear_selection(self):
        self.selected = []
        self._update_sequence()
        self.status_label.config(text="")

    def _set_mode(self, mode):
        self.mode = mode
        self._clear_selection()
        self._update_mode()

    def _update_mode(self):
        if self.mode == "login":
            self.primary_btn.config(text="Войти")
            if isinstance(self.factory, LightPasswordFactory):
                self.login_mode_btn.config(bg="#4a90d9", fg="white")
                self.create_mode_btn.config(bg="#ffffff", fg="#333333")
            else:
                self.login_mode_btn.config(bg="#6a6a6a", fg="white")
                self.create_mode_btn.config(bg="#4a4a4a", fg="white")
        else:
            self.primary_btn.config(text="Сохранить пароль")
            if isinstance(self.factory, LightPasswordFactory):
                self.login_mode_btn.config(bg="#ffffff", fg="#333333")
                self.create_mode_btn.config(bg="#4a90d9", fg="white")
            else:
                self.login_mode_btn.config(bg="#4a4a4a", fg="white")
                self.create_mode_btn.config(bg="#6a6a6a", fg="white")

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
            if not messagebox.askyesno("Подтверждение", "Пароль уже существует. Перезаписать?"):
                return
        try:
            self.password_manager.create_password(self.selected)
            messagebox.showinfo("Успех", "Графический пароль успешно создан.")
            self._clear_selection()
        except ValueError as e:
            self.status_label.config(text=str(e), fg="#ff4444")

    def _login(self):
        if not self.password_manager.has_password():
            messagebox.showwarning("Внимание", "Пароль не создан. Сначала создайте пароль.")
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

    def _clone_pattern(self):
        if not self.current_pattern:
            self.status_label.config(text="Сначала выберите шаблон.", fg="#ffaa00")
            return
        cloned = self.current_pattern.clone()
        cloned.name = f"{cloned.name} — копия"
        self.patterns.append(cloned)
        self._refresh_patterns()
        for card in self.pattern_cards:
            card.set_selected(card.pattern is self.current_pattern)
        self.status_label.config(text=f"Создана копия: {cloned.name}")
        messagebox.showinfo("Клонирование", f"Создана копия шаблона: «{cloned.name}»")

    def _toggle_theme(self):
        if isinstance(self.factory, DarkPasswordFactory):
            self.factory = LightPasswordFactory()
        else:
            self.factory = DarkPasswordFactory()
        self._rebuild_ui()

    def _rebuild_ui(self):
        self.current_pattern = None
        for widget in self.root.winfo_children():
            widget.destroy()
        self.buttons = {}
        self.pattern_cards = []
        self._build_ui()
        self._update_mode()
        self._update_sequence()


if __name__ == "__main__":
    root = tk.Tk()
    app = GraphicalPasswordApp(root)
    root.mainloop()