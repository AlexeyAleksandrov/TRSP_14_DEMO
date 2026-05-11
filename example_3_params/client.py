# клиент для демонстрации различных способов передачи параметров
import asyncio
import websockets
import json


async def demo_path_param():
    # подключение с path-параметром
    print("=== Тест path-параметра ===")
    uri = "ws://localhost:8000/ws/комната_1"
    
    async with websockets.connect(uri) as ws:
        # получаем приветствие
        response = await ws.recv()
        print(f"Ответ сервера: {response}")
        
        # отправляем сообщение
        await ws.send("Привет из комнаты!")
        response = await ws.recv()
        print(f"Ответ сервера: {response}")


async def demo_query_params():
    # подключение с query-параметрами
    print("\n=== Тест query-параметров ===")
    uri = "ws://localhost:8000/ws/chat/general?username=Иван&token=secret"
    
    async with websockets.connect(uri) as ws:
        response = await ws.recv()
        print(f"Ответ сервера: {response}")
        
        await ws.send("Всем привет!")
        response = await ws.recv()
        print(f"Ответ сервера: {response}")


async def demo_initial_message():
    # передача данных первым сообщением (вместо body)
    print("\n=== Тест инициализации через первое сообщение ===")
    uri = "ws://localhost:8000/ws/init"
    
    async with websockets.connect(uri) as ws:
        # получаем инструкцию
        response = await ws.recv()
        print(f"Сервер: {response}")
        
        # отправляем данные инициализации как JSON
        init_data = {
            "username": "Мария",
            "room": "разработка"
        }
        await ws.send(json.dumps(init_data))
        
        # получаем подтверждение
        response = await ws.recv()
        print(f"Ответ инициализации: {response}")
        
        # отправляем обычное сообщение
        await ws.send("Тестовое сообщение после инициализации")
        response = await ws.recv()
        print(f"Ответ сервера: {response}")


async def main():
    await demo_path_param()
    await demo_query_params()
    await demo_initial_message()


if __name__ == "__main__":
    asyncio.run(main())
