# Лабораторная работа №11 — Поведенческие паттерны: Стратегия, Шаблонный метод

**Тема:** Поведенческие паттерны проектирования: Стратегия (Strategy), Шаблонный метод (Template Method)  
**Паттерны:** Стратегия (Strategy), Шаблонный метод (Template Method)  
**Вариант 8:** Графический пароль

---

## Что реализовано

Приложение «Графический пароль» на Python с использованием Tkinter:

- Сетка 3×3 из девяти скруглённых ячеек.
- Формирование последовательности графического пароля.
- Сохранение пароля в виде хэша в файл `graphical_password.json`.
- Проверка пароля путём сравнения хэшей.
- Два режима: **создание пароля** и **вход**.
- Демонстрация паттерна **«Стратегия»** — переключение между алгоритмами хэширования (SHA-256, MD5, Length+Sum) через кнопку «Сменить стратегию».
- Демонстрация паттерна **«Шаблонный метод»** — операции создания и проверки пароля унаследованы от `PasswordOperation`, которая задаёт скелет алгоритма (`validate → prepare → do_hash → save → after_save`).

---

## Паттерн «Стратегия»

Паттерн «Стратегия» (Strategy) — это поведенческий паттерн, который позволяет менять алгоритм работы объекта во время выполнения, инкапсулируя каждый алгоритм в отдельный класс.

В программе определены роли:

- `HashingStrategy` — общий интерфейс стратегии с методами `hash(sequence)` и `get_name()`;
- `SHA256Strategy` — хэширование через SHA-256;
- `MD5Strategy` — хэширование через MD5;
- `LengthStrategy` — простая стратегия: `len:N:sum:M` (для демонстрации).

Переключение стратегии в UI:

```python
def _next_strategy(self):
    self.strategy_index = (self.strategy_index + 1) % len(self.strategies)
    new_strategy = self.strategies[self.strategy_index]
    self.password_manager.set_strategy(new_strategy)
```
PasswordManager использует текущую стратегию через общий интерфейс — ему не важно, какая конкретно реализация выбрана.

## Паттерн «Шаблонный метод»

Паттерн «Шаблонный метод» (Template Method) — это поведенческий паттерн, который определяет скелет алгоритма в базовом классе, оставляя реализацию отдельных шагов подклассам.

В программе определены роли:

- PasswordOperation — абстрактный класс с методом execute(sequence), который задаёт фиксированный порядок шагов:
- validate(sequence) — проверка последовательности;
- prepare(sequence) — подготовка (по умолчанию — копирование);
- do_hash(sequence) — вычисление хэша (абстрактный);
- save(sequence, hash_value) — сохранение или сравнение (абстрактный);
- after_save(sequence, hash_value) — хук после сохранения (по умолчанию ничего);
- success_message() — сообщение при успехе (абстрактный);
- CreatePasswordOperation — создание пароля;
- VerifyPasswordOperation — проверка пароля.

## Базовый шаблонный метод:

```
def execute(self, sequence):
    ok, msg = self.validate(sequence)
    if not ok:
        return PasswordResult(False, msg)
    prepared = self.prepare(sequence)
    hash_value = self.do_hash(prepared)
    save_result = self.save(sequence, hash_value)
    if not save_result.success:
        return save_result
    self.after_save(sequence, hash_value)
    return PasswordResult(True, self.success_message(), hash_value)
Подклассы переопределяют только нужные шаги, не меняя порядок выполнения.
```
## Основные классы
| Элемент| Назначение |
|---|---|
|`HashingStrategy` |	Интерфейс стратегии хэширования |
|`SHA256Strategy`, MD5Strategy, LengthStrategy | Конкретные стратегии | 
|`PasswordOperation` | Абстрактный шаблонный метод |
|`CreatePasswordOperation`, `VerifyPasswordOperation` | Конкретные операции |
|`PasswordManager` | `Singleton` | Хранит текущую стратегию |
|`AppWindow` | Основной класс интерфейса |
|`RoundedButton`, `rounded_rect()` | Скруглённые кнопки и ячейки |
