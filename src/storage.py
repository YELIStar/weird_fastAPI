import os
from typing import Any, Literal
import uuid
from fastapi import HTTPException
import magic  # 验证文件真实类型
from database import settings


class LocalAvatarStorage:
    """本地磁盘头像存储工具类"""

    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        self.max_size = settings.MAX_AVATAR_SIZE
        # 允许的图片MIME类型
        self.allowed_mime_types = {
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/jpg"
        }
        # MIME类型对应扩展名（避免伪造扩展名）
        self.mime_to_ext = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/gif": "gif",
            "image/jpg": "jpg"
        }

    def _validate_file(self, file_content: bytes) -> (Any | Literal['application/octet-stream']):
        """验证文件大小和类型"""
        # 1. 检查文件大小
        if len(file_content) > self.max_size:
            raise HTTPException(
                status_code=400,
                detail=f"文件大小超过{self.max_size/1024/1024}MB限制"
            )

        # 2. 检查文件真实类型（通过文件头，避免伪造Content-Type）
        try:
            mime_type = magic.from_buffer(file_content, mime=True)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"文件类型验证失败：{str(e)}")

        if mime_type not in self.allowed_mime_types:
            raise HTTPException(
                status_code=400,
                detail=f"仅支持{self.allowed_mime_types}类型文件，实际类型：{mime_type}"
            )
        return mime_type

    def upload_avatar(self, user_id: int, file_content: bytes) -> str:
        """
        上传头像到本地磁盘
        :param user_id: 用户ID（用于创建子目录）
        :param file_content: 图片字节流
        :return: 头像相对路径（如：avatars/1/xxx.jpg）
        """
        # 1. 验证文件
        mime_type = self._validate_file(file_content)
        file_ext = self.mime_to_ext.get(mime_type, "jpg")

        # 2. 创建用户专属目录
        user_dir = os.path.join(self.upload_dir, str(user_id))
        os.makedirs(user_dir, exist_ok=True)

        # 3. 生成唯一文件名（UUID避免重名）
        file_name = f"{uuid.uuid4()}.{file_ext}"
        file_path = os.path.join(user_dir, file_name)

        # 4. 写入文件（二进制模式）
        try:
            with open(file_path, "wb") as f:
                f.write(file_content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"文件写入失败：{str(e)}")

        # 5. 返回相对路径（相对于项目根目录）
        relative_path = os.path.join("avatars", str(user_id), file_name)
        return relative_path.replace("\\", "/")  # 统一路径分隔符（兼容Windows）

    def delete_avatar(self, relative_path: str):
        """删除本地头像文件"""
        # 拼接绝对路径
        abs_path = os.path.join(
            settings.UPLOAD_DIR.replace("avatars", ""), relative_path)
        if os.path.exists(abs_path):
            try:
                os.remove(abs_path)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"文件删除失败：{str(e)}")
        else:
            raise HTTPException(status_code=404, detail="头像文件不存在")

    def get_avatar_url(self, relative_path: str) -> str:
        """将相对路径转为可访问的URL"""
        return f"{settings.BASE_URL}/static/{relative_path}"
