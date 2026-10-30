# Лабораторная работа №14 — Системные паттерны: Repository

**Тема:** Системные паттерны и работа с данными
**Паттерн:** Repository
**Вариант 8:** Графический пароль

---

## Что реализовано

- `PasswordRecord` — доменная сущность (хэш, дата создания, число попыток).
- `PasswordRepository` — репозиторий: скрывает работу с `graphical_password.json`, предоставляет методы `find`, `save`, `delete`, `increment_attempts`, `reset_attempts`.
- `PasswordService` — бизнес-логика (создание, проверка, сброс), работает только через репозиторий.
- `PasswordController` — UI и связка с сервисом. О существовании файла не знает.

---

## Паттерн Repository

Repository — это паттерн, который инкапсулирует логику доступа к данным и предоставляет интерфейс, похожий на коллекцию объектов в памяти. Клиент работает с репозиторием так, будто это обычный список записей, а детали хранения (JSON, БД, сеть) скрыты.

В программе:

```python
record = repository.find()
repository.save(PasswordRecord(hash))
repository.delete()
repository.increment_attempts()