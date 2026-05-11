# Pydantic-схемы для валидации данных
from pydantic import BaseModel, EmailStr
from datetime import datetime


class UserCreate(BaseModel):
    # схема для регистрации пользователя
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    # схема для входа пользователя
    username: str
    password: str


class UserResponse(BaseModel):
    # схема для ответа с данными пользователя
    id: int
    username: str
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    # схема для токена
    access_token: str
    token_type: str = "bearer"


class MessageCreate(BaseModel):
    # схема для создания сообщения через WebSocket
    content: str
    receiver_username: str | None = None  # если None - сообщение всем


class MessageResponse(BaseModel):
    # схема для ответа с сообщением
    id: int
    sender_username: str
    receiver_username: str | None
    content: str
    created_at: datetime
