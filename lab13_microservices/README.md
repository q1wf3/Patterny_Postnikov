# Лабораторная работа №13 — Паттерны микросервисов: API Gateway + Circuit Breaker

**Тема:** Паттерны микросервисов и распределённых систем: API Gateway, Circuit Breaker  
**Паттерны:** API Gateway, Circuit Breaker  
**Вариант 8:** Графический пароль

---

## Что реализовано

Приложение «Графический пароль» на Python с использованием Tkinter, демонстрирующее паттерны микросервисов:

- `PasswordService` — «микросервис» хранения пароля (Singleton, SHA-256, JSON).
- `ValidatorService` — «микросервис» валидации последовательности.
- `APIGateway` — единая точка входа для UI: маршрутизирует запросы к нужному сервису, ведёт лог.
- `CircuitBreaker` — предохранитель: после 3 сбоев «размыкает цепь» на 10 секунд и блокирует запросы.
- UI работает **только** с `APIGateway`, не зная о внутренних сервисах.

---

## Паттерн API Gateway

Паттерн API Gateway — это паттерн микросервисной архитектуры, при котором все клиентские запросы проходят через единую точку входа. Шлюз маршрутизирует запросы к нужным микросервисам, скрывая от клиента их внутреннюю структуру.

В программе:

- `APIGateway` — единая точка входа;
- методы `validate()`, `status()`, `create()`, `verify()`, `reset()` — «эндпоинты» шлюза;
- клиент (`AppWindow`) не знает, что за `POST /password` стоит `PasswordService`, а за `POST /validate` — `ValidatorService`.

Маршрутизация:

```python
def create(self, sequence):
    return self._call("POST /password", lambda: self.password_service.create(sequence))

def validate(self, sequence):
    return self._call("POST /validate", lambda: self.validator_service.validate(sequence))
```

## Паттерн Circuit Breaker

Паттерн Circuit Breaker — это паттерн отказоустойчивости, который предотвращает повторные вызовы сбойного сервиса. Он работает как электрический предохранитель:

- CLOSED — запросы проходят;
- после N ошибок переходит в OPEN — запросы блокируются на T секунд;
- после T секунд пробует снова (HALF-OPEN, в упрощённой версии — сразу CLOSED при успехе).

В программе:

- CircuitBreaker(failure_threshold=3, recovery_time=10);
- при каждой ошибке record_failure(), при успехе — record_success();
- если цепь открыта, APIGateway возвращает ServiceResult(False, "Circuit Breaker открыт...").
- Состояние отображается бейджем над сеткой: CLOSED (зелёный) или OPEN (N с) (красный).
- Кнопка «Симулировать сбой» вручную увеличивает счётчик ошибок — удобно для демонстрации

## Основные классы
Элемент	Назначение
|---|---|
|`ServiceResult`|Результат вызова сервиса (success, message, data)|
|`PasswordService`|Микросервис хранения пароля (Singleton)|
|`ValidatorService`|Микросервис валидации|
|`CircuitBreaker`|Предохранитель|
|`APIGateway`|Единая точка входа (шлюз)|
|`AppWindow`| UI-клиент, работающий только с Gateway|
|`RoundedButton`, `rounded_rect()`|Скруглённые кнопки и ячейки|