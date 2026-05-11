# главный файл приложения чата
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Response
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from contextlib import asynccontextmanager
from datetime import datetime
import json

from database import get_session, init_db
from models import User, Message
from schemas import UserCreate, UserLogin, UserResponse, Token
from auth import hash_password, verify_password, create_access_token, decode_access_token
from manager import manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # инициализация базы данных при запуске
    await init_db()
    yield


app = FastAPI(title="Чат с авторизацией", lifespan=lifespan)
security = HTTPBearer()


# регистрация обработчиков событий
@manager.on_connect
async def handle_connect(websocket: WebSocket, user_info: dict):
    # обработчик подключения
    username = user_info["username"]
    print(f"[Система] {username} подключился")
    
    # уведомляем всех о новом пользователе
    await manager.broadcast({
        "тип": "система",
        "событие": "подключение",
        "пользователь": username,
        "время": datetime.utcnow().isoformat()
    }, exclude=websocket)
    
    # отправляем список онлайн-пользователей
    online = manager.get_online_users()
    await websocket.send_json({
        "тип": "онлайн",
        "пользователи": online
    })


@manager.on_receive
async def handle_receive(websocket: WebSocket, user_info: dict, data: dict):
    # обработчик входящих сообщений
    msg_type = data.get("тип", "общее")
    content = data.get("сообщение", "")
    
    sender_id = user_info["user_id"]
    sender_username = user_info["username"]
    
    if msg_type == "общее":
        # сообщение всем
        await manager.broadcast({
            "тип": "сообщение",
            "от": sender_username,
            "от_id": sender_id,
            "сообщение": content,
            "время": datetime.utcnow().isoformat()
        })
        print(f"[Общее] {sender_username}: {content}")
        
    elif msg_type == "личное":
        # личное сообщение
        receiver_username = data.get("кому", "")
        
        # ищем получателя среди онлайн-пользователей
        online = manager.get_online_users()
        receiver = next(
            (u for u in online if u["username"] == receiver_username), 
            None
        )
        
        if receiver:
            # отправляем получателю
            await manager.send_to_user(receiver["user_id"], {
                "тип": "личное",
                "от": sender_username,
                "от_id": sender_id,
                "сообщение": content,
                "время": datetime.utcnow().isoformat()
            })
            
            # подтверждение отправителю
            await websocket.send_json({
                "тип": "доставлено",
                "кому": receiver_username,
                "сообщение": content
            })
            print(f"[Личное] {sender_username} -> {receiver_username}: {content}")
        else:
            await websocket.send_json({
                "тип": "ошибка",
                "сообщение": f"Пользователь {receiver_username} не в сети"
            })


@manager.on_disconnect
async def handle_disconnect(websocket: WebSocket, user_info: dict):
    # обработчик отключения
    username = user_info["username"]
    print(f"[Система] {username} отключился")
    
    await manager.broadcast({
        "тип": "система",
        "событие": "отключение",
        "пользователь": username,
        "время": datetime.utcnow().isoformat()
    })


# HTTP-эндпоинты для регистрации и авторизации
@app.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_session)
):
    # регистрация нового пользователя
    
    # проверка существования пользователя
    result = await session.execute(
        select(User).where(
            (User.username == user_data.username) | 
            (User.email == user_data.email)
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(400, "Пользователь с таким именем или email уже существует")
    
    # создание пользователя
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hash_password(user_data.password)
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    
    return user


@app.post("/login", response_model=Token)
async def login(
    response: Response,
    user_data: UserLogin,
    session: AsyncSession = Depends(get_session)
):
    # авторизация пользователя
    
    # поиск пользователя
    result = await session.execute(
        select(User).where(User.username == user_data.username)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(401, "Неверное имя пользователя или пароль")
    
    # создание токена
    token = create_access_token({
        "sub": user.id,
        "username": user.username
    })
    
    # установка токена в cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=60 * 60 * 24,  # 24 часа
        samesite="lax"
    )
    
    return Token(access_token=token)


@app.post("/logout")
async def logout(response: Response):
    # выход из системы
    response.delete_cookie("access_token")
    return {"сообщение": "Выход выполнен"}


@app.get("/me", response_model=UserResponse)
async def get_current_user(
    session: AsyncSession = Depends(get_session),
    token: str = Depends(security)
):
    # получение информации о текущем пользователе
    payload = decode_access_token(token.credentials)
    if not payload:
        raise HTTPException(401, "Недействительный токен")
    
    result = await session.execute(
        select(User).where(User.id == payload["sub"])
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    
    return user


# WebSocket-эндпоинт
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # основной WebSocket-эндпоинт
    
    # получаем токен из query-параметра или cookie
    token = websocket.query_params.get("token")
    if not token:
        token = websocket.cookies.get("access_token")
    
    if not token:
        await websocket.close(code=1008, reason="Требуется авторизация")
        return
    
    # проверяем токен
    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=1008, reason="Недействительный токен")
        return
    
    user_info = {
        "user_id": payload["sub"],
        "username": payload["username"]
    }
    
    # подключаем пользователя
    await manager.connect(websocket, user_info)
    
    try:
        while True:
            data = await websocket.receive_json()
            await manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
