# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import os
import warnings
import sys
from datetime import datetime
from contextlib import asynccontextmanager


# ===================== 全局警告过滤 (必须在导入 rasterio/sklearn 之前) =====================
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", message=".*CPLE_AppDefined.*")
warnings.filterwarnings("ignore", message=".*PROJ.*version.*")
warnings.filterwarnings("ignore", message=".*rasterio.*env.*")
warnings.filterwarnings("ignore", message=".*FutureWarning.*")
warnings.filterwarnings("ignore", message=".*numpy.*dtype.*") # 常见 numpy 警告

# ===================== 日志配置 =====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ===================== 数据库初始化 =====================
from app.core.config import settings
from app.database import engine, Base

try:
    # 创建所有表 (checkfirst=True 确保表存在时不报错)
    Base.metadata.create_all(bind=engine, checkfirst=True)
    logger.info("✅ 数据库表结构检查/创建完成")
except Exception as e:
    logger.error(f"❌ 数据库初始化失败：{str(e)}")
    # 开发环境可以选择继续运行，生产环境建议退出
    # sys.exit(1) 

# ===================== 导入 Spark 引擎 =====================
try:
    from app.tool.spark_engine import spark_engine  # <--- 新增 Spark 导入
except ImportError:
    spark_engine = None
    logger.warning("⚠️ 未找到 Spark 引擎，跳过优雅关闭")

# ===================== 优雅关闭生命周期（核心！） =====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # -------------- 启动时执行 --------------
    logger.info("✅ 服务启动成功")
    yield
    # -------------- 关闭时执行 --------------
    logger.info("\n🔌 正在执行优雅关闭流程...")
    
    # 1. 安全关闭 Spark
    if spark_engine is not None:
        try:
            spark_engine.stop()
            logger.info("✅ Spark 引擎已安全关闭")
        except Exception as e:
            logger.warning(f"⚠️ Spark 关闭时出现可忽略警告: {str(e)}")
    
    # 2. 关闭数据库连接（可选）
    try:
        if 'engine' in locals():
            engine.dispose()
            logger.info("✅ 数据库连接已释放")
    except:
        pass
    
    logger.info("✅ 服务已完全关闭")

# ===================== FastAPI 应用实例 =====================
app = FastAPI(
    title="帽儿山生物量数字孪生平台工具箱",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    description="""
    ## 功能模块
    - **用户鉴权**: 登录/注册/信息管理
    - **算法任务**: 生物量预测模型训练 / 空间预测 / 单目标提取
    - **文件服务**: 结果下载 / 图片预览 / HDFS 代理
    - **新闻资讯**: 林业新闻自动抓取
    
    ## 存储模式
    - 优先使用 **HDFS** 集群存储大规模结果
    - 自动降级到 **本地文件系统**
    """
)

# ===================== 中间件配置 =====================
# 处理跨域问题
# 使用 settings 中解析好的列表，支持 "*" 或 ["http://a.com", "http://b.com"]
cors_origins = settings.CORS_ORIGINS_LIST
if cors_origins == ["*"]:
    logger.warning("⚠️ 当前允许所有来源跨域 (CORS *)，生产环境建议指定具体域名")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===================== 路由挂载 (核心逻辑) =====================
# 强制从 app.api 导入聚合路由，确保前缀管理统一
try:
    from app.api import api_router as main_api_router
    
    # 统一挂载到 /api 前缀下
    # 子路由的具体路径 (如 /task/run) 在 app/api/__init__.py 中定义
    app.include_router(main_api_router, prefix="/api")
    
    logger.info("✅ 已挂载主 API 路由 (/api)")
    
except ImportError as e:
    logger.error(f"❌ 严重错误：无法导入聚合路由 app.api.api_router")
    logger.error(f"   错误详情：{str(e)}")
    logger.error("   请检查 app/api/__init__.py 是否存在且正确导出了 api_router")
    sys.exit(1)

# ===================== 系统端点 =====================
@app.get("/", tags=["系统状态"])
def root():
    return {
        "status": "running",
        "service": "帽儿山生物量预测工具箱",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "swagger_docs": "/docs",
            "redoc_docs": "/redoc",
            "api_base": "/api",
            "health_check": "/health"
        },
        "storage_mode": "HDFS" if getattr(settings, 'HDFS_HOST', None) else "LOCAL"
    }

@app.get("/health", tags=["系统状态"])
def health_check():
    """K8s/Docker 健康检查端点"""
    return {
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "database": "connected" # 简单判断，实际可加 ping 测试
    }

# ===================== 启动入口 =====================
if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🚀 正在启动帽儿山生物量数字孪生平台...")
    logger.info("=" * 60)
    logger.info(f"📡 监听地址：http://{settings.API_HOST}:{settings.API_PORT}")
    logger.info(f"📂 数据根目录：{settings.BASE_DIR}")
    logger.info(f"💾 数据存储区：{settings.BASE_DATA_DIR}")
    logger.info(f"📝 日志目录：{settings.LOG_DIR}")
    
    if hasattr(settings, 'HDFS_HOST'):
        logger.info(f"🌐 HDFS 模式：{'启用' if os.getenv('HDFS_ENABLED', 'False').lower() == 'true' else '禁用 (将使用本地存储)'}")
        if os.getenv('HDFS_ENABLED', 'False').lower() == 'true':
            logger.info(f"   NameNode: {settings.HDFS_HOST}:{settings.HDFS_PORT}")
    
    logger.info("=" * 60)
    logger.info("📖 API 文档地址:")
    logger.info(f"   Swagger UI: http://{settings.API_HOST}:{settings.API_PORT}/docs")
    logger.info(f"   ReDoc:      http://{settings.API_HOST}:{settings.API_PORT}/redoc")
    logger.info("=" * 60)
    
    try:
        uvicorn.run(
            "main:app",
            host=settings.API_HOST,
            port=settings.API_PORT,
            reload=False,      # 生产环境务必为 False
            workers=1,         # 多进程需配合 gunicorn，此处单进程保证日志清晰
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("👋 收到中断信号，正在停止服务...")
    except Exception as e:
        logger.error(f"💥 服务启动失败：{str(e)}")
        sys.exit(1)