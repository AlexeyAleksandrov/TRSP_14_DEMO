# HTTP-клиент для отправки сообщений
import aiohttp
import asyncio
import sys


async def send_message(sender: str, receiver: str, content: str):
    # отправка сообщения через HTTP
    url = "http://localhost:8000/send"
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            params={
                "sender": sender,
                "receiver": receiver,
                "content": content
            }
        ) as response:
            result = await response.json()
            print(f"Ответ: {result}")


async def broadcast(sender: str, content: str):
    # рассылка сообщения всем
    url = "http://localhost:8000/broadcast"
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            params={
                "sender": sender,
                "content": content
            }
        ) as response:
            result = await response.json()
            print(f"Ответ: {result}")


async def get_clients():
    # получение списка подключённых клиентов
    url = "http://localhost:8000/clients"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            result = await response.json()
            print(f"Подключённые клиенты: {result}")


async def demo():
    # демонстрационный режим
    print("=== Демонстрация SSE ===\n")
    print("Для полной демонстрации:")
    print("1. Запустите сервер: uvicorn server:app --reload --port 8000")
    print("2. В отдельном терминале запустите SSE-клиента: python client_sse.py Алиса")
    print("3. В ещё одном терминале отправьте сообщение: python client_sender.py send Борис Алиса 'Привет!'")
    print()
    
    # проверяем подключённых клиентов
    print("Проверка подключённых клиентов:")
    await get_clients()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        asyncio.run(demo())
    
    elif sys.argv[1] == "send" and len(sys.argv) == 5:
        # отправка личного сообщения
        # python client_sender.py send <от> <кому> <сообщение>
        asyncio.run(send_message(sys.argv[2], sys.argv[3], sys.argv[4]))
    
    elif sys.argv[1] == "broadcast" and len(sys.argv) == 4:
        # рассылка всем
        # python client_sender.py broadcast <от> <сообщение>
        asyncio.run(broadcast(sys.argv[2], sys.argv[3]))
    
    elif sys.argv[1] == "clients":
        # список клиентов
        asyncio.run(get_clients())
    
    else:
        print("Использование:")
        print("  python client_sender.py                           - демонстрация")
        print("  python client_sender.py send <от> <кому> <текст>  - отправить сообщение")
        print("  python client_sender.py broadcast <от> <текст>    - отправить всем")
        print("  python client_sender.py clients                   - список клиентов")
