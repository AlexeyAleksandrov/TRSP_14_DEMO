# модульные тесты для WebSocket-эндпоинтов
import pytest
from fastapi.testclient import TestClient
from server import app


class TestWebSocketText:
    # тесты для текстового WebSocket-эндпоинта
    
    def test_echo_single_message(self):
        # проверка эхо-ответа на одно сообщение
        client = TestClient(app)
        
        with client.websocket_connect("/ws") as websocket:
            websocket.send_text("Привет")
            response = websocket.receive_text()
            assert response == "Эхо: Привет"
    
    def test_echo_multiple_messages(self):
        # проверка эхо-ответа на несколько сообщений подряд
        client = TestClient(app)
        messages = ["Первое сообщение", "Второе сообщение", "Третье сообщение"]
        
        with client.websocket_connect("/ws") as websocket:
            for message in messages:
                websocket.send_text(message)
                response = websocket.receive_text()
                assert response == f"Эхо: {message}"
    
    def test_echo_cyrillic(self):
        # проверка корректной работы с кириллицей
        client = TestClient(app)
        
        with client.websocket_connect("/ws") as websocket:
            websocket.send_text("Тестовое сообщение на русском языке")
            response = websocket.receive_text()
            assert "русском" in response


class TestWebSocketJson:
    # тесты для JSON WebSocket-эндпоинта
    
    def test_json_simple(self):
        # проверка простого JSON-обмена
        client = TestClient(app)
        
        with client.websocket_connect("/ws/json") as websocket:
            data = {"сообщение": "Привет", "число": 42}
            websocket.send_json(data)
            response = websocket.receive_json()
            
            assert response["статус"] == "получено"
            assert response["данные"] == data
    
    def test_json_nested(self):
        # проверка вложенных JSON-структур
        client = TestClient(app)
        
        with client.websocket_connect("/ws/json") as websocket:
            data = {
                "пользователь": {
                    "имя": "Иван",
                    "возраст": 25
                },
                "действие": "вход"
            }
            websocket.send_json(data)
            response = websocket.receive_json()
            
            assert response["статус"] == "получено"
            assert response["данные"]["пользователь"]["имя"] == "Иван"


class TestWebSocketBytes:
    # тесты для бинарного WebSocket-эндпоинта
    
    def test_bytes_simple(self):
        # проверка передачи бинарных данных
        client = TestClient(app)
        
        with client.websocket_connect("/ws/bytes") as websocket:
            data = b"Binary data test"
            websocket.send_bytes(data)
            response = websocket.receive_bytes()
            
            # ответ содержит информацию о размере и исходные данные
            assert b"Binary data test" in response
            assert b"16" in response  # размер исходных данных
    
    def test_bytes_cyrillic(self):
        # проверка бинарных данных с кириллицей
        client = TestClient(app)
        
        with client.websocket_connect("/ws/bytes") as websocket:
            text = "Тест кириллицы"
            data = text.encode("utf-8")
            websocket.send_bytes(data)
            response = websocket.receive_bytes()
            
            assert text.encode("utf-8") in response
