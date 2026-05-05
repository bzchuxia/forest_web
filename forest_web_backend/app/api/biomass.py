from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
import pandas as pd
import os
import json
import tempfile
import logging

# 🔥 核心修复 1: 导入缺失的 Schema 和 Service 函数
from app.schemas import TaskStatusResponse
from app.services.task_service import get_task_status

# 🔥 核心修复 2: 导入全局 HDFS 配置 (不要在本文件重复定义 URL 或 Client)
from app.core.hdfs_config import (
    HDFS_ENABLED, 
    hdfs_client, 
    HDFS_TASK_ROOT, 
    LOCAL_TASK_ROOT,
    HDFS_ROOT
)

# VLM 引擎
from app.ml.vlm_engine import run_vlm_biomass_estimation

logger = logging.getLogger("biomass_api")
router = APIRouter()

# ===================== 路径配置 (基于全局配置衍生) =====================
# 动态计算本地项目根目录
CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(CURRENT_FILE_DIR)
PROJECT_ROOT = os.path.dirname(APP_DIR)

# 1. 本地数据文件路径 (采样点/热力图)
LOCAL_DATA_DIR = os.path.join(PROJECT_ROOT, "data")
os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
LOCAL_SAMPLE_FILE = os.path.join(LOCAL_DATA_DIR, "111.xlsx")
LOCAL_HEATMAP_FILE = os.path.join(LOCAL_DATA_DIR, "simple_heatmap.geojson")

# 2. HDFS 数据文件路径 (基于全局 HDFS_ROOT)
HDFS_DATA_DIR = f"{HDFS_ROOT}/data"
HDFS_SAMPLE_FILE = "/forest/111.xlsx"
HDFS_HEATMAP_FILE = f"{HDFS_DATA_DIR}/simple_heatmap.geojson"

# 初始化检查 (确保目录存在)
if HDFS_ENABLED and hdfs_client:
    try:
        if not hdfs_client.status(HDFS_DATA_DIR, strict=False):
            hdfs_client.makedirs(HDFS_DATA_DIR)
        logger.info(f"✅ [biomass.py] HDFS 数据目录就绪：{HDFS_DATA_DIR}")
    except Exception as e:
        logger.warning(f"⚠️ [biomass.py] HDFS 目录检查失败：{str(e)}")

# ===================== 核心工具函数 =====================
def download_file_from_hdfs(hdfs_path: str, local_temp_path: str) -> str:
    """
    从 HDFS 下载文件到本地临时路径
    """
    if not hdfs_client:
        raise Exception("HDFS 客户端未初始化")
    
    try:
        hdfs_client.download(hdfs_path, local_temp_path, overwrite=True)
        logger.info(f"✅ 从 HDFS 下载文件成功：{hdfs_path} -> {local_temp_path}")
        return local_temp_path
    except Exception as e:
        raise Exception(f"HDFS 文件下载失败：{hdfs_path}，错误：{str(e)}")

def read_file_from_hdfs(hdfs_path: str, file_type: str = "text") -> Any:
    """
    直接从 HDFS 读取文件内容
    """
    if not hdfs_client:
        raise Exception("HDFS 客户端未初始化")
    
    try:
        with hdfs_client.read(hdfs_path, encoding="utf-8") as f:
            content = f.read()
            if file_type == "json":
                return json.loads(content)
            return content
    except Exception as e:
        raise Exception(f"HDFS 文件读取失败：{hdfs_path}，错误：{str(e)}")

def get_file_path(file_type: str) -> tuple:
    """
    获取文件路径（优先 HDFS，降级本地）
    :return: (is_hdfs, file_path, storage_type)
    """
    hdfs_path = ""
    local_path = ""
    
    if file_type == "sample":
        hdfs_path = HDFS_SAMPLE_FILE
        local_path = LOCAL_SAMPLE_FILE
    elif file_type == "heatmap":
        hdfs_path = HDFS_HEATMAP_FILE
        local_path = LOCAL_HEATMAP_FILE
    else:
        raise ValueError(f"不支持的文件类型：{file_type}")
    
    print("=" * 50)
    print(f"🚨 [DEBUG] 正在查找文件类型：{file_type}")
    print(f"🚨 [DEBUG] HDFS_ENABLED 状态：{HDFS_ENABLED}")
    print(f"🚨 [DEBUG] 代码计算的 HDFS 绝对路径：{hdfs_path}") 
    print(f"🚨 [DEBUG] 代码计算的本地绝对路径：{local_path}")
          
    # 优先检查 HDFS
    if HDFS_ENABLED and hdfs_client:
        try:
            if hdfs_client.status(hdfs_path, strict=False):
                return True, hdfs_path, "HDFS"
        except Exception as e:
            logger.warning(f"HDFS 状态检查失败，尝试降级本地：{str(e)}")
    
    # 降级到本地
    if os.path.exists(local_path):
        return False, local_path, "LOCAL"
    
    # 文件不存在
    raise FileNotFoundError(f"{file_type}文件不存在\nHDFS 路径：{hdfs_path}\n本地路径：{local_path}")

# ===================== 模型定义 =====================
class SamplePoint(BaseModel):
    jindu: float  # 经度
    weidu: float  # 纬度
    AGB: float    # 生物量

class VLMPredictionRequest(BaseModel):
    image_path: str
    prompt: Optional[str] = None
    model_name: Optional[str] = "Qwen/Qwen2-VL-7B-Instruct"

class BaseResponse(BaseModel):
    code: int = 200
    msg: str
    data: Any
    storage_type: Optional[str] = None

# ===================== 接口 1：采样点数据 (强制本地绝对路径版) =====================
@router.get("/samplePoints", response_model=BaseResponse)
async def get_sample_points(year: Optional[int] = 2023):
    """
    直接从指定的本地绝对路径读取采样点 Excel 文件。
    完全绕过 HDFS 检查和动态路径计算。
    """
    # 🔴 强制指定绝对路径
    file_path = r"D:\desktop\forest_web\forest_web_backend\data\111.xlsx"
    
    # 1. 预先检查文件是否存在，给出明确报错
    if not os.path.exists(file_path):
        error_msg = f"❌ 文件未找到！请确认文件是否存在于：{file_path}"
        logger.error(error_msg)
        raise HTTPException(status_code=404, detail=error_msg)
    
    try:
        logger.info(f"📖 正在读取本地固定路径：{file_path}")
        
        # 2. 直接读取 Excel (不再区分 HDFS/本地，不再创建临时文件)
        df = pd.read_excel(file_path)
        
        # 3. 按年份过滤
        if "year" in df.columns:
            original_count = len(df)
            df = df[df["year"] == year]
            logger.info(f" 原始数据 {original_count} 条，过滤后 ({year}年) 剩余 {len(df)} 条")
        else:
            logger.warning("⚠️ Excel 中未检测到 'year' 列，返回所有数据")
        
        # 4. 转换为字典列表
        data = df.to_dict("records")
        
        return BaseResponse(
            msg=f"成功获取 {len(data)} 个采样点数据 (本地直读模式)",
            data=data,
            storage_type="LOCAL_FIXED_PATH" # 标记为固定本地路径
        )
    
    except Exception as e:
        error_detail = f"读取 Excel 失败：{str(e)}"
        logger.error(f"💥 {error_detail}", exc_info=True)
        raise HTTPException(status_code=500, detail=error_detail)

# ===================== 接口 2：热力图数据 =====================
@router.get("/heatmap", response_model=BaseResponse)
async def get_biomass_heatmap(year: Optional[int] = Query(2023, description="查询年份")):
    try:
        is_hdfs, file_path, storage_type = get_file_path("heatmap")
        geojson_data = None
        
        if is_hdfs:
            geojson_data = read_file_from_hdfs(file_path, file_type="json")
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                geojson_data = json.load(f)
        
        # 按年份过滤
        if "features" in geojson_data and geojson_data["features"]:
            filtered_features = [
                f for f in geojson_data["features"]
                if f.get("properties", {}).get("year", year) == year
            ]
            geojson_data["features"] = filtered_features
        
        return BaseResponse(
            msg=f"成功读取 {len(geojson_data.get('features', []))} 个热力图要素（存储类型：{storage_type}）",
            data=geojson_data,
            storage_type=storage_type
        )
    
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"读取热力图失败：{str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"读取热力图失败：{str(e)}")

# ===================== 接口 3：上传文件到 HDFS =====================
@router.post("/upload/sample", response_model=BaseResponse)
async def upload_sample_file(file_path: str = Query(..., description="本地 Excel 文件路径")):
    try:
        if not HDFS_ENABLED or not hdfs_client:
            raise Exception("HDFS 客户端未初始化，无法上传文件")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"本地文件不存在：{file_path}")
        
        hdfs_client.upload(HDFS_SAMPLE_FILE, file_path, overwrite=True)
        
        return BaseResponse(
            msg=f"采样点文件成功上传到 HDFS：{HDFS_SAMPLE_FILE}",
            data={"local_path": file_path, "hdfs_path": HDFS_SAMPLE_FILE},
            storage_type="HDFS"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传采样点文件失败：{str(e)}")

@router.post("/upload/heatmap", response_model=BaseResponse)
async def upload_heatmap_file(file_path: str = Query(..., description="本地 GeoJSON 文件路径")):
    try:
        if not HDFS_ENABLED or not hdfs_client:
            raise Exception("HDFS 客户端未初始化，无法上传文件")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"本地文件不存在：{file_path}")
        
        hdfs_client.upload(HDFS_HEATMAP_FILE, file_path, overwrite=True)
        
        return BaseResponse(
            msg=f"热力图文件成功上传到 HDFS：{HDFS_HEATMAP_FILE}",
            data={"local_path": file_path, "hdfs_path": HDFS_HEATMAP_FILE},
            storage_type="HDFS"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传热力图文件失败：{str(e)}")

# ===================== 接口 4：查询任务状态 (修复导入错误) =====================
@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status_api(task_id: str):
    """
    查询任务状态：增强 HDFS 读取的容错性
    """
    try:
        # 1. 获取内存/DB 中的基础状态
        task_info = get_task_status(task_id)
        if not task_info:
            raise HTTPException(status_code=404, detail=f"任务 ID 不存在：{task_id}")
        
        # 初始化返回字段
        task_info["storage_type"] = "UNKNOWN"
        task_info["result_path"] = ""
        task_info["best_model_spatial_result"] = {}
        task_info["all_models_spatial_results"] = {}
        task_info["best_model_name"] = ""
        task_info["best_geojson_path"] = ""
        
        metadata_filename = f"{task_id}_metadata.json"
        
        # ================= HDFS 读取逻辑 =================
        if HDFS_ENABLED and hdfs_client:
            hdfs_metadata_path = f"{HDFS_TASK_ROOT}/{metadata_filename}"
            try:
                if hdfs_client.status(hdfs_metadata_path, strict=False):
                    logger.info(f"🔍 [HDFS] 读取元数据：{hdfs_metadata_path}")
                    
                    with hdfs_client.read(hdfs_metadata_path, encoding='utf-8') as f:
                        metadata_content = f.read()
                        metadata = json.loads(metadata_content)
                    
                    task_info["result_path"] = metadata.get("result_path", "")
                    task_info["storage_type"] = "HDFS"

                    result_hdfs_path = metadata.get("result_path")
                    if result_hdfs_path:
                        try:
                            if hdfs_client.status(result_hdfs_path, strict=False):
                                logger.info(f"🔍 [HDFS] 读取结果详情：{result_hdfs_path}")
                                with hdfs_client.read(result_hdfs_path, encoding='utf-8') as f:
                                    result_content = f.read()
                                    result_data = json.loads(result_content)
                                
                                task_info["best_model_spatial_result"] = result_data.get("best_model_spatial_result", {})
                                task_info["all_models_spatial_results"] = result_data.get("all_models_spatial_results", {})
                                task_info["best_model_name"] = result_data.get("best_model_name", "")
                                task_info["best_geojson_path"] = result_data.get("best_geojson_path", "")
                            else:
                                logger.warning(f"⚠️ [HDFS] 结果文件尚未生成：{result_hdfs_path}")
                        except Exception as read_err:
                            logger.warning(f"⚠️ [HDFS] 读取结果文件失败：{str(read_err)}")
                    
                    return task_info
                else:
                    logger.warning(f"⚠️ [HDFS] 元数据文件不存在，尝试降级本地")
            except Exception as hdfs_err:
                logger.error(f"❌ [HDFS ERROR] 访问 HDFS 失败：{str(hdfs_err)}")
                # 不 raise，继续执行本地逻辑
        
        # ================= 本地降级逻辑 =================
        local_metadata_path = os.path.join(LOCAL_TASK_ROOT, metadata_filename)
        if os.path.exists(local_metadata_path):
            try:
                with open(local_metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                task_info["result_path"] = metadata.get("result_path", "")
                task_info["storage_type"] = "LOCAL"

                result_local_path = metadata.get("result_path")
                if result_local_path and os.path.exists(result_local_path):
                    with open(result_local_path, 'r', encoding='utf-8') as f:
                        result_data = json.load(f)
                    
                    task_info["best_model_spatial_result"] = result_data.get("best_model_spatial_result", {})
                    task_info["all_models_spatial_results"] = result_data.get("all_models_spatial_results", {})
                    task_info["best_model_name"] = result_data.get("best_model_name", "")
                    task_info["best_geojson_path"] = result_data.get("best_geojson_path", "")
                
                return task_info
            except Exception as local_err:
                logger.error(f"❌ [LOCAL ERROR] 读取本地文件失败：{str(local_err)}")
        
        return task_info

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"❌ [CRITICAL] 查询任务状态异常：{str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"查询服务内部错误：{str(e)}")

# ===================== 接口 5：VLM 估算 =====================
@router.post("/vlm/estimate", response_model=BaseResponse)
async def estimate_biomass_vlm(req: VLMPredictionRequest):
    """
    使用视觉大模型 (VLM) 估算生物量
    """
    # 动态生成输出路径，避免硬编码 /data/results
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    safe_name = os.path.basename(req.image_path).replace(".", "_").replace("/", "_")
    
    if HDFS_ENABLED and hdfs_client:
        # HDFS 模式：先存本地临时，后续可上传，或直接存本地供本次返回
        output_dir = os.path.join(LOCAL_DATA_DIR, "vlm_results")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"vlm_{safe_name}_{timestamp}.json")
        storage_type = "HDFS_READY"
    else:
        output_dir = os.path.join(LOCAL_DATA_DIR, "vlm_results")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"vlm_{safe_name}_{timestamp}.json")
        storage_type = "LOCAL"
    
    try:
        result = run_vlm_biomass_estimation(
            image_path=req.image_path,
            output_json_path=output_path,
            prompt=req.prompt,
            model_name=req.model_name
        )
        
        return BaseResponse(
            msg="VLM 分析成功",
            data=result,
            storage_type=storage_type
        )
    except Exception as e:
        logger.error(f"VLM 估算失败：{str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI 分析失败：{str(e)}")