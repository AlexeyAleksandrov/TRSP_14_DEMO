# Пример 2: Модульное тестирование WebSocket

## Описание

Данный пример демонстрирует тестирование WebSocket-эндпоинтов с использованием PyTest и TestClient из FastAPI.

## Структура

- `server.py` - сервер с тремя WebSocket-эндпоинтами (текст, JSON, бинарные данные)
- `test_websocket.py` - модульные тесты для всех эндпоинтов

## Эндпоинты

- `/ws` - текстовый эхо-сервер
- `/ws/json` - JSON эхо-сервер
- `/ws/bytes` - бинарный эхо-сервер

## Запуск тестов

```bash
pytest test_websocket.py -v
```

## Запуск с покрытием кода

```bash
pytest test_websocket.py -v --cov=server
```

## Зависимости

```
fastapi
uvicorn
pytest
httpx
```
