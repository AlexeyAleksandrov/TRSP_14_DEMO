# менеджер подключений WebSocket с событийной моделью
from fastapi import WebSocket
from typing import Callable, Awaitable
import json


class ChatManager:
    # менеджер чата с событийной моделью
    
    def __init__(self):
        # словарь: user_id -> websocket
        self.connections: dict[int, WebSocket] = {}
        # словарь: websocket -> user_info
        self.users: dict[WebSocket, dict] = {}
        
        # обработчики событий
        self._on_connect: Callable | None = None
        self._on_receive: Callable | None = None
        self._on_disconnect: Callable | None = None
    
    def on_connect(self, handler: Callable[[WebSocket, dict], Awaitable[None]]):
        # декоратор для обработчика подключения
        self._on_connect = handler
        return handler
    
    def on_receive(self, handler: Callable[[WebSocket, dict, dict], Awaitable[None]]):
        # декоратор для обработчика сообщений
        self._on_receive = handler
        return handler
    
    def on_disconnect(self, handler: Callable[[WebSocket, dict], Awaitable[None]]):
        # декоратор для обработчика отключения
        self._on_disconnect = handler
        return handler
    
    async def connect(self, websocket: WebSocket, user_info: dict):
        # подключение пользователя
        await websocket.accept()
        
        user_id = user_info["user_id"]
        self.connections[user_id] = websocket
        self.users[websocket] = user_info
        
        if self._on_connect:
            await self._on_connect(websocket, user_info)
    
    async def disconnect(self, websocket: WebSocket):
        # отключение пользователя
        user_info = self.users.pop(websocket, None)
        if not user_info:
            return
        
        user_id = user_info["user_id"]
        self.connections.pop(user_id, None)
        
        if self._on_disconnect:
            await self._on_disconnect(websocket, user_info)
    
    async def handle_message(self, websocket: WebSocket, data: dict):
        # обработка входящего сообщения
        user_info = self.users.get(websocket)
        if not user_info:
            return
        
        if self._on_receive:
            await self._on_receive(websocket, user_info, data)
    
    async def broadcast(self, message: dict, exclude: WebSocket | None = None):
        # отправка сообщения всем подключённым
        text = json.dumps(message, ensure_ascii=False)
        
        disconnected = []
        for ws in list(self.users.keys()):
            if ws != exclude:
                try:
                    await ws.send_text(text)
                except Exception:
                    disconnected.append(ws)
        
        # очищаем отключившихся
        for ws in disconnected:
            await self.disconnect(ws)
    
    async def send_to_user(self, user_id: int, message: dict) -> bool:
        # отправка личного сообщения
        ws = self.connections.get(user_id)
        if not ws:
            return False
        
        try:
            text = json.dumps(message, ensure_ascii=False)
            await ws.send_text(text)
            return True
        except Exception:
            await self.disconnect(ws)
            return False
    
    def get_user_by_websocket(self, websocket: WebSocket) -> dict | None:
        # получение информации о пользователе по websocket
        return self.users.get(websocket)
    
    def get_online_users(self) -> list[dict]:
        # получение списка онлайн-пользователей
        return [
            {"user_id": info["user_id"], "username": info["username"]}
            for info in self.users.values()
        ]
    
    def is_online(self, user_id: int) -> bool:
        # проверка, онлайн ли пользователь
        return user_id in self.connections


# глобальный экземпляр менеджера
manager = ChatManager()
