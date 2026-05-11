# клиент чата для демонстрации событийной модели
import asyncio
import websockets
import json
import sys


async def chat_client(room: str, username: str):
    uri = f"ws://localhost:8000/ws/{room}?username={username}"
    
    async with websockets.connect(uri) as ws:
        print(f"Подключение к комнате '{room}' как '{username}'")
        print("Команды:")
        print("  /выход - выйти из чата")
        print("  /личное <имя> <сообщение> - личное сообщение")
        print("  любой текст - сообщение всем")
        print()
        
        # задача для получения сообщений
        async def receiver():
            try:
                async for message in ws:
                    data = json.loads(message)
                    msg_type = data.get("тип", "")
                    
                    if msg_type == "система":
                        print(f"[Система] {data.get('сообщение', '')}")
                    elif msg_type == "участники":
                        print(f"[Участники] {', '.join(data.get('список', []))}")
                    elif msg_type == "сообщение":
                        print(f"{data.get('от', '?')}: {data.get('сообщение', '')}")
                    elif msg_type == "личное":
                        print(f"[Личное от {data.get('от', '?')}] {data.get('сообщение', '')}")
                    elif msg_type == "доставлено":
                        print(f"[Доставлено для {data.get('кому', '?')}]")
                    elif msg_type == "ошибка":
                        print(f"[Ошибка] {data.get('сообщение', '')}")
            except websockets.exceptions.ConnectionClosed:
                print("Соединение закрыто")
        
        # задача для отправки сообщений
        async def sender():
            loop = asyncio.get_event_loop()
            while True:
                # читаем ввод в отдельном потоке чтобы не блокировать
                line = await loop.run_in_executor(None, sys.stdin.readline)
                line = line.strip()
                
                if not line:
                    continue
                
                if line == "/выход":
                    break
                
                if line.startswith("/личное "):
                    parts = line[8:].split(" ", 1)
                    if len(parts) == 2:
                        await ws.send(json.dumps({
                            "тип": "личное",
                            "кому": parts[0],
                            "сообщение": parts[1]
                        }, ensure_ascii=False))
                    else:
                        print("Формат: /личное <имя> <сообщение>")
                else:
                    await ws.send(json.dumps({
                        "тип": "общее",
                        "сообщение": line
                    }, ensure_ascii=False))
        
        # запускаем обе задачи
        receiver_task = asyncio.create_task(receiver())
        sender_task = asyncio.create_task(sender())
        
        # ждём завершения отправителя (по команде /выход)
        await sender_task
        receiver_task.cancel()


async def demo_mode():
    # демо-режим без интерактивного ввода
    print("=== Демонстрация чата ===\n")
    
    uri_1 = "ws://localhost:8000/ws/demo?username=Алиса"
    uri_2 = "ws://localhost:8000/ws/demo?username=Борис"
    
    async with websockets.connect(uri_1) as ws1:
        print("Алиса подключилась")
        
        # получаем приветственные сообщения
        msg = await ws1.recv()
        print(f"Алиса получила: {msg}")
        msg = await ws1.recv()
        print(f"Алиса получила: {msg}")
        
        async with websockets.connect(uri_2) as ws2:
            print("\nБорис подключился")
            
            # Алиса получает уведомление о Борисе
            msg = await ws1.recv()
            print(f"Алиса получила: {msg}")
            
            # Борис получает свои приветственные сообщения
            msg = await ws2.recv()
            print(f"Борис получил: {msg}")
            msg = await ws2.recv()
            print(f"Борис получил: {msg}")
            
            # Алиса отправляет сообщение всем
            print("\nАлиса отправляет сообщение всем")
            await ws1.send(json.dumps({
                "тип": "общее",
                "сообщение": "Привет всем!"
            }, ensure_ascii=False))
            
            await asyncio.sleep(0.5)
            
            # Борис получает сообщение
            msg = await ws2.recv()
            print(f"Борис получил: {msg}")
            
            # Алиса тоже получает своё сообщение (broadcast)
            msg = await ws1.recv()
            print(f"Алиса получила: {msg}")
            
            # Борис отправляет личное сообщение Алисе
            print("\nБорис отправляет личное сообщение Алисе")
            await ws2.send(json.dumps({
                "тип": "личное",
                "кому": "Алиса",
                "сообщение": "Привет, Алиса!"
            }, ensure_ascii=False))
            
            await asyncio.sleep(0.5)
            
            # Борис получает подтверждение
            msg = await ws2.recv()
            print(f"Борис получил: {msg}")
            
            # Алиса получает личное сообщение
            msg = await ws1.recv()
            print(f"Алиса получила: {msg}")
            
        print("\nБорис отключился")
        
        # Алиса получает уведомление об отключении Бориса
        msg = await ws1.recv()
        print(f"Алиса получила: {msg}")
    
    print("\nДемонстрация завершена")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        # интерактивный режим: python client.py <комната> <имя>
        asyncio.run(chat_client(sys.argv[1], sys.argv[2]))
    else:
        # демо-режим
        asyncio.run(demo_mode())
