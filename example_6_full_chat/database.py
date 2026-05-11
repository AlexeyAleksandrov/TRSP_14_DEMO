# настройка подключения к базе данных
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import os

# URL подключения к PostgreSQL
# формат: postgresql+asyncpg://user:password@host:port/database
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/chat_db"
)

# создание асинхронного движка
engine = create_async_engine(DATABASE_URL, echo=False)

# фабрика сессий
async_session = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


async def get_session() -> AsyncSession:
    # получение сессии базы данных
    async with async_session() as session:
        yield session


async def init_db():
    # инициализация базы данных (создание таблиц)
    from models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
