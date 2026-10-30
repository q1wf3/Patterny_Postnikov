# Лабораторная работа №15 — Идиоматические паттерны: Producer-Consumer

**Тема:** Идиоматические паттерны: Producer-Consumer, Thread Pool, Future / Promise
**Паттерн:** Producer-Consumer
**Вариант 8:** Графический пароль

---

## Что реализовано

- `ProducerConsumerApp` — UI (producer): генерирует задачи и кладёт их в `queue.Queue`.
- `Worker` — фоновый поток (consumer): читает задачи и выполняет их, не блокируя UI.
- `PasswordStore` — работа с `graphical_password.json`.
- `Task` — описание задачи (тип, последовательность, callback).
- Результаты возвращаются в UI через `root.after(...)` и `_poll_results()`.

---

## Паттерн Producer-Consumer

Producer-Consumer — идиоматический паттерн многопоточности, при котором один поток (producer) генерирует задачи и помещает их в очередь, а другой (consumer) извлекает и выполняет. Потоки общаются через потокобезопасную очередь, что исключает гонки данных.

В программе:

- `self.task_queue = queue.Queue()` — очередь задач;
- `self.result_queue = queue.Queue()` — очередь результатов;
- `Worker.run()` — цикл consumer: `task = self.task_queue.get()`;
- UI вызывает `_enqueue(...)` — producer кладёт задачу и блокирует кнопки до получения результата.

Без паттерна проверка пароля выполнялась бы в главном потоке Tkinter и «подвешивала» бы интерфейс. С паттерном UI остаётся отзывчивым.

---

## Как запустить

```bash
cd lab15_producer_consumer
python main.py
