# SSE-клиент для получения уведомлений
import aiohttp
import asyncio
import sys


async def listen_sse(client_id: str):
    # подключение к SSE-эндпоинту
    url = f"http://localhost:8000/sse/{client_id}"
    
    print(f"Подключение к SSE как {client_id}...")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            print(f"Подключено. Ожидание уведомлений...\n")
            
            async for line in response.content:
                line = line.decode("utf-8").strip()
                
                if not line:
                    continue
                
                if line.startswith("event:"):
                    event_type = line[6:].strip()
                    print(f"[Событие: {event_type}]")
                
                elif line.startswith("data:"):
                    data = line[5:].strip()
                    print(f"  Данные: {data}")
                
                elif line.startswith(":"):
                    # комментарий (keepalive)
                    print("[keepalive]")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python client_sse.py <client_id>")
        print("Пример: python client_sse.py Алиса")
        sys.exit(1)
    
    client_id = sys.argv[1]
    asyncio.run(listen_sse(client_id))
