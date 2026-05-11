# чат-сервер с событийной моделью и ConnectionManager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Callable, Awaitable
import json

app = FastAPI()


class ConnectionManager:
    # менеджер подключений с событийной моделью
    
    def __init__(self):
        # словарь: имя комнаты -> множество подключений
        self.rooms: dict[str, set[WebSocket]] = {}
        # словарь: websocket -> информация о пользователе
        self.users: dict[WebSocket, dict] = {}
        
        # обработчики событий
        self._on_connect: Callable[[WebSocket, str, str], Awaitable[None]] | None = None
        self._on_receive: Callable[[WebSocket, str, str, dict], Awaitable[None]] | None = None
        self._on_disconnect: Callable[[WebSocket, str, str], Awaitable[None]] | None = None
    
    def on_connect(self, handler: Callable[[WebSocket, str, str], Awaitable[None]]):
        # декоратор для регистрации обработчика подключения
        self._on_connect = handler
        return handler
    
    def on_receive(self, handler: Callable[[WebSocket, str, str, dict], Awaitable[None]]):
        # декоратор для регистрации обработчика получения сообщения
        self._on_receive = handler
        return handler
    
    def on_disconnect(self, handler: Callable[[WebSocket, str, str], Awaitable[None]]):
        # декоратор для регистрации обработчика отключения
        self._on_disconnect = handler
        return handler
    
    async def connect(self, websocket: WebSocket, room: str, username: str):
        # подключение пользователя к комнате
        await websocket.accept()
        
        self.rooms.setdefault(room, set()).add(websocket)
        self.users[websocket] = {"room": room, "username": username}
        
        if self._on_connect:
            await self._on_connect(websocket, room, username)
    
    async def disconnect(self, websocket: WebSocket):
        # отключение пользователя
        user_info = self.users.pop(websocket, None)
        if not user_info:
            return
        
        room = user_info["room"]
        username = user_info["username"]
        
        if room in self.rooms:
            self.rooms[room].discard(websocket)
            if not self.rooms[room]:
                del self.rooms[room]
        
        if self._on_disconnect:
            await self._on_disconnect(websocket, room, username)
    
    async def handle_message(self, websocket: WebSocket, data: dict):
        # обработка входящего сообщения
        user_info = self.users.get(websocket)
        if not user_info:
            return
        
        if self._on_receive:
            await self._on_receive(
                websocket, 
                user_info["room"], 
                user_info["username"], 
                data
            )
    
    async def broadcast(self, room: str, message: dict, exclude: WebSocket | None = None):
        # отправка сообщения всем в комнате
        if room not in self.rooms:
            return
        
        text = json.dumps(message, ensure_ascii=False)
        for ws in list(self.rooms[room]):
            if ws != exclude:
                try:
                    await ws.send_text(text)
                except Exception:
                    await self.disconnect(ws)
    
    async def send_to_user(self, room: str, target_username: str, message: dict):
        # отправка личного сообщения конкретному пользователю
        if room not in self.rooms:
            return False
        
        text = json.dumps(message, ensure_ascii=False)
        for ws in self.rooms[room]:
            user_info = self.users.get(ws)
            if user_info and user_info["username"] == target_username:
                try:
                    await ws.send_text(text)
                    return True
                except Exception:
                    return False
        return False
    
    def get_users_in_room(self, room: str) -> list[str]:
        # получение списка пользователей в комнате
        users = []
        for ws in self.rooms.get(room, []):
            user_info = self.users.get(ws)
            if user_info:
                users.append(user_info["username"])
        return users


# создаём экземпляр менеджера
manager = ConnectionManager()


# регистрация обработчиков событий через декораторы
@manager.on_connect
async def handle_connect(websocket: WebSocket, room: str, username: str):
    # обработчик события подключения
    print(f"[{room}] {username} подключился")
    
    # уведомляем всех о новом пользователе
    await manager.broadcast(room, {
        "тип": "система",
        "сообщение": f"{username} присоединился к чату"
    })
    
    # отправляем новому пользователю список участников
    users = manager.get_users_in_room(room)
    await websocket.send_json({
        "тип": "участники",
        "список": users
    })


@manager.on_receive
async def handle_receive(websocket: WebSocket, room: str, username: str, data: dict):
    # обработчик события получения сообщения
    msg_type = data.get("тип", "общее")
    text = data.get("сообщение", "")
    
    if msg_type == "общее":
        # отправляем всем в комнате
        await manager.broadcast(room, {
            "тип": "сообщение",
            "от": username,
            "сообщение": text
        })
        print(f"[{room}] {username}: {text}")
        
    elif msg_type == "личное":
        # отправляем конкретному пользователю
        target = data.get("кому", "")
        success = await manager.send_to_user(room, target, {
            "тип": "личное",
            "от": username,
            "сообщение": text
        })
        
        if success:
            # подтверждение отправителю
            await websocket.send_json({
                "тип": "доставлено",
                "кому": target,
                "сообщение": text
            })
        else:
            await websocket.send_json({
                "тип": "ошибка",
                "сообщение": f"Пользователь {target} не найден"
            })


@manager.on_disconnect
async def handle_disconnect(websocket: WebSocket, room: str, username: str):
    # обработчик события отключения
    print(f"[{room}] {username} отключился")
    
    await manager.broadcast(room, {
        "тип": "система",
        "сообщение": f"{username} покинул чат"
    })


@app.websocket("/ws/{room}")
async def websocket_endpoint(
    websocket: WebSocket, 
    room: str,
    username: str = "Аноним"
):
    # основной WebSocket-эндпоинт
    # подключение: ws://localhost:8000/ws/general?username=Ivan
    
    await manager.connect(websocket, room, username)
    
    try:
        while True:
            data = await websocket.receive_json()
            await manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
