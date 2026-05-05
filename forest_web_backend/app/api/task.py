from fastapi import APIRouter, BackgroundTasks, HTTPException
from starlette.responses import StreamingResponse
from typing import Dict, Any, Optional
import numpy as np
from app.core.config import settings
import os
import json
import time
import re

# ===================== 导入公共HDFS配置 =====================
from app.core.hdfs_config import (
    HDFS_ENABLED, 
    hdfs_client, 
    HDFS_TASK_ROOT, 
    HDFS_RESULTS_ROOT,  # 解决 "未定义 HDFS_RESULTS_ROOT" 报错
    LOCAL_TASK_ROOT,
    HDFS_ROOT
)

# ===================== 导入空间预测核心函数 =====================
from app.ml.biomass_pred import generate_spatial_biomass_map

from app.schemas import TaskCreate, TaskStatus, TaskStatusResponse,ChatMessage, ChatResponse
from app.services.task_service import create_task, run_algorithm_task, get_task_status
from app.services.ai_service import get_ai_response
router = APIRouter(tags=["算法任务"])

# ===================== 核心工具函数 =====================
def save_task_metadata(task_id: str, task_data: Dict[str, Any]):
    """
    保存任务元数据：优先HDFS，失败则本地
    """
    timestamp = task_data.get("timestamp", "unknown_time")
    metadata_filename = f"{task_id}_metadata.json"
    
    if HDFS_ENABLED and hdfs_client:
        try:
            hdfs_dir = f"{HDFS_TASK_ROOT}/{timestamp}"
            hdfs_path = f"{hdfs_dir}/{metadata_filename}"
            # 1. 如果目录不存在，先创建目录
            if not hdfs_client.status(hdfs_dir, strict=False):
                hdfs_client.makedirs(hdfs_dir)
                print(f"📁 [HDFS] 创建目录：{hdfs_dir}")

            hdfs_client.write(
                hdfs_path, 
                json.dumps(task_data, ensure_ascii=False, indent=2), 
                encoding='utf-8',
                overwrite=True  
            )
            print(f"✅ 任务元数据已保存到 HDFS：{hdfs_path}")
            return hdfs_path
        except Exception as e:
            print(f"⚠️ [HDFS] 保存元数据失败，将降级到本地：{str(e)}")
    
    local_dir = os.path.join(LOCAL_TASK_ROOT, timestamp)
    os.makedirs(local_dir, exist_ok=True)

    local_path = os.path.join(local_dir, metadata_filename)
    with open(local_path, 'w', encoding='utf-8') as f:
        json.dump(task_data, f, ensure_ascii=False, indent=2)
    print(f"✅ 任务元数据已保存到本地：{local_path}")
    return local_path

def save_task_result(task_id: str, result_data: Dict[str, Any]):
    """
    保存任务结果：
    1. 过滤不可序列化数据 (numpy等)
    2. 提取时间戳创建专属文件夹
    3. 优先存 HDFS，失败存本地
    4. 强制覆盖旧文件
    """
    # --- 数据清洗 (保持不变) ---
    def filter_serializable(data):
        if isinstance(data, dict):
            filtered = {}
            for key, value in data.items():
                if key in ["model", "base_models", "meta_model", "estimator", "cv", "scaler"]:
                    continue
                filtered[key] = filter_serializable(value)
            return filtered
        elif isinstance(data, list):
            return [filter_serializable(item) for item in data]
        elif isinstance(data, (int, float, str, bool, type(None))):
            return data
        elif isinstance(data, np.ndarray):
            return data.tolist()
        elif isinstance(data, (np.floating, np.integer)):
            return float(data) if isinstance(data, np.floating) else int(data)
        else:
            return str(data)
    
    serializable_result = filter_serializable(result_data)
    timestamp = result_data.get("timestamp", "unknown_time")
    result_filename = f"{task_id}_result.json"
    
    # --- HDFS 逻辑 ---
    if HDFS_ENABLED and hdfs_client:
        try:
            # 🔥 关键：构建带时间戳的目录路径 /forest/results/{timestamp}/
            hdfs_dir = f"{HDFS_RESULTS_ROOT}/{timestamp}"
            hdfs_path = f"{hdfs_dir}/{result_filename}"
            
            # 1. 如果目录不存在，先创建目录
            if not hdfs_client.status(hdfs_dir, strict=False):
                hdfs_client.makedirs(hdfs_dir)
                print(f"📁 [HDFS] 创建结果目录：{hdfs_dir}")
            
            # 2. 写入结果文件 (overwrite=True)
            hdfs_client.write(
                hdfs_path, 
                json.dumps(serializable_result, ensure_ascii=False, indent=2), 
                encoding='utf-8',
                overwrite=True
            )
            
            # 3. 更新元数据中的 result_path 指向新位置
            metadata_filename = f"{task_id}_metadata.json"
            metadata_hdfs_dir = f"{HDFS_TASK_ROOT}/{timestamp}"
            metadata_hdfs_path = f"{metadata_hdfs_dir}/{metadata_filename}"
            
            if hdfs_client.status(metadata_hdfs_path, strict=False):
                with hdfs_client.read(metadata_hdfs_path) as reader:
                    meta_str = reader.read().decode('utf-8')
                metadata = json.loads(meta_str)
                
                metadata['result_path'] = hdfs_path # 记录 HDFS 路径
                metadata['storage_type'] = 'HDFS'
                
                hdfs_client.write(
                    metadata_hdfs_path,
                    json.dumps(metadata, ensure_ascii=False, indent=2),
                    encoding='utf-8',
                    overwrite=True
                )
            
            print(f"✅ [HDFS] 结果已保存：{hdfs_path}")
            return hdfs_path
        except Exception as e:
            print(f"⚠️ [HDFS] 保存结果失败，将降级到本地：{str(e)}")
            import traceback
            traceback.print_exc()
    
    # --- 本地逻辑 (降级方案) ---
    local_dir = os.path.join(settings.BASE_DATA_DIR, "biomass_results", timestamp)
    os.makedirs(local_dir, exist_ok=True)
    local_path = os.path.join(local_dir, result_filename)

    with open(local_path, 'w', encoding='utf-8') as f:
        json.dump(serializable_result, f, ensure_ascii=False, indent=2)
    
    # 更新本地元数据
    metadata_local_dir = os.path.join(LOCAL_TASK_ROOT, timestamp)
    metadata_local_path = os.path.join(metadata_local_dir, f"{task_id}_metadata.json")
    
    if os.path.exists(metadata_local_path):
        with open(metadata_local_path, 'r+', encoding='utf-8') as f:
            metadata = json.load(f)
            metadata['result_path'] = local_path
            metadata['storage_type'] = 'LOCAL'
            f.seek(0)
            json.dump(metadata, f, ensure_ascii=False, indent=2)
            f.truncate()
            
    print(f"✅ [LOCAL] 结果已保存：{local_path}")
    return local_path

# ===================== 自动执行空间预测的函数（核心修复） =====================
def run_spatial_prediction_after_ml(task_id: str, result: Dict[str, Any]):
    """
    机器学习任务成功后执行空间预测：
    【核心修复】智能查找模型文件 (优先 HDFS -> 降级本地)，并自动清理临时文件
    """
    temp_files_to_clean = [] # 记录需要清理的临时下载文件
    
    try:
        # 1. 基础数据补全
        if "feature_count" not in result:
            best_info = result.get("best_model_info", {})
            result["feature_count"] = best_info.get("feature_count", 0)
        if "statistics" not in result:
            result["statistics"] = {}
        if "feature_count" not in result["statistics"]:
            result["statistics"]["feature_count"] = result.get("feature_count", 0)

        timestamp = result.get("timestamp")
        if not timestamp:
            error_msg = f"❌ 任务 {task_id} 无有效时间戳，终止空间预测"
            print(error_msg)
            result["spatial_prediction_error"] = error_msg
            save_task_result(task_id, result)
            raise ValueError(error_msg)
        
        all_models = result.get("all_models", {})
        final_model_paths = {} 
        final_feat_paths = {}

        print(f"🔍 开始准备空间预测所需的模型文件 (时间戳：{timestamp})...")

        # 2. 智能获取文件路径 (核心逻辑)
        for model_name, model_info in all_models.items():
            model_filename = f"{model_name}_model_{timestamp}.joblib"
            feat_filename = f"{model_name}_feature_list_{timestamp}.joblib"
            
            # 构造可能的路径
            hdfs_base = f"{HDFS_RESULTS_ROOT}/{timestamp}"
            hdfs_model_path = f"{hdfs_base}/{model_filename}"
            hdfs_feat_path = f"{hdfs_base}/{feat_filename}"
            
            local_base = os.path.join(settings.BASE_DATA_DIR, "biomass_results", timestamp)
            local_model_path = os.path.join(local_base, model_filename)
            local_feat_path = os.path.join(local_base, feat_filename)
            
            chosen_model_path = ""
            chosen_feat_path = ""
            
            # --- 策略 A: 优先尝试 HDFS ---
            if HDFS_ENABLED and hdfs_client:
                if hdfs_client.status(hdfs_model_path, strict=False):
                    print(f"✅ [HDFS] 发现模型文件：{model_filename}，正在下载...")
                    try:
                        import tempfile
                        # 创建临时文件
                        temp_model = tempfile.NamedTemporaryFile(delete=False, suffix=".joblib")
                        temp_feat = tempfile.NamedTemporaryFile(delete=False, suffix=".joblib")
                        temp_model.close()
                        temp_feat.close()
                        
                        # 下载
                        hdfs_client.download(hdfs_model_path, temp_model.name, overwrite=True)
                        hdfs_client.download(hdfs_feat_path, temp_feat.name, overwrite=True)
                        
                        chosen_model_path = temp_model.name
                        chosen_feat_path = temp_feat.name
                        temp_files_to_clean.extend([temp_model.name, temp_feat.name])
                        print(f"   📥 下载成功 -> {temp_model.name}")
                    except Exception as e:
                        print(f"   ⚠️ [HDFS] 下载失败：{e}，将尝试回退到本地文件...")
                        chosen_model_path = "" # 重置，触发本地回退
                else:
                    print(f"   ℹ️ [HDFS] 未在 HDFS 找到 {model_filename}，尝试查找本地文件...")
            
            # --- 策略 B: 回退到本地 ---
            if not chosen_model_path:
                if os.path.exists(local_model_path) and os.path.exists(local_feat_path):
                    print(f"✅ [LOCAL] 找到本地模型文件：{local_model_path}")
                    chosen_model_path = local_model_path
                    chosen_feat_path = local_feat_path
                else:
                    # 彻底失败
                    err_msg = f"❌ 模型文件丢失：{model_filename} (HDFS和本地均未找到)"
                    print(err_msg)
                    raise FileNotFoundError(err_msg)
            
            final_model_paths[model_name] = chosen_model_path
            final_feat_paths[model_name] = chosen_feat_path

        # 3. 处理 Metrics 数据格式
        raw_metrics = result.get("model_metrics", [])
        model_metrics_dict = {}
        if isinstance(raw_metrics, list):
            for item in raw_metrics:
                m_name = item.get("模型名称") or item.get("model_name") or item.get("name")
                if m_name:
                    model_metrics_dict[m_name] = item
        elif isinstance(raw_metrics, dict):
            model_metrics_dict = raw_metrics
        
        model_metrics = model_metrics_dict
        all_models_info = result.get("all_models", {})

        # 4. 遍历执行空间预测
        all_spatial_results = {}
        for model_name, model_info in all_models_info.items():
            try:
                m_path = final_model_paths.get(model_name)
                f_path = final_feat_paths.get(model_name)
                
                if not m_path or not f_path:
                    print(f"⚠️ 模型 {model_name} 路径准备失败，跳过")
                    continue
                
                # 双重检查文件存在性
                if not os.path.exists(m_path):
                    raise FileNotFoundError(f"本地缓存模型文件不存在：{m_path}")
                if not os.path.exists(f_path):
                    raise FileNotFoundError(f"本地缓存特征文件不存在：{f_path}")

                print(f"🚀 执行 {model_name} 空间预测...")
                
                spatial_result = generate_spatial_biomass_map(
                    model_path=m_path,
                    feature_list_path=f_path,
                    timestamp=timestamp,
                    model_name=model_name
                )
                all_spatial_results[model_name] = spatial_result
                
            except Exception as e:
                print(f"⚠️ 模型 {model_name} 空间预测失败：{str(e)}")
                import traceback
                traceback.print_exc()
                all_spatial_results[model_name] = {"error": str(e), "status": "failed"}
        
        # 5. 筛选最优模型并合并结果
        valid_models = {}
        for name, metrics in model_metrics.items():
            if name in all_spatial_results and "error" not in all_spatial_results[name]:
                r2_score = metrics.get("R²") or metrics.get("r2") or metrics.get("R2") or 0
                valid_models[name] = float(r2_score)
        
        if not valid_models:
            error_msg = f"❌ 无有效空间预测结果的模型"
            result["spatial_prediction_error"] = error_msg
            result["all_models_spatial_results"] = all_spatial_results
            result["best_model_name"] = ""
            result["best_model_spatial_result"] = {}
            result["best_geojson_path"] = ""
            # 这里不 raise，而是保存结果后返回，让前端看到错误信息
            save_task_result(task_id, result)
            return 

        best_model_name = max(valid_models.keys(), key=lambda x: valid_models[x])
        best_model_result = all_spatial_results[best_model_name]
        best_geojson_path = best_model_result.get("geojson_path", "")
        
        result["all_models_spatial_results"] = all_spatial_results
        result["best_model_name"] = best_model_name
        result["best_model_spatial_result"] = best_model_result
        result["best_geojson_path"] = best_geojson_path  
        result["model_metrics"] = model_metrics
        result["spatial_prediction_status"] = "success"
        
        save_task_result(task_id, result)
        print(f"✅ 任务 {task_id} 全流程 (训练+空间预测) 执行完毕")

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ 任务 {task_id} 空间预测发生严重异常：{str(e)}")
        print(error_trace)
        result["status"] = "failed"
        result["error"] = str(e)
        result["spatial_prediction_error"] = str(e)
        save_task_result(task_id, result)
        # 这里选择不再 raise，避免背景任务反复重试导致日志爆炸，状态已标记为 failed
    
    finally:
        # 🔥 清理临时下载的文件
        for f_path in temp_files_to_clean:
            if os.path.exists(f_path):
                try:
                    os.remove(f_path)
                    print(f"🗑️ 清理临时文件：{f_path}")
                except Exception:
                    pass

# ===================== API 接口 =====================
@router.post("/run", response_model=Dict[str, str])
async def run_algorithm(
    task: TaskCreate,
    background_tasks: BackgroundTasks
):
    """
    提交算法任务：严格透传前端时间戳
    """
    try:

        timestamp = task.params.dict().get("timestamp")
        if not timestamp:
            raise HTTPException(status_code=400, detail="前端未传入 timestamp 参数")
        
        # 1. 创建任务
        task_id = create_task(task.algorithm, task.params.dict())
        
        # 2. 保存元数据（包含前端透传的时间戳）
        task_metadata = {
            "task_id": task_id,
            "algorithm": task.algorithm,
            "params": task.params.dict(),
            "status": "pending",
            "create_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "result_path": "",
            "storage_type": "HDFS" if HDFS_ENABLED else "LOCAL",
            "timestamp": task.params.dict().get("timestamp")
        }
        save_task_metadata(task_id, task_metadata)
        
        # 3. 后台执行算法
        def run_algorithm_with_fallback(task_id: str):
            result = run_algorithm_task(task_id)
            if result and "status" in result and result["status"] == "success":
                if task.algorithm == "biomass_prediction":
                    run_spatial_prediction_after_ml(task_id, result)
                else:
                    save_task_result(task_id, result)
            return result
        
        background_tasks.add_task(run_algorithm_with_fallback, task_id)
        
        msg = "任务已提交，优先存储到HDFS集群" if HDFS_ENABLED else "任务已提交，使用本地存储模式"
        return {"task_id": task_id, "message": msg}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"任务提交失败：{str(e)}")

@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status_api(task_id: str):
    """
    查询任务状态：优先HDFS，失败则本地
    【核心修复】将 HDFS 物理路径转换为前端可访问的 API 路径
    """
    try:
        task_info = get_task_status(task_id)
        if not task_info:
            raise HTTPException(status_code=404, detail=f"任务ID不存在：{task_id}")
        
        metadata_filename = f"{task_id}_metadata.json"
        task_info["storage_type"] = "UNKNOWN"
        task_info["result_path"] = ""
        task_info["best_model_spatial_result"] = {}
        task_info["all_models_spatial_results"] = {}
        task_info["best_model_name"] = ""
        task_info["best_geojson_path"] = "" 
        
        # --- 辅助函数：路径转换逻辑 ---
        def convert_forest_path_to_api(raw_path: str) -> str:
            if not raw_path:
                return ""
            
            # 情况 A: HDFS 绝对路径 (例如 hdfs://localhost:9000/forest/results/20260323/file.geojson)
            if raw_path.startswith("hdfs://"):
                # 去掉协议头，只保留 /forest/...
                hdfs_internal_path = raw_path.split(":", 2)[-1] # 去掉 hdfs://host:port
                
                # 如果路径以 /forest/results 开头
                if hdfs_internal_path.startswith(f"{HDFS_RESULTS_ROOT}"):
                    # 提取 /forest/results 后面的部分，例如 20260323/file.geojson
                    relative_part = hdfs_internal_path.replace(f"{HDFS_RESULTS_ROOT}", "").lstrip("/")
                    # 拼接成前端 API 路径
                    # 假设 file.py 中 /api/file/biomass_results 映射到了 HDFS_RESULTS_ROOT
                    return f"/api/file/biomass_results/{relative_part}"
                
                # 如果路径以 /forest/tasks 开头 (元数据等)
                elif hdfs_internal_path.startswith(f"{HDFS_TASK_ROOT}"):
                     # 任务元数据通常不需要直接给前端访问，返回空或特定处理
                     return ""
                
                # 其他 /forest 下的文件
                elif hdfs_internal_path.startswith(HDFS_ROOT):
                    relative_part = hdfs_internal_path.replace(HDFS_ROOT, "").lstrip("/")
                    return f"/api/file/forest/{relative_part}"
                    
                else:
                    print(f"⚠️ 未知的 HDFS 路径前缀：{hdfs_internal_path}")
                    return ""

            # 情况 B: 本地绝对路径 (例如 /data/biomass_results/...)
            elif raw_path.startswith("/"):
                base_dir = settings.BASE_DATA_DIR # 例如 /data
                if raw_path.startswith(base_dir):
                    relative = raw_path.replace(base_dir, "").lstrip("/")
                    return f"/api/file/{relative}"
                else:
                    return f"/api/file{raw_path}"
            
            # 情况 C: 已经是 API 路径
            return raw_path

        # --- 主逻辑 ---
        if HDFS_ENABLED and hdfs_client:
            hdfs_metadata_path = f"{HDFS_TASK_ROOT}/{metadata_filename}"
            if hdfs_client.status(hdfs_metadata_path, strict=False):
                with hdfs_client.read(hdfs_metadata_path) as reader:
                        # reader.read() 拿到二进制流，必须 .decode('utf-8') 转为字符串
                        metadata_str = reader.read().decode('utf-8')
                metadata = json.loads(metadata_str)
                task_info["result_path"] = metadata.get("result_path", "")
                task_info["storage_type"] = "HDFS"

                if metadata.get("result_path"):
                    try:
                        result_content = hdfs_client.read(metadata["result_path"], encoding='utf-8')
                        result_data = json.loads(result_content)
                        
                        task_info["best_model_spatial_result"] = result_data.get("best_model_spatial_result", {})
                        task_info["all_models_spatial_results"] = result_data.get("all_models_spatial_results", {})
                        task_info["best_model_name"] = result_data.get("best_model_name", "")
                        
                        # 🔥🔥🔥 核心修复：转换 GeoJSON 路径 🔥🔥🔥
                        raw_geojson = result_data.get("best_geojson_path", "")
                        task_info["best_geojson_path"] = convert_forest_path_to_api(raw_geojson)
                        
                        # 同时也转换 all_models_spatial_results 中的路径 (如果需要)
                        # 遍历并转换其中可能的路径字段...
                        
                    except Exception as e:
                        print(f"⚠️ 读取或解析 HDFS 结果文件失败：{str(e)}")
                        import traceback
                        traceback.print_exc()
                return task_info
        
        # 本地逻辑 (保持不变)
        local_metadata_path = os.path.join(LOCAL_TASK_ROOT, metadata_filename)
        if os.path.exists(local_metadata_path):
            with open(local_metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                task_info["result_path"] = metadata.get("result_path", "")
                task_info["storage_type"] = "LOCAL"

                if metadata.get("result_path") and os.path.exists(metadata["result_path"]):
                    try:
                        with open(metadata["result_path"], 'r', encoding='utf-8') as f:
                            result_data = json.load(f)
                            task_info["best_model_spatial_result"] = result_data.get("best_model_spatial_result", {})
                            task_info["all_models_spatial_results"] = result_data.get("all_models_spatial_results", {})
                            task_info["best_model_name"] = result_data.get("best_model", result_data.get("best_model_name", ""))
                            
                            # 🔥 本地路径也要转换 (虽然通常已经是绝对路径，但为了统一)
                            raw_geojson = result_data.get("best_geojson_path", "")
                            task_info["best_geojson_path"] = convert_forest_path_to_api(raw_geojson)
                    except Exception:
                        pass
        
        return task_info
    
    except HTTPException as e:
        raise e
    except Exception as e:
        import traceback
        print(f"❌ 查询任务状态严重异常：{str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"查询任务状态失败：{str(e)}")

@router.get("/list", response_model=Dict[str, Any])
async def list_all_tasks():
    """
    列出所有任务
    """
    try:
        tasks = {}
        
        if HDFS_ENABLED and hdfs_client:
            try:
                hdfs_files = hdfs_client.list(HDFS_TASK_ROOT)
                metadata_files = [f for f in hdfs_files if f.endswith("_metadata.json")]
                for meta_file in metadata_files:
                    task_id = meta_file.replace("_metadata.json", "")
                    meta_path = f"{HDFS_TASK_ROOT}/{meta_file}"
                    metadata = json.loads(hdfs_client.read(meta_path, encoding='utf-8'))
                    tasks[task_id] = {**metadata, "storage_type": "HDFS"}
            except Exception as e:
                print(f"⚠️ 读取 HDFS 任务列表失败，降级到本地：{str(e)}")
        
        local_files = os.listdir(LOCAL_TASK_ROOT) if os.path.exists(LOCAL_TASK_ROOT) else []
        local_meta_files = [f for f in local_files if f.endswith("_metadata.json")]
        for meta_file in local_meta_files:
            task_id = meta_file.replace("_metadata.json", "")
            if task_id not in tasks:
                local_meta_path = os.path.join(LOCAL_TASK_ROOT, meta_file)
                with open(local_meta_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    tasks[task_id] = {**metadata, "storage_type": "LOCAL"}
        
        return {
            "total": len(tasks),
            "tasks": tasks,
            "storage_info": {
                "hdfs_enabled": HDFS_ENABLED,
                "hdfs_path": HDFS_TASK_ROOT if HDFS_ENABLED else "",
                "local_path": LOCAL_TASK_ROOT
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务列表失败：{str(e)}")

@router.delete("/{task_id}", response_model=Dict[str, str])
async def delete_task(task_id: str):
    """
    删除任务
    """
    try:
        deleted_files = []
        
        if HDFS_ENABLED and hdfs_client:
            metadata_path = f"{HDFS_TASK_ROOT}/{task_id}_metadata.json"
            result_path = f"{HDFS_TASK_ROOT}/{task_id}_result.json"
            
            if hdfs_client.status(metadata_path, strict=False):
                hdfs_client.delete(metadata_path)
                deleted_files.append(f"HDFS: {metadata_path}")
            
            if hdfs_client.status(result_path, strict=False):
                hdfs_client.delete(result_path)
                deleted_files.append(f"HDFS: {result_path}")
        
        local_metadata_path = os.path.join(LOCAL_TASK_ROOT, f"{task_id}_metadata.json")
        local_result_path = os.path.join(LOCAL_TASK_ROOT, f"{task_id}_result.json")
        
        if os.path.exists(local_metadata_path):
            os.remove(local_metadata_path)
            deleted_files.append(f"LOCAL: {local_metadata_path}")
        
        if os.path.exists(local_result_path):
            os.remove(local_result_path)
            deleted_files.append(f"LOCAL: {local_result_path}")
        
        if not deleted_files:
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
        
        return {
            "message": f"任务 {task_id} 已删除",
            "deleted_files": deleted_files
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除任务失败：{str(e)}")
    
@router.post("/chat")
async def chat_endpoint(payload: ChatMessage):
    """
    AI 聊天接口
    前端 POST 请求到这里
    """
    # 生成器包装成流式响应
    return StreamingResponse(
        get_ai_response(payload.message, payload.history),
        media_type="text/plain"
    )