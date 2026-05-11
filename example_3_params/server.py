# сервер WebSocket с демонстрацией path и query параметров
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query

app = FastAPI()


@app.websocket("/ws/{room_id}")
async def websocket_with_path_param(
    websocket: WebSocket, 
    room_id: str
):
    # path-параметр room_id извлекается из URL
    await websocket.accept()
    await websocket.send_text(f"Вы подключились к комнате: {room_id}")
    
    try:
        while True:
            message = await websocket.receive_text()
            await websocket.send_text(f"[Комната {room_id}] Получено: {message}")
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/chat/{room_id}")
async def websocket_with_query_params(
    websocket: WebSocket,
    room_id: str,
    username: str = Query(..., description="Имя пользователя"),
    token: str | None = Query(None, description="Токен авторизации")
):
    # комбинация path-параметра и query-параметров
    # подключение: ws://localhost:8000/ws/chat/room1?username=Ivan&token=abc123
    
    # проверка токена (упрощённая демонстрация)
    if token and token != "secret":
        await websocket.close(code=1008, reason="Неверный токен")
        return
    
    await websocket.accept()
    await websocket.send_text(f"Добро пожаловать, {username}! Комната: {room_id}")
    
    try:
        while True:
            message = await websocket.receive_text()
            await websocket.send_text(f"[{room_id}] {username}: {message}")
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/init")
async def websocket_with_initial_message(websocket: WebSocket):
    # демонстрация передачи данных первым сообщением
    # поскольку WebSocket не поддерживает body при рукопожатии,
    # данные можно передать первым сообщением после подключения
    
    await websocket.accept()
    await websocket.send_text("Отправьте JSON с вашими данными для инициализации")
    
    try:
        # ожидаем первое сообщение с данными инициализации
        init_data = await websocket.receive_json()
        
        username = init_data.get("username", "Аноним")
        room = init_data.get("room", "общая")
        
        await websocket.send_json({
            "тип": "инициализация",
            "статус": "успех",
            "пользователь": username,
            "комната": room
        })
        
        # основной цикл обработки сообщений
        while True:
            message = await websocket.receive_text()
            await websocket.send_text(f"[{room}] {username}: {message}")
            
    except WebSocketDisconnect:
        pass
