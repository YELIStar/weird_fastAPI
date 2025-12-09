from sqlmodel import SQLModel, Field
from typing import Optional


class User(SQLModel, table=True):
    """用户表：存储头像相对路径"""
    id: int = Field(
        primary_key=True
    )
    username: str = Field(
        unique=True,
        index=True
    )  # 唯一用户名
    avatar_path: str | None = Field(
        default=None
    )  # 头像相对路径（如：avatars/1/xxx.jpg）
