# сервер WebSocket для демонстрации тестирования
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # принимаем соединение
    await websocket.accept()
    
    try:
        while True:
            # получаем текстовое сообщение
            message = await websocket.receive_text()
            
            # отправляем эхо-ответ
            await websocket.send_text(f"Эхо: {message}")
            
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/json")
async def websocket_json_endpoint(websocket: WebSocket):
    # эндпоинт для работы с JSON-сообщениями
    await websocket.accept()
    
    try:
        while True:
            # получаем JSON-данные
            data = await websocket.receive_json()
            
            # формируем ответ
            response = {
                "статус": "получено",
                "данные": data,
                "длина": len(str(data))
            }
            
            # отправляем JSON-ответ
            await websocket.send_json(response)
            
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/bytes")
async def websocket_bytes_endpoint(websocket: WebSocket):
    # эндпоинт для работы с бинарными данными
    await websocket.accept()
    
    try:
        while True:
            # получаем бинарные данные
            data = await websocket.receive_bytes()
            
            # отправляем данные обратно с добавлением информации о размере
            size_info = f"Размер: {len(data)} байт\n".encode("utf-8")
            await websocket.send_bytes(size_info + data)
            
    except WebSocketDisconnect:
        pass
