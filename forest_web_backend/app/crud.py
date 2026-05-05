from sqlalchemy.orm import Session
from passlib.context import CryptContext
from passlib.exc import UnknownHashError
from app import  schemas
from app.models.user import User

# 密码加密上下文（锁定 bcrypt 后端，解决版本兼容问题）
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__default_rounds=12  # 固定加密轮数，提升兼容性
)

def get_user_by_username(db: Session, username: str) -> User | None:
    """根据用户名查询用户"""
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, user: schemas.UserCreate) -> User:
    """创建用户（自动加密密码）"""
    # 校验密码长度（BCrypt 限制 72 字节）
    if len(user.password) > 72:
        raise ValueError("密码长度不能超过 72 个字符")
    
    # 加密密码
    hashed_pwd = pwd_context.hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_pwd)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def verify_password(plain_pwd: str, hashed_pwd: str) -> bool:
    """验证密码（增加异常捕获，避免哈希格式错误导致 500）"""
    try:
        # 校验密码长度
        if len(plain_pwd) > 72:
            return False
        # 验证密码
        return pwd_context.verify(plain_pwd, hashed_pwd)
    except UnknownHashError:
        # 捕获非法哈希格式（如数据库中的明文密码）
        return False