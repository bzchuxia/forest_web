import sys
import os
import time
import logging
from datetime import datetime

# 将项目根目录加入路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.crawler_service import crawler_service

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/crawler_daemon.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("🚀 爬虫守护进程已启动，将每分钟执行一次...")
    
    while True:
        try:
            start_time = time.time()
            logger.info(f"⏰ [{datetime.now()}] 开始执行爬虫任务...")
            
            crawler_service.run_full_process()
            
            end_time = time.time()
            duration = end_time - start_time
            logger.info(f"✅ 爬虫任务执行成功，耗时 {duration:.2f} 秒")
            
        except Exception as e:
            logger.error(f"❌ 爬虫任务执行失败: {e}", exc_info=True)
        
        # 计算需要等待的时间，确保整分钟执行一次
        # 例如：如果任务跑了 10 秒，则等待 50 秒，总共凑够 60 秒
        sleep_time = 60 - (time.time() - start_time)
        if sleep_time > 0:
            logger.info(f"💤 等待 {sleep_time:.2f} 秒后下一次执行...")
            time.sleep(sleep_time)
        else:
            logger.warning("⚠️ 任务执行时间超过 60 秒，立即开始下一次执行（可能导致重叠）")