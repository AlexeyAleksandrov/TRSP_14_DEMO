# сервер WebSocket с эхо-функциональностью
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # принимаем входящее соединение
    await websocket.accept()
    print("Клиент подключился")
    
    try:
        while True:
            # ожидаем сообщение от клиента
            message = await websocket.receive_text()
            print(f"Получено сообщение: {message}")
            
            # отправляем сообщение обратно (эхо)
            response = f"Эхо: {message}"
            await websocket.send_text(response)
            print(f"Отправлен ответ: {response}")
            
    except WebSocketDisconnect:
        print("Клиент отключился")
