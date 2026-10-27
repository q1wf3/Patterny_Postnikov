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


class GraphicalPasswordApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Графический пароль — вариант 8")
        self.root.geometry("420x640")
        self.root.configure(bg="#2b2b2b")
        self.root.resizable(False, False)

        self.password_manager = PasswordManager()

        self.mode = "login"
        self.selected = []
        self.buttons = {}

        self._build_ui()
        self._update_mode()

    def _build_ui(self):
        grid_frame = tk.Frame(self.root, bg="#2b2b2b")
        grid_frame.pack(pady=30)

        for i in range(1, 10):
            btn = tk.Button(
                grid_frame,
                text=str(i),
                font=("Segoe UI", 18),
                width=4,
                height=2,
                bg="#4a4a4a",
                fg="white",
                relief=tk.FLAT,
                bd=0,
                highlightthickness=0,
                activebackground="#5a5a5a",
                activeforeground="white",
                command=lambda num=i: self._select_cell(num)
            )
            row = (i - 1) // 3
            col = (i - 1) % 3
            btn.grid(row=row, column=col, padx=8, pady=8)
            self.buttons[i] = btn

        self.sequence_label = tk.Label(
            self.root,
            text="",
            font=("Segoe UI", 14),
            bg="#2b2b2b",
            fg="#a0a0a0"
        )
        self.sequence_label.pack(pady=10)

        btn_frame = tk.Frame(self.root, bg="#2b2b2b")
        btn_frame.pack(pady=10)

        self.primary_btn = tk.Button(
            btn_frame,
            text="Войти",
            font=("Segoe UI", 13),
            width=22,
            bg="#4a90d9",
            fg="white",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            activebackground="#357abd",
            activeforeground="white",
            command=self._primary_action
        )
        self.primary_btn.pack(pady=6)

        clear_btn = tk.Button(
            btn_frame,
            text="Очистить",
            font=("Segoe UI", 13),
            width=22,
            bg="#4a4a4a",
            fg="white",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            activebackground="#6a6a6a",
            activeforeground="white",
            command=self._clear_selection
        )
        clear_btn.pack(pady=6)

        mode_frame = tk.Frame(self.root, bg="#2b2b2b")
        mode_frame.pack(pady=10)

        self.login_mode_btn = tk.Button(
            mode_frame,
            text="Вход",
            font=("Segoe UI", 12),
            width=14,
            bg="#6a6a6a",
            fg="white",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            activebackground="#7a7a7a",
            activeforeground="white",
            command=lambda: self._set_mode("login")
        )
        self.login_mode_btn.pack(side=tk.LEFT, padx=5)

        self.create_mode_btn = tk.Button(
            mode_frame,
            text="Создать пароль",
            font=("Segoe UI", 12),
            width=16,
            bg="#4a4a4a",
            fg="white",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            activebackground="#7a7a7a",
            activeforeground="white",
            command=lambda: self._set_mode("create")
        )
        self.create_mode_btn.pack(side=tk.LEFT, padx=5)

        reset_btn = tk.Button(
            self.root,
            text="Сбросить сохранённый пароль",
            font=("Segoe UI", 10),
            width=28,
            bg="#3a3a3a",
            fg="#a0a0a0",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            activebackground="#5a5a5a",
            activeforeground="white",
            command=self._reset_password
        )
        reset_btn.pack(pady=20)

        self.status_label = tk.Label(
            self.root,
            text="",
            font=("Segoe UI", 10),
            bg="#2b2b2b",
            fg="#a0a0a0"
        )
        self.status_label.pack(pady=5)

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
            if num in self.selected:
                btn.config(bg="#6a6a6a", relief=tk.SUNKEN)
            else:
                btn.config(bg="#4a4a4a", relief=tk.FLAT)

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
            self.primary_btn.config(text="Войти", command=self._primary_action)
            self.login_mode_btn.config(bg="#6a6a6a", relief=tk.SUNKEN)
            self.create_mode_btn.config(bg="#4a4a4a", relief=tk.FLAT)
        else:
            self.primary_btn.config(text="Сохранить пароль", command=self._primary_action)
            self.login_mode_btn.config(bg="#4a4a4a", relief=tk.FLAT)
            self.create_mode_btn.config(bg="#6a6a6a", relief=tk.SUNKEN)

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

    def _reset_password(self):
        if not self.password_manager.has_password():
            self.status_label.config(text="Пароль не установлен.", fg="#ffaa00")
            return
        if messagebox.askyesno("Подтверждение", "Удалить сохранённый графический пароль?"):
            self.password_manager.reset_password()
            messagebox.showinfo("Успех", "Пароль удалён.")
            self._clear_selection()


if __name__ == "__main__":
    root = tk.Tk()
    app = GraphicalPasswordApp(root)
    root.mainloop()