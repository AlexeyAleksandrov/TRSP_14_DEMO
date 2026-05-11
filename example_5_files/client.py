# клиент для передачи файлов по WebSocket
import asyncio
import websockets
import json
import hashlib
import os
import uuid

# размер чанка (должен совпадать с сервером)
CHUNK_SIZE = 64 * 1024


async def upload_file(filepath: str):
    # загрузка файла на сервер
    if not os.path.exists(filepath):
        print(f"Файл {filepath} не найден")
        return
    
    uri = "ws://localhost:8000/ws/upload"
    
    async with websockets.connect(uri) as ws:
        # читаем файл
        with open(filepath, "rb") as f:
            file_data = f.read()
        
        filename = os.path.basename(filepath)
        total_size = len(file_data)
        total_chunks = (total_size + CHUNK_SIZE - 1) // CHUNK_SIZE
        transfer_id = str(uuid.uuid4())
        original_hash = hashlib.md5(file_data).hexdigest()
        
        print(f"Загрузка файла: {filename}")
        print(f"Размер: {total_size} байт")
        print(f"Количество чанков: {total_chunks}")
        print(f"MD5: {original_hash}")
        print()
        
        # отправляем метаданные
        await ws.send(json.dumps({
            "тип": "начало_передачи",
            "id": transfer_id,
            "имя_файла": filename,
            "размер": total_size,
            "количество_чанков": total_chunks
        }, ensure_ascii=False))
        
        # ожидаем подтверждения
        response = json.loads(await ws.recv())
        if response.get("тип") != "готов_к_приёму":
            print(f"Ошибка: {response}")
            return
        
        # отправляем чанки
        for i in range(total_chunks):
            start = i * CHUNK_SIZE
            end = min(start + CHUNK_SIZE, total_size)
            chunk = file_data[start:end]
            
            # метаданные чанка
            await ws.send(json.dumps({
                "тип": "чанк",
                "id": transfer_id,
                "индекс": i
            }, ensure_ascii=False))
            
            # данные чанка
            await ws.send(chunk)
            
            # ожидаем подтверждения
            response = json.loads(await ws.recv())
            
            if response.get("тип") == "чанк_получен":
                progress = response.get("прогресс", 0)
                print(f"Отправлено: {progress:.1f}%")
            elif response.get("тип") == "передача_завершена":
                server_hash = response.get("хеш")
                print(f"\nФайл успешно загружен!")
                print(f"Путь на сервере: {response.get('путь')}")
                print(f"MD5 на сервере: {server_hash}")
                
                if server_hash == original_hash:
                    print("Проверка целостности: OK")
                else:
                    print("ВНИМАНИЕ: хеши не совпадают!")
                break


async def download_file(filename: str, save_path: str):
    # скачивание файла с сервера
    uri = f"ws://localhost:8000/ws/download/{filename}"
    
    async with websockets.connect(uri) as ws:
        # получаем метаданные
        response = json.loads(await ws.recv())
        
        if response.get("тип") == "ошибка":
            print(f"Ошибка: {response.get('сообщение')}")
            return
        
        total_size = response.get("размер")
        total_chunks = response.get("количество_чанков")
        server_hash = response.get("хеш")
        
        print(f"Скачивание файла: {filename}")
        print(f"Размер: {total_size} байт")
        print(f"Количество чанков: {total_chunks}")
        print(f"MD5 на сервере: {server_hash}")
        print()
        
        # подтверждаем готовность
        await ws.send(json.dumps({
            "тип": "готов_к_приёму"
        }))
        
        # получаем чанки
        chunks: dict[int, bytes] = {}
        
        while True:
            msg = await ws.recv()
            
            if isinstance(msg, str):
                data = json.loads(msg)
                
                if data.get("тип") == "чанк":
                    # следующее сообщение - бинарные данные
                    chunk_index = data.get("индекс")
                    chunk_data = await ws.recv()
                    chunks[chunk_index] = chunk_data
                    progress = ((chunk_index + 1) / total_chunks) * 100
                    print(f"Получено: {progress:.1f}%")
                    
                elif data.get("тип") == "передача_завершена":
                    break
        
        # собираем файл
        file_data = b""
        for i in range(total_chunks):
            file_data += chunks[i]
        
        # проверяем хеш
        local_hash = hashlib.md5(file_data).hexdigest()
        
        # сохраняем файл
        with open(save_path, "wb") as f:
            f.write(file_data)
        
        print(f"\nФайл сохранён: {save_path}")
        print(f"MD5 локальный: {local_hash}")
        
        if local_hash == server_hash:
            print("Проверка целостности: OK")
        else:
            print("ВНИМАНИЕ: хеши не совпадают!")


async def demo():
    # демонстрация передачи файлов
    print("=== Демонстрация передачи файлов по WebSocket ===\n")
    
    # создаём тестовый файл
    test_file = "test_file.txt"
    test_content = "Тестовое содержимое файла.\n" * 1000
    
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(test_content)
    
    print(f"Создан тестовый файл: {test_file}")
    print(f"Размер: {os.path.getsize(test_file)} байт\n")
    
    # загружаем на сервер
    print("--- Загрузка на сервер ---")
    await upload_file(test_file)
    print()
    
    # скачиваем обратно
    print("--- Скачивание с сервера ---")
    await download_file(test_file, "downloaded_" + test_file)
    
    # удаляем тестовые файлы (с задержкой для Windows)
    import gc
    gc.collect()
    await asyncio.sleep(0.1)
    
    try:
        os.remove(test_file)
        if os.path.exists("downloaded_" + test_file):
            os.remove("downloaded_" + test_file)
    except PermissionError:
        print("\nПримечание: временные файлы не удалены (заняты системой)")
    
    print("\nДемонстрация завершена")


async def demo_large_file():
    # демонстрация передачи большого файла (чанкование)
    print("=== Демонстрация передачи большого файла ===\n")
    
    # создаём большой тестовый файл (200 КБ)
    test_file = "large_file.bin"
    file_size = 200 * 1024
    
    with open(test_file, "wb") as f:
        # записываем псевдослучайные данные
        import random
        random.seed(42)
        f.write(bytes([random.randint(0, 255) for _ in range(file_size)]))
    
    print(f"Создан большой файл: {test_file}")
    print(f"Размер: {file_size} байт ({file_size // 1024} КБ)")
    print(f"Размер чанка: {CHUNK_SIZE} байт ({CHUNK_SIZE // 1024} КБ)")
    print(f"Ожидаемое количество чанков: {(file_size + CHUNK_SIZE - 1) // CHUNK_SIZE}")
    print()
    
    # загружаем на сервер
    print("--- Загрузка на сервер ---")
    await upload_file(test_file)
    print()
    
    # скачиваем обратно
    print("--- Скачивание с сервера ---")
    await download_file("large_file.bin", "downloaded_large_file.bin")
    
    # удаляем тестовые файлы (с задержкой для Windows)
    import gc
    gc.collect()
    await asyncio.sleep(0.1)
    
    try:
        os.remove(test_file)
        if os.path.exists("downloaded_large_file.bin"):
            os.remove("downloaded_large_file.bin")
    except PermissionError:
        print("\nПримечание: временные файлы не удалены (заняты системой)")
    
    print("\nДемонстрация завершена")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) == 1:
        # демо-режим
        asyncio.run(demo())
    elif sys.argv[1] == "large":
        # демо большого файла
        asyncio.run(demo_large_file())
    elif sys.argv[1] == "upload" and len(sys.argv) == 3:
        # загрузка файла
        asyncio.run(upload_file(sys.argv[2]))
    elif sys.argv[1] == "download" and len(sys.argv) == 4:
        # скачивание файла
        asyncio.run(download_file(sys.argv[2], sys.argv[3]))
    else:
        print("Использование:")
        print("  python client.py              - демонстрация")
        print("  python client.py large        - демонстрация большого файла")
        print("  python client.py upload <файл>")
        print("  python client.py download <имя> <путь_сохранения>")
