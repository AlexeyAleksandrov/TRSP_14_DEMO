# модуль аутентификации
from datetime import datetime, timedelta
from passlib.context import CryptContext
import jwt
import os

# секретный ключ для JWT
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 часа

# контекст для хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    # хеширование пароля
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # проверка пароля
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    # создание JWT-токена
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    # декодирование JWT-токена
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None
