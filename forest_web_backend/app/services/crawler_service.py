# app/services/crawler_service.py
import requests
from bs4 import BeautifulSoup
import json
import hashlib
import re
import os
import warnings
from datetime import datetime
from typing import List, Optional
from app.core.hdfs_config import hdfs_client, HDFS_ENABLED, HDFS_DATA_ROOT, LOCAL_TASK_ROOT
from app.models.news import NewsItem
import logging

# 忽略 HTTPS 证书警告
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

logger = logging.getLogger(__name__)

class CrawlerService:
    def __init__(self):
        self.hdfs_client = hdfs_client
        self.is_hdfs_mode = HDFS_ENABLED
        
        # 配置存储路径：forest/news
        if self.is_hdfs_mode:
            logger.info("✅ 爬虫服务已启动 [HDFS 模式]")
            # 确保基础目录存在
            self.base_storage_path = f"/forest/news"
            if not self.hdfs_client.status(self.base_storage_path, strict=False):
                self.hdfs_client.makedirs(self.base_storage_path)
        else:
            logger.warning("⚠️ 爬虫服务已启动 [LOCAL 模式]")
            self.base_storage_path = os.path.join(LOCAL_TASK_ROOT, "forest", "news")
            os.makedirs(self.base_storage_path, exist_ok=True)

        # 🎯 核心配置：帽儿山国家野外科学观测研究站
        self.base_url = "https://mef.cern.ac.cn"
        # 科研动态栏目 ID (从你提供的 URL 解析得出)
        self.category_id = "mef15" 
        self.list_url = f"{self.base_url}/list?id={self.category_id}"
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'zh-CN,zh;q=0.9'
        }

    def fetch_news(self, max_pages: int = 3) -> List[NewsItem]:
        """
        专门针对 mef.cern.ac.cn 的爬虫
        自动处理分页和数据结构提取
        """
        logger.info(f"🌲 开始抓取帽儿山森林生态系统观测站数据...")
        logger.info(f"📄 目标栏目：科研动态 (ID: {self.category_id})")
        
        all_news = []
        session = requests.Session()
        session.headers.update(self.headers)

        # 遍历分页
        for page in range(1, max_pages + 1):
            # 构建分页 URL: /list?id=mef15&page=1
            # 注意：第一页通常不需要 page 参数，或者 page=1，根据 HTML 中的 js 逻辑，带 page 参数也是安全的
            current_url = f"{self.list_url}&page={page}" if page > 1 else self.list_url
            
            try:
                logger.debug(f"正在请求第 {page} 页: {current_url}")
                response = session.get(current_url, timeout=10, verify=False)
                response.encoding = 'utf-8' # 该网站通常是 utf-8
                
                if response.status_code != 200:
                    logger.warning(f"⚠️ 第 {page} 页请求失败: {response.status_code}")
                    break

                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 🔍 精准定位：查找包含新闻列表的 table
                # 根据 HTML: <div class="list"> -> <table> -> <tr>
                news_table = soup.find('div', class_='list')
                if not news_table:
                    logger.warning(f"⚠️ 第 {page} 页未找到新闻列表区域，可能已无更多数据")
                    break
                
                rows = news_table.find('table').find_all('tr')
                page_count = 0
                
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) < 2:
                        continue
                    
                    # 提取标题和链接 (第一个 td.class="link")
                    link_td = cols[0]
                    a_tag = link_td.find('a')
                    if not a_tag:
                        continue
                    
                    title = a_tag.get_text(strip=True)
                    href = a_tag.get('href')
                    
                    # 提取日期 (第二个 td.class="time")
                    time_td = cols[1]
                    time_a = time_td.find('a')
                    date_str_raw = time_a.get_text(strip=True) if time_a else ""
                    
                    # 数据清洗
                    if not title or not href:
                        continue
                    
                    # 补全链接 (处理相对路径 /content?id=...)
                    if href.startswith('/'):
                        full_url = f"{self.base_url}{href}"
                    else:
                        full_url = href
                    
                    # 解析日期 [2024-10-11] -> 2024-10-11
                    pub_date = self._parse_date(date_str_raw)
                    
                    # 去重检查 (基于标题)
                    if any(n.title == title for n in all_news):
                        continue

                    # 构建内容摘要
                    content_summary = f"【帽儿山观测站】{title}。发布日期：{pub_date}。来源：黑龙江帽儿山森林生态系统国家野外科学观测研究站。详情：{full_url}"
                    
                    # 生成唯一 ID
                    news_id = hashlib.md5(f"{title}{full_url}".encode()).hexdigest()

                    all_news.append(NewsItem(
                        id=news_id,
                        title=title,
                        date=pub_date,
                        source="黑龙江帽儿山森林生态系统国家野外科学观测研究站",
                        content=content_summary,
                        url=full_url
                    ))
                    page_count += 1

                logger.info(f"📄 第 {page} 页解析完成，新增 {page_count} 条")
                
                # 如果某页没有抓取到数据，说明已经到底了，提前结束
                if page_count == 0:
                    logger.info("✅ 已抓取完所有可用页面")
                    break

            except Exception as e:
                logger.error(f"❌ 抓取第 {page} 页时发生异常: {e}")
                continue

        logger.info(f"🎉 抓取结束，共获取有效新闻 {len(all_news)} 条")
        return all_news

    def _parse_date(self, date_str: str) -> str:
        """清洗日期格式：[2024-10-11] -> 2024-10-11"""
        if not date_str:
            return datetime.now().strftime("%Y-%m-%d")
        
        # 去除方括号和空格
        clean_date = re.sub(r'[\\[\\]\\s]', '', date_str)
        
        # 验证格式是否为 YYYY-MM-DD
        if re.match(r'\d{4}-\d{2}-\d{2}', clean_date):
            return clean_date
        
        # 如果格式不对，返回今天
        return datetime.now().strftime("%Y-%m-%d")

    def save_to_storage(self, news_list: List[NewsItem]) -> str:
        """
        保存到 HDFS 或本地
        路径规则：.../forest/news/YYYYMMDD_HHMMSS.json
        """
        if not news_list:
            logger.warning("⚠️ 没有数据需要保存")
            return ""

        # 生成带时间戳的文件名，方便管理
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"maoershan_news_{timestamp}.json"
        
        # 确定完整路径
        if self.is_hdfs_mode:
            full_path = f"{self.base_storage_path}/{file_name}"
        else:
            full_path = os.path.join(self.base_storage_path, file_name)

        # 准备数据
        # 兼容 Pydantic V1 和 V2
        data_json = []
        for item in news_list:
            if hasattr(item, 'model_dump'): # Pydantic V2
                data_json.append(item.model_dump())
            else: # Pydantic V1
                data_json.append(item.dict())
        
        json_str = json.dumps(data_json, ensure_ascii=False, indent=2)

        try:
            if self.is_hdfs_mode and self.hdfs_client:
                # HDFS 写入
                with self.hdfs_client.write(full_path, encoding='utf-8') as writer:
                    writer.write(json_str)
                logger.info(f"💾 [HDFS] 数据成功保存至: {full_path}")
            else:
                # 本地写入
                # 确保目录存在
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(json_str)
                logger.info(f"💾 [LOCAL] 数据成功保存至: {full_path}")
            
            return full_path

        except Exception as e:
            logger.error(f"❌ 文件保存失败: {e}")
            raise e

    def run_full_process(self):
        """执行完整流程"""
        logger.info("🚀 启动帽儿山科研新闻采集任务...")
        try:
            # 1. 抓取 (默认抓取前 3 页，可根据需要调整)
            news_data = self.fetch_news(max_pages=3)
            
            if not news_data:
                logger.warning("⚠️ 本次未抓取到任何新数据")
                return None
            
            # 2. 保存
            saved_path = self.save_to_storage(news_data)
            
            logger.info(f"✨ 任务圆满完成！共处理 {len(news_data)} 条数据，存储位置：{saved_path}")
            return saved_path
            
        except Exception as e:
            logger.error(f"💥 任务执行失败: {e}")
            raise e

# 单例模式
crawler_service = CrawlerService()