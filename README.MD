# Паттерны проектирования — лабораторные работы

**Студент:** Постников Илья Викторович  
**Группа:** ПИЖ-б-о-23-1  
**Направление:** 09.03.04 «Программная инженерия»  
**Дисциплина:** «Паттерны проектирования»  
**Университет:** СКФУ, Институт перспективной инженерии, Департамент цифровых, робототехнических систем и электроники

---

## Список лабораторных работ

| № | Тема | Паттерны | Вариант | Папка |
|---|------|----------|---------|-------|
| 1 | Порождающие паттерны | Одиночка (Singleton) | 8 — Графический пароль | [lab01_singleton](./lab01_singleton) |
| 2 | Порождающие паттерны | Абстрактная фабрика, Фабричный метод, Прототип | — | [lab02_abstract_factory](./lab02_abstract_factory) |
| 3 | Структурные паттерны | Адаптер, Мост | — | [lab03_adapter_bridge](./lab03_adapter_bridge) |
| 4 | Структурные паттерны | Компоновщик, Декоратор | — | [lab04_composite_decorator](./lab04_composite_decorator) |
| 5 | Структурные паттерны | Фасад, Приспособленец | — | [lab05_facade_flyweight](./lab05_facade_flyweight) |
| 6 | Структурные паттерны | Заместитель | — | [lab06_proxy](./lab06_proxy) |
| 7 | Поведенческие паттерны | Команда, Итератор | — | [lab07_command_iterator](./lab07_command_iterator) |
| 8 | Поведенческие паттерны | Цепочка обязанностей | — | [lab08_chain_of_responsibility](./lab08_chain_of_responsibility) |
| 9 | Поведенческие паттерны | Посредник, Снимок | — | [lab09_mediator_memento](./lab09_mediator_memento) |
| 10 | Поведенческие паттерны | Наблюдатель, Состояние | — | [lab10_observer_state](./lab10_observer_state) |
| 11 | Поведенческие паттерны | Стратегия, Шаблонный метод | — | [lab11_strategy_template](./lab11_strategy_template) |
| 12 | Архитектурные паттерны | MVC / MVP / MVVM / Clean Architecture | — | [lab12_architectural](./lab12_architectural) |
| 13 | Паттерны микросервисов | Saga / CQRS / Event Sourcing / Circuit Breaker / API Gateway | — | [lab13_microservices](./lab13_microservices) |
| 14 | Системные паттерны | Repository / Data Mapper / Active Record / Unit of Work | — | [lab14_data_patterns](./lab14_data_patterns) |
| 15 | Идиоматические паттерны | Producer-Consumer / Thread Pool / Future-Promise | — | [lab15_idiomatic](./lab15_idiomatic) |

---

## Как запустить

Каждая лабораторная — это **отдельное приложение**. Перейдите в папку нужной лабы и запустите `main.py`:

```bash
cd lab01_singleton
python main.py