import tkinter as tk
from tkinter import messagebox
import hashlib
import json
import os
import queue
import threading
import time
from datetime import datetime


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
    return hashlib.sha256(seq_str.encode("utf-8")).hexdigest()


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


class PasswordStore:
    def __init__(self, filename="graphical_password.json"):
        self.filename = filename

    def _read(self):
        if not os.path.exists(self.filename):
            return None
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def _write(self, data):
        if data is None:
            try:
                if os.path.exists(self.filename):
                    os.remove(self.filename)
            except OSError:
                pass
            return
        try:
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except OSError:
            pass

    def get_hash(self):
        data = self._read()
        return data.get("password_hash") if data else None

    def set_hash(self, password_hash):
        self._write({
            "password_hash": password_hash,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

    def clear(self):
        self._write(None)


class Task:
    def __init__(self, kind, sequence, callback):
        self.kind = kind
        self.sequence = sequence
        self.callback = callback


class Worker(threading.Thread):
    def __init__(self, task_queue, result_queue, store):
        super().__init__(daemon=True, name="PasswordWorker")
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.store = store
        self._stop_event = threading.Event()

    def stop_worker(self):
        self._stop_event.set()
        try:
            self.task_queue.put_nowait(None)
        except Exception:
            pass

    def run(self):
        while not self._stop_event.is_set():
            try:
                task = self.task_queue.get(timeout=0.3)
            except queue.Empty:
                continue
            if task is None:
                break
            try:
                result = self._process_task(task)
            except Exception as e:
                result = (False, f"Ошибка обработки: {e}")
            try:
                self.result_queue.put((task.callback, result))
            except Exception:
                pass
            try:
                self.task_queue.task_done()
            except ValueError:
                pass

    def _process_task(self, task):
        time.sleep(2)
        if task.kind == "create":
            ok, msg = validate_sequence(task.sequence)
            if not ok:
                return False, msg
            if self.store.get_hash() is not None:
                return False, "Пароль уже существует."
            self.store.set_hash(hash_sequence(task.sequence))
            return True, "Пароль сохранён."

        if task.kind == "verify":
            ok, msg = validate_sequence(task.sequence)
            if not ok:
                return False, msg
            stored = self.store.get_hash()
            if stored is None:
                return False, "Пароль не создан."
            if hash_sequence(task.sequence) == stored:
                return True, "Пароль верный. Доступ разрешён."
            return False, "Пароль неверный. Доступ запрещён."

        if task.kind == "reset":
            self.store.clear()
            return True, "Пароль удалён."

        if task.kind == "status":
            return True, "OK" if self.store.get_hash() else "Пароль не создан."

        return False, "Неизвестная задача."


class ProducerConsumerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Графический пароль — Producer-Consumer")
        self.root.geometry("560x980")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.bg_color = "#2b2b2b"
        self.fg_color = "white"
        self.root.configure(bg=self.bg_color)

        self.mode = "login"
        self.selected = []
        self.cell_rects = {}
        self.busy = False
        self._pending_id = None

        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.store = PasswordStore()

        self.worker = Worker(self.task_queue, self.result_queue, self.store)
        self.worker.start()

        self._build_ui()
        self._refresh()
        self._poll_results()
        self._enqueue_status()

    def _build_ui(self):
        tk.Label(self.root, text="Графический пароль",
                 font=("Segoe UI", 16, "bold"),
                 bg=self.bg_color, fg=self.fg_color).pack(pady=(12, 4))

        self.status_badge = tk.Label(
            self.root, text="Инициализация...", font=("Segoe UI", 10, "bold"),
            bg=self.bg_color, fg="#a0a0a0"
        )
        self.status_badge.pack(pady=2)

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

        self.queue_label = tk.Label(self.root, text="Очередь: 0",
                                     font=("Segoe UI", 9),
                                     bg=self.bg_color, fg="#a0a0a0")
        self.queue_label.pack(pady=(4, 10))

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
        if self.busy:
            return
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

        self.queue_label.config(text=f"Очередь: {self.task_queue.qsize()}")

    def _clear_selection(self):
        if self.busy:
            return
        self.selected = []
        self._refresh()
        self.status_label.config(text="")

    def _set_mode(self, mode):
        if self.busy:
            return
        self.mode = mode
        self.selected = []
        self._refresh()

    def _primary_action(self):
        if self.busy:
            return
        if not self.selected:
            self.status_label.config(text="Выберите последовательность.", fg="#ffaa00")
            return
        ok, msg = validate_sequence(self.selected)
        if not ok:
            self.status_label.config(text=msg, fg="#ff4444")
            return
        sequence = list(self.selected)
        if self.mode == "login":
            self._enqueue("verify", sequence, self._on_action_done)
        else:
            self._enqueue("create", sequence, self._on_action_done)

    def _reset_password(self):
        if self.busy:
            return
        self._enqueue("reset", None, self._on_action_done)

    def _enqueue_status(self):
        self._enqueue("status", None, self._on_status_done, show_busy=False)

    def _enqueue(self, kind, sequence, callback, show_busy=True):
        if show_busy:
            self.busy = True
            self.primary_btn.set_text("Обработка...")
        self.task_queue.put(Task(kind, sequence, callback))
        self._refresh()
        if show_busy:
            self._pending_id = self.root.after(3000, self._safety_unlock)

    def _safety_unlock(self):
        self._pending_id = None
        if self.busy:
            self.busy = False
            self.status_label.config(
                text="Превышено время ожидания. Попробуйте ещё раз.",
                fg="#ff4444"
            )
            self._refresh()

    def _cancel_pending(self):
        if self._pending_id is not None:
            try:
                self.root.after_cancel(self._pending_id)
            except Exception:
                pass
            self._pending_id = None

    def _poll_results(self):
        try:
            while True:
                callback, result = self.result_queue.get_nowait()
                try:
                    if callback:
                        callback(result)
                    else:
                        self.busy = False
                        self._refresh()
                except Exception as e:
                    self.busy = False
                    self.status_label.config(text=f"Ошибка UI: {e}", fg="#ff4444")
                    self._refresh()
        except queue.Empty:
            pass
        self.root.after(50, self._poll_results)

    def _on_status_done(self, result):
        success, message = result
        if success:
            self.status_badge.config(text="Сервис готов", fg="#4caf50")
        else:
            self.status_badge.config(text=message, fg="#a0a0a0")
        self._refresh()

    def _on_action_done(self, result):
        self._cancel_pending()
        self.busy = False
        success, message = result
        if success:
            self.status_label.config(text=message, fg="#4caf50")
            messagebox.showinfo("Успех", message)
            self.selected = []
        else:
            self.status_label.config(text=message, fg="#ff4444")
            messagebox.showerror("Ошибка", message)
        self._refresh()

    def _on_close(self):
        self._cancel_pending()
        try:
            self.worker.stop_worker()
        except Exception:
            pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ProducerConsumerApp(root)
    root.mainloop()