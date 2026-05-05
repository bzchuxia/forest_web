# app/api/news.py
from fastapi import APIRouter, HTTPException
from hdfs import InsecureClient, HdfsError
from app.core.config import settings
from app.models.news import NewsItem, NewsListResponse
import json
import logging
import re
from typing import List, Dict, Any

router = APIRouter(tags=["News"])
logger = logging.getLogger(__name__)

# 预编译正则，用于匹配文件名格式 maoershan_news_YYYYMMDD_HHMMSS.json
FILE_PATTERN = re.compile(r"(news_batch|maoershan_news)_\d{8}_\d{6}\.json")

@router.get("/latest", response_model=NewsListResponse)
def get_latest_news(limit: int = 10):
    """
    获取最新的新闻数据
    策略：扫描 HDFS 目录 -> 过滤有效文件 -> 按文件名时间戳倒序 -> 读取最新文件 -> 解析并返回
    """
    client = None
    try:
        # 初始化 HDFS 客户端
        hdfs_url = f'http://{settings.HDFS_HOST}:{settings.HDFS_PORT}'
        client = InsecureClient(hdfs_url, user=settings.HDFS_USER)
        
        # 1. 检查目录是否存在
        if not client.status(settings.HDFS_NEWS_PATH, strict=False):
            logger.warning(f"HDFS 目录不存在: {settings.HDFS_NEWS_PATH}")
            return NewsListResponse(data=[], total=0)
            
        # 2. 列出文件并安全处理返回结构
        try:
            # list 返回通常是迭代器 [(name, status_dict), ...] 或 [status_dict, ...]
            # 我们统一转换为包含 'name' 和 'path' 的列表
            files_info = []
            raw_list = client.list(settings.HDFS_NEWS_PATH, status=True)
            
            for item in raw_list:
                # 兼容不同版本的返回格式
                if isinstance(item, tuple) and len(item) == 2:
                    name, status = item
                    path = status.get('path') or f"{settings.HDFS_NEWS_PATH}/{name}"
                elif isinstance(item, dict):
                    # 如果是纯字典，需要从 path 中提取 name
                    path = item.get('path', '')
                    name = path.split('/')[-1]
                    status = item
                else:
                    continue
                
                files_info.append({'name': name, 'path': path, 'status': status})
                
        except Exception as list_err:
            logger.error(f"HDFS 列表读取失败: {list_err}")
            raise HTTPException(status_code=500, detail="无法读取 HDFS 文件列表")

        if not files_info:
            return NewsListResponse(data=[], total=0)
        
        # 3. 核心过滤：只保留符合命名规范的文件 (排除 _SUCCESS, .tmp 等)
        valid_files = [f for f in files_info if FILE_PATTERN.match(f['name'])]
        
        if not valid_files:
            logger.warning(f"目录 {settings.HDFS_NEWS_PATH} 下未找到有效的新闻文件 (匹配模式: maoershan_news_*.json)")
            return NewsListResponse(data=[], total=0)
        
        # 4. 排序：按文件名倒序 (因为文件名含时间戳，字符串排序即时间排序)
        # 例如: maoershan_news_20260324_174900.json > maoershan_news_20260324_120000.json
        valid_files.sort(key=lambda x: x['name'], reverse=True)
        
        latest_file = valid_files[0]
        latest_file_path = latest_file['path']
        
        logger.info(f"✅ 选定最新文件: {latest_file['name']}")
        
        # 5. 读取文件内容
        all_news: List[Dict[str, Any]] = []
        try:
            with client.read(latest_file_path, encoding='utf-8') as reader:
                content = reader.read()
                if not content:
                    logger.warning(f"文件 {latest_file_path} 内容为空")
                    return NewsListResponse(data=[], total=0)
                
                all_news = json.loads(content)
                
                if not isinstance(all_news, list):
                    logger.error(f"文件格式错误，期望 List 但得到 {type(all_news)}")
                    raise ValueError("JSON 根元素必须是列表")
                    
        except json.JSONDecodeError as je:
            logger.error(f"JSON 解析失败: {je}")
            raise HTTPException(status_code=500, detail="数据格式损坏，无法解析 JSON")
        except Exception as read_err:
            logger.error(f"读取文件流失败: {read_err}")
            raise HTTPException(status_code=500, detail="读取 HDFS 文件内容失败")

        # 6. 数据清洗：去重 (基于 ID)
        unique_map = {item.get('id'): item for item in all_news if item.get('id')}
        unique_list = list(unique_map.values())
        
        # 7. 二次排序：按业务日期 (date 字段) 倒序，防止文件内乱序
        # 增加容错：如果 date 缺失，给一个极小值排到最后
        def safe_date_key(item):
            return item.get('date', '1970-01-01')
            
        sorted_list = sorted(unique_list, key=safe_date_key, reverse=True)
        
        # 8. 截取 Limit
        final_data = sorted_list[:limit]
        
        logger.info(f"📤 成功返回 {len(final_data)} 条新闻 (源文件共 {len(unique_list)} 条)")
        
        return NewsListResponse(data=final_data, total=len(unique_list))
        
    except HdfsError as he:
        logger.error(f"HDFS 连接或操作错误: {he}")
        raise HTTPException(status_code=503, detail=f"HDFS 服务不可用: {str(he)}")
    except Exception as e:
        logger.exception(f"未预期的内部错误: {e}") # exception 会自动打印堆栈
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")
    finally:
        # 虽然 InsecureClient 不需要显式 close，但保持结构清晰
        pass