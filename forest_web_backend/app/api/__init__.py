# app/api/__init__.py
from fastapi import APIRouter
from .user import router as user_router
from .task import router as task_router  
from .file import router as file_router
from .biomass import router as biomass_router 
from .model_train import router as fast_router
from .report import router as report_router
from . import news
import logging

api_router = APIRouter()

# ✅ 统一在这里加前缀
# 最终路径 = main.py的"/api" + 这里的"/task" + task.py里的"/run" = /api/task/run
api_router.include_router(task_router, prefix="/task", tags=["算法任务"])

# 用户路由示例
api_router.include_router(user_router, prefix="/user", tags=["用户管理"])

# 文件路由示例
api_router.include_router(file_router, prefix="/file", tags=["文件管理"])

# 新闻路由
api_router.include_router(news.router, prefix="/news", tags=["新闻资讯"])

api_router.include_router(biomass_router , prefix="/biomass", tags=["数据加载"])

api_router.include_router(fast_router , prefix="/fast", tags=["模型训练"])

api_router.include_router(report_router, prefix="/report", tags=["智能报告"])

logger = logging.getLogger(__name__)
logger.info("✅ app/api/__init__.py 已执行，当前注册的子路由数量: %d", len(api_router.routes))

__all__ = ["api_router"]