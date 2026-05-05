import asyncio
import random
import json
import time
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any

# --- 1. 初始化应用 ---
app = FastAPI(title="帽儿山数据模拟后端", description="独立运行的模拟数据服务")

# 允许跨域 (关键：允许你的前端访问)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议指定具体域名，如 ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. 全局配置与状态 ---
# 模拟地理中心 (帽儿山)
CENTER_LON = 127.55
CENTER_LAT = 45.33
GEO_RANGE = 0.08  # 经纬度波动范围

# 树种配置
SPECIES_LIST = ["红松", "落叶松", "白桦", "水曲柳", "紫椴"]
COLOR_MAP = {
    "红松": "#8B4513",
    "落叶松": "#D2691E",
    "白桦": "#F5F5DC",
    "水曲柳": "#228B22",
    "紫椴": "#9370DB"
}

# 内存中的“最新数据”存储 (模拟数据库)
latest_data_store = {
    "metrics": {
        "total_biomass": 1250.0,
        "carbon_storage": 625.0,
        "forest_coverage": 88.5,
        "device_rate": 95.8
    },
    "species_distribution": [],
    "timestamp": 0
}

# --- 3. 数据生成逻辑 ---
def generate_mock_data():
    """
    核心算法：根据上一帧数据生成下一帧数据
    """
    global latest_data_store
    
    # 获取旧数据
    old_metrics = latest_data_store['metrics']

    # A. 模拟指标逻辑
    # 1. 设备接入率：在 95.0 - 96.5 之间微幅随机游走
    new_rate = old_metrics['device_rate'] + random.uniform(-0.15, 0.15)
    new_rate = max(95.0, min(96.5, new_rate)) # 限制范围

    # 2. 森林覆盖率：极稳定，偶尔变动 0.01
    new_coverage = old_metrics['forest_coverage']
    if random.random() > 0.95: # 5% 概率变动
        new_coverage += random.uniform(-0.01, 0.02)

    # 3. 碳储量：基于生物量系数(0.5) + 波动
    simulated_biomass = old_metrics['total_biomass'] + random.uniform(-5, 5)
    new_carbon = simulated_biomass * 0.5 + random.uniform(-2, 2)

    # B. 【关键修复】生成 50 个非空的物种分布点
    points = []
    count = 50  # 固定生成50个点，不再随机30-50，避免空数组
    for _ in range(count):
        species = random.choice(SPECIES_LIST)
        # 严格限制在帽儿山经纬度范围内
        lon = round(random.uniform(CENTER_LON - GEO_RANGE, CENTER_LON + GEO_RANGE), 6)
        lat = round(random.uniform(CENTER_LAT - GEO_RANGE, CENTER_LAT + GEO_RANGE), 6)
        points.append({
            "name": species,
            "lon": lon,
            "lat": lat,
            "value": random.randint(20, 100),
            "color": COLOR_MAP[species]
        })

    # 更新全局存储
    latest_data_store = {
        "timestamp": int(time.time()),
        "metrics": {
            "total_biomass": round(simulated_biomass, 2),
            "carbon_storage": round(new_carbon, 2),
            "forest_coverage": round(new_coverage, 2),
            "device_rate": round(new_rate, 2)
        },
        "species_distribution": points  # 现在points一定非空
    }
    
    return latest_data_store

# --- 4. 接口定义 ---

# 接口 1: RESTful API (用于前端初始化/刷新时获取一次数据)
@app.get("/api/mock/latest")
async def get_latest_data():
    # 【关键】每次请求都生成新数据，保证species_distribution非空
    return generate_mock_data()

# 接口 2: WebSocket (用于实时推送)
@app.websocket("/ws/data")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print(f"客户端连接成功: {websocket.client}")
    try:
        while True:
            # 生成新数据
            data = generate_mock_data()
            # 推送
            await websocket.send_text(json.dumps(data))
            # 间隔 2 秒 (模拟传感器上报频率)
            await asyncio.sleep(2)
    except Exception as e:
        print(f"连接断开或出错: {e}")

# --- 5. 启动命令 ---
# 在终端运行: uvicorn mock_server:app --reload --host 0.0.0.0 --port 5000