# сервер для передачи файлов по WebSocket
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
import os
import hashlib

app = FastAPI()

# размер чанка для передачи больших файлов (64 КБ)
CHUNK_SIZE = 64 * 1024

# директория для сохранения полученных файлов
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class FileReceiver:
    # класс для сборки файла из чанков
    
    def __init__(self, filename: str, total_size: int, total_chunks: int):
        self.filename = filename
        self.total_size = total_size
        self.total_chunks = total_chunks
        self.chunks: dict[int, bytes] = {}
        self.received_size = 0
    
    def add_chunk(self, index: int, data: bytes) -> bool:
        # добавление чанка
        if index in self.chunks:
            return False
        
        self.chunks[index] = data
        self.received_size += len(data)
        return True
    
    def is_complete(self) -> bool:
        # проверка завершённости приёма
        return len(self.chunks) == self.total_chunks
    
    def get_data(self) -> bytes:
        # сборка файла из чанков
        result = b""
        for i in range(self.total_chunks):
            result += self.chunks[i]
        return result
    
    def progress(self) -> float:
        # процент выполнения
        return (len(self.chunks) / self.total_chunks) * 100


# хранилище активных передач
active_transfers: dict[str, FileReceiver] = {}


@app.websocket("/ws/upload")
async def websocket_upload(websocket: WebSocket):
    # эндпоинт для загрузки файлов на сервер
    await websocket.accept()
    
    try:
        while True:
            # получаем сообщение
            data = await websocket.receive_text()
            msg = json.loads(data)
            msg_type = msg.get("тип")
            
            if msg_type == "начало_передачи":
                # начало новой передачи файла
                transfer_id = msg["id"]
                filename = msg["имя_файла"]
                total_size = msg["размер"]
                total_chunks = msg["количество_чанков"]
                
                active_transfers[transfer_id] = FileReceiver(
                    filename, total_size, total_chunks
                )
                
                await websocket.send_json({
                    "тип": "готов_к_приёму",
                    "id": transfer_id
                })
                print(f"Начата передача: {filename} ({total_size} байт, {total_chunks} чанков)")
            
            elif msg_type == "чанк":
                # получаем следующее сообщение с бинарными данными
                chunk_data = await websocket.receive_bytes()
                
                transfer_id = msg["id"]
                chunk_index = msg["индекс"]
                
                if transfer_id not in active_transfers:
                    await websocket.send_json({
                        "тип": "ошибка",
                        "сообщение": "Передача не найдена"
                    })
                    continue
                
                receiver = active_transfers[transfer_id]
                receiver.add_chunk(chunk_index, chunk_data)
                
                # отправляем подтверждение
                await websocket.send_json({
                    "тип": "чанк_получен",
                    "id": transfer_id,
                    "индекс": chunk_index,
                    "прогресс": receiver.progress()
                })
                
                # проверяем завершение
                if receiver.is_complete():
                    file_data = receiver.get_data()
                    file_hash = hashlib.md5(file_data).hexdigest()
                    
                    # сохраняем файл
                    filepath = os.path.join(UPLOAD_DIR, receiver.filename)
                    with open(filepath, "wb") as f:
                        f.write(file_data)
                    
                    await websocket.send_json({
                        "тип": "передача_завершена",
                        "id": transfer_id,
                        "путь": filepath,
                        "хеш": file_hash
                    })
                    
                    print(f"Файл сохранён: {filepath} (MD5: {file_hash})")
                    del active_transfers[transfer_id]
            
            elif msg_type == "отмена":
                # отмена передачи
                transfer_id = msg["id"]
                if transfer_id in active_transfers:
                    del active_transfers[transfer_id]
                    await websocket.send_json({
                        "тип": "передача_отменена",
                        "id": transfer_id
                    })
                    
    except WebSocketDisconnect:
        print("Клиент отключился")


@app.websocket("/ws/download/{filename}")
async def websocket_download(websocket: WebSocket, filename: str):
    # эндпоинт для скачивания файлов с сервера
    await websocket.accept()
    
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    if not os.path.exists(filepath):
        await websocket.send_json({
            "тип": "ошибка",
            "сообщение": f"Файл {filename} не найден"
        })
        await websocket.close()
        return
    
    try:
        # читаем файл
        with open(filepath, "rb") as f:
            file_data = f.read()
        
        total_size = len(file_data)
        total_chunks = (total_size + CHUNK_SIZE - 1) // CHUNK_SIZE
        file_hash = hashlib.md5(file_data).hexdigest()
        
        # отправляем метаданные
        await websocket.send_json({
            "тип": "начало_передачи",
            "имя_файла": filename,
            "размер": total_size,
            "количество_чанков": total_chunks,
            "хеш": file_hash
        })
        
        # ожидаем подтверждения готовности
        response = await websocket.receive_json()
        if response.get("тип") != "готов_к_приёму":
            await websocket.close()
            return
        
        # отправляем чанки
        for i in range(total_chunks):
            start = i * CHUNK_SIZE
            end = min(start + CHUNK_SIZE, total_size)
            chunk = file_data[start:end]
            
            # сначала метаданные чанка
            await websocket.send_json({
                "тип": "чанк",
                "индекс": i,
                "размер": len(chunk)
            })
            
            # затем сами данные
            await websocket.send_bytes(chunk)
            
            print(f"Отправлен чанк {i+1}/{total_chunks}")
        
        await websocket.send_json({
            "тип": "передача_завершена"
        })
        
        print(f"Файл {filename} отправлен клиенту")
        
    except WebSocketDisconnect:
        print("Клиент отключился во время передачи")
