from fastapi import FastAPI, File, UploadFile, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
import os
from database import create_db_and_tables, get_session, settings
from models import User
from storage import LocalAvatarStorage

# 初始化FastAPI应用
app = FastAPI(title="本地存储用户头像服务", version="1.0")

# 配置CORS（跨域支持）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境替换为前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件服务：访问http://127.0.0.1:8000/static/avatars/1/xxx.jpg即可查看头像
# 注意：uploads目录是静态文件根目录，所以URL中的static对应uploads
app.mount(
    "/static",
    StaticFiles(directory=settings.UPLOAD_DIR.replace(
        "avatars", "")),  # 指向uploads/目录
    name="static"
)

# 启动时创建数据库表


@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# ------------------- 接口实现 -------------------
# 1. 创建用户（测试用）


@app.post("/users", summary="创建用户")
def create_user(user: User, session: Session = Depends(get_session)):
    # 检查用户名是否存在
    existing_user = session.exec(select(User).where(
        User.username == user.username)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

# 2. 上传用户头像


@app.post("/users/{user_id}/avatar", summary="上传用户头像")
def upload_user_avatar(
    user_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    storage: LocalAvatarStorage = Depends(LocalAvatarStorage)
):
    # 1. 检查用户是否存在
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 2. 读取文件内容
    try:
        file_content = file.file.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文件失败：{str(e)}")
    finally:
        file.file.close()

    # 3. 上传文件到本地磁盘
    new_avatar_path = storage.upload_avatar(user_id, file_content)

    # 4. 先删除旧头像（如果有）
    if user.avatar_path:
        storage.delete_avatar(user.avatar_path)

    # 5. 更新用户头像路径
    try:
        user.avatar_path = new_avatar_path
        session.add(user)
        session.commit()
        session.refresh(user)
    except Exception as e:
        # 数据库更新失败，删除新上传的文件
        storage.delete_avatar(new_avatar_path)
        raise HTTPException(status_code=500, detail=f"更新用户信息失败：{str(e)}")

    # 6. 返回结果（含头像URL）
    return {
        "message": "头像上传成功",
        "user_id": user_id,
        "avatar_path": user.avatar_path,
        "avatar_url": storage.get_avatar_url(user.avatar_path)
    }

# 3. 获取用户信息（含头像URL）


@app.get("/users/{user_id}", summary="获取用户信息")
def get_user(
    user_id: int,
    session: Session = Depends(get_session),
    storage: LocalAvatarStorage = Depends(LocalAvatarStorage)
):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 拼接头像URL（无头像则返回None）
    avatar_url = storage.get_avatar_url(
        user.avatar_path) if user.avatar_path else None
    return {
        "id": user.id,
        "username": user.username,
        "avatar_path": user.avatar_path,
        "avatar_url": avatar_url
    }

# 4. 删除用户头像（可选）


@app.delete("/users/{user_id}/avatar", summary="删除用户头像")
def delete_user_avatar(
    user_id: int,
    session: Session = Depends(get_session),
    storage: LocalAvatarStorage = Depends(LocalAvatarStorage)
):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if not user.avatar_path:
        raise HTTPException(status_code=400, detail="用户暂无头像")

    # 删除文件 + 更新数据库
    storage.delete_avatar(user.avatar_path)
    user.avatar_path = None
    session.add(user)
    session.commit()
    session.refresh(user)

    return {"message": "头像删除成功", "user_id": user_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app="main:app",
        host="127.0.0.1",
        port=5005,
        log_level="info",
        reload=True
    )
