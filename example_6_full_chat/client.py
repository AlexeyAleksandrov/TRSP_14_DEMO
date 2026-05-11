# клиент для тестирования чата
import asyncio
import aiohttp
import json
import sys


BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws"


async def register(username: str, email: str, password: str) -> dict:
    # регистрация пользователя
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_URL}/register",
            json={
                "username": username,
                "email": email,
                "password": password
            }
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error = await response.json()
                raise Exception(error.get("detail", "Ошибка регистрации"))


async def login(username: str, password: str) -> str:
    # авторизация и получение токена
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_URL}/login",
            json={
                "username": username,
                "password": password
            }
        ) as response:
            if response.status == 200:
                data = await response.json()
                return data["access_token"]
            else:
                error = await response.json()
                raise Exception(error.get("detail", "Ошибка авторизации"))


async def chat_client(token: str, username: str):
    # подключение к чату
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(f"{WS_URL}?token={token}") as ws:
            print(f"Подключение к чату как {username}")
            print("Команды:")
            print("  /выход - выйти из чата")
            print("  /личное <имя> <сообщение> - личное сообщение")
            print("  /онлайн - список онлайн-пользователей")
            print("  любой текст - сообщение всем")
            print()
            
            async def receiver():
                # получение сообщений
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        msg_type = data.get("тип", "")
                        
                        if msg_type == "система":
                            event = data.get("событие", "")
                            user = data.get("пользователь", "")
                            if event == "подключение":
                                print(f"[Система] {user} присоединился")
                            elif event == "отключение":
                                print(f"[Система] {user} покинул чат")
                        
                        elif msg_type == "онлайн":
                            users = data.get("пользователи", [])
                            names = [u["username"] for u in users]
                            print(f"[Онлайн] {', '.join(names)}")
                        
                        elif msg_type == "сообщение":
                            sender = data.get("от", "?")
                            content = data.get("сообщение", "")
                            print(f"{sender}: {content}")
                        
                        elif msg_type == "личное":
                            sender = data.get("от", "?")
                            content = data.get("сообщение", "")
                            print(f"[Личное от {sender}] {content}")
                        
                        elif msg_type == "доставлено":
                            receiver = data.get("кому", "")
                            print(f"[Доставлено для {receiver}]")
                        
                        elif msg_type == "ошибка":
                            print(f"[Ошибка] {data.get('сообщение', '')}")
                    
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        print(f"Ошибка: {ws.exception()}")
                        break
            
            async def sender():
                # отправка сообщений
                loop = asyncio.get_event_loop()
                while True:
                    line = await loop.run_in_executor(None, sys.stdin.readline)
                    line = line.strip()
                    
                    if not line:
                        continue
                    
                    if line == "/выход":
                        await ws.close()
                        break
                    
                    if line == "/онлайн":
                        # запрос списка онлайн уже получили при подключении
                        continue
                    
                    if line.startswith("/личное "):
                        parts = line[8:].split(" ", 1)
                        if len(parts) == 2:
                            await ws.send_json({
                                "тип": "личное",
                                "кому": parts[0],
                                "сообщение": parts[1]
                            })
                        else:
                            print("Формат: /личное <имя> <сообщение>")
                    else:
                        await ws.send_json({
                            "тип": "общее",
                            "сообщение": line
                        })
            
            # запускаем обе задачи
            receiver_task = asyncio.create_task(receiver())
            sender_task = asyncio.create_task(sender())
            
            await sender_task
            receiver_task.cancel()


async def demo():
    # демонстрационный режим
    print("=== Демонстрация чата с авторизацией ===\n")
    
    # регистрация пользователей
    print("--- Регистрация пользователей ---")
    try:
        user1 = await register("Алиса", "alice@example.com", "password123")
        print(f"Зарегистрирован: {user1['username']}")
    except Exception as e:
        print(f"Алиса: {e}")
    
    try:
        user2 = await register("Борис", "boris@example.com", "password456")
        print(f"Зарегистрирован: {user2['username']}")
    except Exception as e:
        print(f"Борис: {e}")
    
    print()
    
    # авторизация
    print("--- Авторизация ---")
    token1 = await login("Алиса", "password123")
    print("Алиса авторизована")
    token2 = await login("Борис", "password456")
    print("Борис авторизован")
    print()
    
    # подключение к чату
    print("--- Чат ---")
    
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(f"{WS_URL}?token={token1}") as ws1:
            # Алиса получает список онлайн
            msg = await ws1.receive_json()
            print(f"Алиса получила: {json.dumps(msg, ensure_ascii=False)}")
            
            async with session.ws_connect(f"{WS_URL}?token={token2}") as ws2:
                # Борис получает список онлайн
                msg = await ws2.receive_json()
                print(f"Борис получил: {json.dumps(msg, ensure_ascii=False)}")
                
                # Алиса получает уведомление о Борисе
                msg = await ws1.receive_json()
                print(f"Алиса получила: {json.dumps(msg, ensure_ascii=False)}")
                
                # Алиса отправляет сообщение всем
                print("\nАлиса отправляет сообщение всем")
                await ws1.send_json({
                    "тип": "общее",
                    "сообщение": "Всем привет!"
                })
                
                await asyncio.sleep(0.5)
                
                # Алиса и Борис получают сообщение
                msg = await ws1.receive_json()
                print(f"Алиса получила: {json.dumps(msg, ensure_ascii=False)}")
                msg = await ws2.receive_json()
                print(f"Борис получил: {json.dumps(msg, ensure_ascii=False)}")
                
                # Борис отправляет личное сообщение Алисе
                print("\nБорис отправляет личное сообщение Алисе")
                await ws2.send_json({
                    "тип": "личное",
                    "кому": "Алиса",
                    "сообщение": "Привет, Алиса!"
                })
                
                await asyncio.sleep(0.5)
                
                # Борис получает подтверждение
                msg = await ws2.receive_json()
                print(f"Борис получил: {json.dumps(msg, ensure_ascii=False)}")
                
                # Алиса получает личное сообщение
                msg = await ws1.receive_json()
                print(f"Алиса получила: {json.dumps(msg, ensure_ascii=False)}")
            
            # Борис отключился
            msg = await ws1.receive_json()
            print(f"\nАлиса получила: {json.dumps(msg, ensure_ascii=False)}")
    
    print("\nДемонстрация завершена")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # демо-режим
        asyncio.run(demo())
    elif len(sys.argv) == 3:
        # интерактивный режим: python client.py <username> <password>
        async def interactive():
            username = sys.argv[1]
            password = sys.argv[2]
            
            try:
                token = await login(username, password)
                await chat_client(token, username)
            except Exception as e:
                print(f"Ошибка: {e}")
        
        asyncio.run(interactive())
    else:
        print("Использование:")
        print("  python client.py                  - демонстрация")
        print("  python client.py <user> <pass>    - интерактивный режим")
