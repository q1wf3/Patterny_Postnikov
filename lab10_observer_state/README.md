# Лабораторная работа №10 — Поведенческие паттерны: Наблюдатель, Состояние

**Тема:** Поведенческие паттерны проектирования: Наблюдатель (Observer), Состояние (State)  
**Паттерны:** Наблюдатель (Observer), Состояние (State)  
**Вариант 8:** Графический пароль

---

## Что реализовано

Приложение «Графический пароль» на Python с использованием Tkinter:

- Сетка 3×3 из девяти скруглённых ячеек.
- Формирование последовательности графического пароля.
- Сохранение пароля в виде SHA-256 хэша в файл `graphical_password.json`.
- Проверка пароля путём сравнения хэшей.
- Демонстрация паттерна **«Наблюдатель»** — `AppWindow` подписан на события `PasswordManager` и автоматически обновляет интерфейс при создании/сбросе пароля.
- Демонстрация паттерна **«Состояние»** — приложение переключается между состояниями `NoPasswordState`, `PasswordSetState`, `BlockedState`, и поведение кнопок зависит от текущего состояния.

---

## Паттерн «Наблюдатель»

Паттерн «Наблюдатель» (Observer) — это поведенческий паттерн, который позволяет одним объектам (наблюдателям) автоматически получать уведомления об изменениях в другом объекте (субъекте).

В программе определены роли:

- `PasswordManager` — субъект (Subject), уведомляющий наблюдателей при событиях `password_created` и `password_reset`;
- `StateObserver` — интерфейс наблюдателя;
- `AppWindow` — конкретный наблюдатель, реализующий `on_state_changed(event, info)`.

Подписка:

```python
self.password_manager.subscribe(self)
```
Уведомление внутри PasswordManager:

```
def _notify(self, event, info=None):
    for observer in list(self._observers):
        observer.on_state_changed(event, info)
```
Реакция UI:
```
def on_state_changed(self, event, info=None):
    if event == "password_created":
        self.state = PasswordSetState()
    elif event == "password_reset":
        self.state = NoPasswordState()
    self._update_view()
```

## Паттерн «Состояние»
Паттерн «Состояние» (State) — это поведенческий паттерн, который позволяет объекту менять поведение при изменении внутреннего состояния.

В программе определены роли:

- AppState — абстрактное состояние.
- NoPasswordState — пароль не установлен (можно только создать).
- PasswordSetState — пароль установлен (можно войти или перезаписать).
- BlockedState — блокировка после 5 неверных попыток (на 30 секунд).

Каждое состояние определяет:

- название и цвет бейджа над сеткой.
- доступность входа/создания (can_login(), can_create()).
- текст основной кнопки (get_primary_text(mode)).
- статусное сообщение.

Пример:

```
class BlockedState(AppState):
    def can_login(self): return False
    def can_create(self): return False
    def get_primary_text(self, mode):
        remaining = int((self.until_time - datetime.now()).total_seconds())
        return f"Заблокировано ({remaining} с)"
```
---
## Основные классы
Элемент	Назначение:
- StateObserver	Интерфейс наблюдателя
- PasswordManager	Субъект (Singleton), уведомляющий наблюдателей
- AppState	Абстрактное состояние
- NoPasswordState	Пароль не установлен
- PasswordSetState	Пароль установлен
- BlockedState	Заблокировано после неверных попыток
- AppWindow	Основной класс интерфейса (наблюдатель)
- RoundedButton, rounded_rect()	Скруглённые кнопки и ячейки