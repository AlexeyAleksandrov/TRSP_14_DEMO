# Пример 6: Полноценный чат с авторизацией

## Описание

Данный пример демонстрирует полноценное приложение чата с:

- Регистрацией и авторизацией пользователей
- Хранением данных в PostgreSQL
- JWT-токенами
- Хранением токена в Cookie
- WebSocket-чатом с событийной моделью
- Личными и общими сообщениями

## Структура

- `models.py` - модели SQLAlchemy (User, Message)
- `database.py` - настройка подключения к PostgreSQL
- `auth.py` - функции для работы с JWT и паролями
- `schemas.py` - Pydantic-схемы для валидации
- `manager.py` - менеджер подключений с событийной моделью
- `main.py` - главный файл приложения
- `client.py` - клиент для тестирования

## Требования

PostgreSQL должен быть запущен и доступен.

## Настройка базы данных

```bash
# создание базы данных
createdb chat_db
```

Или через psql:
```sql
CREATE DATABASE chat_db;
```

## Переменные окружения

```bash
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/chat_db"
export SECRET_KEY="your-secret-key"
```

## Запуск

### Сервер

```bash
uvicorn main:app --reload --port 8000
```

### Демонстрация

```bash
python client.py
```

### Интерактивный режим

```bash
python client.py Алиса password123
```

## HTTP-эндпоинты

- `POST /register` - регистрация пользователя
- `POST /login` - авторизация (возвращает JWT, устанавливает cookie)
- `POST /logout` - выход (удаляет cookie)
- `GET /me` - информация о текущем пользователе

## WebSocket-эндпоинт

`/ws?token=<jwt_token>` или с cookie `access_token`

### Формат сообщений

Общее сообщение:
```json
{"тип": "общее", "сообщение": "Привет всем!"}
```

Личное сообщение:
```json
{"тип": "личное", "кому": "Борис", "сообщение": "Привет!"}
```

## Зависимости

```
fastapi
uvicorn
sqlalchemy
asyncpg
pyjwt
passlib[bcrypt]
aiohttp
```
