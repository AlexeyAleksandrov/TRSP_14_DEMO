# сервер с SSE для уведомлений о новых сообщениях
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import asyncio
import json
from datetime import datetime
from typing import AsyncGenerator

app = FastAPI()

# очередь сообщений для SSE-уведомлений
# в реальном приложении использовать Redis Pub/Sub или подобное
message_queues: dict[str, asyncio.Queue] = {}


async def event_generator(client_id: str) -> AsyncGenerator[str, None]:
    # генератор событий SSE для конкретного клиента
    queue = asyncio.Queue()
    message_queues[client_id] = queue
    
    try:
        # отправляем начальное событие подключения
        yield f"event: connected\ndata: {json.dumps({'client_id': client_id}, ensure_ascii=False)}\n\n"
        
        while True:
            # ожидаем сообщение из очереди
            try:
                message = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield f"event: message\ndata: {json.dumps(message, ensure_ascii=False)}\n\n"
            except asyncio.TimeoutError:
                # отправляем keepalive каждые 30 секунд
                yield f": keepalive\n\n"
    finally:
        # удаляем очередь при отключении
        message_queues.pop(client_id, None)


@app.get("/sse/{client_id}")
async def sse_endpoint(client_id: str):
    # SSE-эндпоинт для получения уведомлений
    return StreamingResponse(
        event_generator(client_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # для nginx
        }
    )


@app.post("/send")
async def send_message(sender: str, receiver: str, content: str):
    # HTTP-эндпоинт для отправки сообщения
    # отправитель делает HTTP-запрос, получатель получает SSE-уведомление
    
    message = {
        "от": sender,
        "кому": receiver,
        "сообщение": content,
        "время": datetime.utcnow().isoformat()
    }
    
    # если получатель подключён к SSE - отправляем уведомление
    if receiver in message_queues:
        await message_queues[receiver].put(message)
        return {
            "статус": "доставлено",
            "сообщение": message
        }
    else:
        return {
            "статус": "получатель_не_в_сети",
            "сообщение": message
        }


@app.post("/broadcast")
async def broadcast_message(sender: str, content: str):
    # рассылка сообщения всем подключённым клиентам
    message = {
        "от": sender,
        "тип": "broadcast",
        "сообщение": content,
        "время": datetime.utcnow().isoformat()
    }
    
    # отправляем всем подключённым
    for client_id, queue in message_queues.items():
        await queue.put(message)
    
    return {
        "статус": "отправлено",
        "получатели": list(message_queues.keys()),
        "сообщение": message
    }


@app.get("/clients")
async def get_clients():
    # получение списка подключённых клиентов
    return {
        "клиенты": list(message_queues.keys()),
        "количество": len(message_queues)
    }
