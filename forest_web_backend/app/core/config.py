# app/core/config.py
import os
import sys
from dotenv import load_dotenv
from typing import List, Optional
from pydantic_settings import BaseSettings

# ===================== 路径计算核心逻辑 =====================
# 获取当前文件 (config.py) 的绝对路径: .../app/core/config.py
CURRENT_FILE = os.path.abspath(__file__)
# 获取 core 目录: .../app/core
CORE_DIR = os.path.dirname(CURRENT_FILE)
# 获取 app 目录: .../app
APP_DIR = os.path.dirname(CORE_DIR)
# 获取项目根目录: .../project_root (假设 .env 在这里)
PROJECT_ROOT = os.path.dirname(APP_DIR)

# 加载 .env 文件 (优先从项目根目录加载)
ENV_FILE_PATH = os.path.join(PROJECT_ROOT, ".env")
if os.path.exists(ENV_FILE_PATH):
    load_dotenv(dotenv_path=ENV_FILE_PATH)
else:
    # 兼容模式：如果根目录没有，尝试在当前目录找
    load_dotenv()

class Settings(BaseSettings):
    """
    全局配置类
    优先级: 环境变量 > .env 文件 > 默认值
    """
    
    # ------------------------------
    # 安全与认证配置 (JWT)
    # ------------------------------
    # ⚠️ 生产环境务必修改 SECRET_KEY！建议使用 openssl rand -hex 32 生成
    SECRET_KEY: str = os.getenv("SECRET_KEY", "mangrove_forest_2026_secret_key_123456")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 120))  # 2小时

    # ------------------------------
    # 数据库配置 (PostgreSQL)
    # ------------------------------
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "15255862931zhu")
    DB_HOST: str = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT: int = int(os.getenv("DB_PORT", 5432))
    DB_NAME: str = os.getenv("DB_NAME", "mangrove_db")

    @property
    def DATABASE_URL(self) -> str:
        """生成 SQLAlchemy 所需的数据库连接 URL"""
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # ------------------------------
    # FastAPI 服务配置
    # ------------------------------
    API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
    API_PORT: int = int(os.getenv("API_PORT", 8000))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # 跨域配置 (支持逗号分隔的多个域名)
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")
    
    @property
    def CORS_ORIGINS_LIST(self) -> List[str]:
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # ------------------------------
    # 文件系统与机器学习路径配置
    # ------------------------------
    # 项目根目录
    BASE_DIR: str = PROJECT_ROOT
    
    # 数据根目录 (项目根目录/data)
    BASE_DATA_DIR: str = os.path.join(BASE_DIR, "data")
    
    # 默认输入文件
    DEFAULT_INPUT_FILE: str = os.getenv(
        "DEFAULT_INPUT_FILE",
        os.path.join(BASE_DATA_DIR, "111.xls")
    )
    
    # 算法结果输出目录
    DEFAULT_OUTPUT_DIR: str = os.getenv(
        "DEFAULT_OUTPUT_DIR",
        os.path.join(BASE_DATA_DIR, "biomass_results")
    )
    
    # 日志目录
    LOG_DIR: str = os.path.join(BASE_DIR, "logs")

    # ------------------------------
    # HDFS 配置 (可选)
    # ------------------------------
    HDFS_HOST: str = os.getenv("HDFS_HOST", "localhost")
    HDFS_PORT: int = int(os.getenv("HDFS_PORT", 9870))
    HDFS_USER: str = os.getenv("HDFS_USER", "hadoop")
    HDFS_ROOT: str = os.getenv("HDFS_ROOT", "/forest")
    HDFS_NEWS_PATH: str = "/forest/news"

    # ------------------------------
    # 初始化逻辑
    # ------------------------------
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ensure_directories()

    def _ensure_directories(self):
        """确保必要的目录存在"""
        dirs_to_create = [
            self.BASE_DATA_DIR,
            self.DEFAULT_OUTPUT_DIR,
            self.LOG_DIR
        ]
        for dir_path in dirs_to_create:
            try:
                os.makedirs(dir_path, exist_ok=True)
            except Exception as e:
                print(f"⚠️ 创建目录失败 {dir_path}: {e}")

    class Config:
        env_file = ENV_FILE_PATH
        env_file_encoding = "utf-8"
        case_sensitive = False  # 环境变量不区分大小写
        extra = "ignore"  # 忽略 .env 中未定义的字段

# ===================== 全局单例 =====================
settings = Settings()

# ===================== 调试信息 (仅在直接运行时打印) =====================
if __name__ == "__main__":
    print("🔍 配置加载检查:")
    print(f"   项目根目录：{settings.BASE_DIR}")
    print(f"   数据目录：{settings.BASE_DATA_DIR}")
    print(f"   输出目录：{settings.DEFAULT_OUTPUT_DIR}")
    print(f"   数据库 URL：{settings.DATABASE_URL.replace(settings.DB_PASSWORD, '***')}")
    print(f"   .env 文件路径：{ENV_FILE_PATH} (存在：{os.path.exists(ENV_FILE_PATH)})")