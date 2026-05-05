from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt
from passlib.exc import UnknownHashError  # 新增：捕获密码哈希异常

from app import crud, schemas, database
from app.models.user import User
from app.core.config import settings  # 修复：从core目录导入config


router = APIRouter(
    tags=["user"]
)

# 注册接口（增加异常捕获，避免密码加密失败）
@router.post("/register", response_model=dict)
def register(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    try:
        # 检查用户名是否存在
        db_user = crud.get_user_by_username(db, username=user.username)
        if db_user:
            return {"code": 400, "message": "用户名已存在"}
        
        # 创建用户（自动加密密码）
        crud.create_user(db=db, user=user)
        return {"code": 200, "message": "注册成功"}
    except ValueError as e:
        # 捕获密码长度/格式错误
        return {"code": 400, "message": str(e)}
    except Exception as e:
        # 兜底异常，避免500错误
        return {"code": 500, "message": f"注册失败：{str(e)}"}

# 登录接口（核心修复：密码验证异常 + Token生成 + 统一返回）
@router.post("/login", response_model=dict)
def login(user: schemas.UserLogin, db: Session = Depends(database.get_db)):
    try:
        # 1. 查询用户
        db_user = crud.get_user_by_username(db, username=user.username)
        if not db_user:
            return {"code": 400, "message": "用户名或密码错误"}
        
        # 2. 验证密码（增加异常捕获，解决UnknownHashError）
        # 在验证密码前加
        print("前端传的密码:", user.password)
        print("数据库里的哈希:", db_user.hashed_password)
        print("验证结果:", crud.verify_password(user.password, db_user.hashed_password))
        try:
            pwd_valid = crud.verify_password(user.password, db_user.hashed_password)
        except UnknownHashError:
            # 数据库中是明文/非法哈希，直接返回密码错误
            return {"code": 400, "message": "用户名或密码错误"}
        
        if not pwd_valid:
            return {"code": 400, "message": "用户名或密码错误"}
        
        # 3. 生成Token（规范写法，避免时间戳错误）
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = jwt.encode(
            claims={
                "sub": str(db_user.id),
                "username": db_user.username,
                "exp": datetime.utcnow() + access_token_expires
            },
            key=settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        # 4. 返回前端需要的格式（包含token和username）
        return {
            "code": 200,
            "message": "登录成功",
            "data": {
                "token": access_token,
                "username": db_user.username
            }
        }
    except Exception as e:
        # 兜底异常，返回500但不崩溃
        return {"code": 500, "message": f"登录失败：{str(e)}"}

# 获取用户信息接口（保留，适配token验证）
@router.get("/info", response_model=dict)
def get_user_info(
    current_user: User = Depends(database.get_current_user),
    db: Session = Depends(database.get_db)
):
    try:
        return {
            "code": 200,
            "data": {
                "id": current_user.id,
                "username": current_user.username
            }
        }
    except Exception as e:
        return {"code": 500, "message": f"获取用户信息失败：{str(e)}"}

# 退出登录接口（保留）
@router.post("/logout", response_model=dict)
def logout():
    return {"code": 200, "message": "退出登录成功"}