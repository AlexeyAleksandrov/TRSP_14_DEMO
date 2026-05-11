# клиент WebSocket для взаимодействия с эхо-сервером
import asyncio
import websockets


async def main():
    uri = "ws://localhost:8000/ws"
    
    async with websockets.connect(uri) as websocket:
        print("Подключение к серверу установлено")
        
        # отправляем несколько тестовых сообщений
        messages = [
            "Привет, сервер!",
            "Как дела?",
            "Это тестовое сообщение",
        ]
        
        for message in messages:
            print(f"Отправка: {message}")
            await websocket.send(message)
            
            # ожидаем ответ от сервера
            response = await websocket.recv()
            print(f"Получено: {response}")
            print()
            
            # небольшая пауза между сообщениями
            await asyncio.sleep(1)
        
        print("Все сообщения отправлены, закрытие соединения")


if __name__ == "__main__":
    asyncio.run(main())
