from sqlmodel import create_engine, Session, SQLModel
from pydantic_settings import BaseSettings, SettingsConfigDict
import os


# 加载环境变量
class Settings(BaseSettings):
    DATABASE_URL: str
    UPLOAD_DIR: str
    MAX_AVATAR_SIZE: int
    BASE_URL: str

    model_config = SettingsConfigDict(
        env_file="src/.env",
        env_file_encoding="utf-8"
    )


settings = Settings()


# 确保上传目录存在
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


# 数据库引擎（SQLite需加check_same_thread=False）
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={
        "check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)


# 创建数据库表
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


# 数据库会话依赖
def get_session():
    with Session(engine) as session:
        yield session
