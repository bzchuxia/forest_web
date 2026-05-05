# task_service.py 中关键修改：使用枚举值替代硬编码字符串
import uuid
import time
import tempfile
import shutil
from typing import Dict, Any, Optional, List
from app.ml.pipelines import run_biomass_prediction
from asyncio.exceptions import CancelledError
from app.core.config import settings
import numpy as np
import json
import os
import re
# 导入 TaskStatus 枚举
from app.schemas import TaskStatus

# ===================== 导入HDFS配置 =====================
from app.core.hdfs_config import HDFS_ENABLED, hdfs_client, HDFS_RESULTS_ROOT, HDFS_HOST, WEBHDFS_PORT,HDFS_ROOT

# ===================== 全局配置 =====================
# 内存存储任务状态
task_storage: Dict[str, Dict[str, Any]] = {}
task_temp_dirs: Dict[str, str] = {}

# 时间戳格式校验正则（仅支持 YYYYMMDDHHMMSS 或 YYYYMMDD_HHMMSS）
TIMESTAMP_PATTERN = re.compile(r'^\d{8}_?\d{6}$')

# =====================过滤不可序列化的对象 =====================
def filter_serializable(data):
    """
    递归过滤数据，只保留可 JSON 序列化的类型
    - 自动删除：model、scaler、boruta、explainer 等不可序列化对象
    - 自动转换：numpy.ndarray → list，numpy.float → float，numpy.int → int
    - 其他类型：转为字符串兜底
    """
    if isinstance(data, dict):
        return {k: filter_serializable(v) for k, v in data.items() 
                if k not in ["model", "scaler", "boruta", "explainer", "base_models", "meta_model"]}
    elif isinstance(data, (np.ndarray, list)):
        return [filter_serializable(i) for i in data] if isinstance(data, list) else data.tolist()
    elif isinstance(data, (np.floating, np.integer)):
        return float(data) if isinstance(data, np.floating) else int(data)
    elif isinstance(data, (int, float, str, bool, type(None))):
        return data
    else:
        # 兜底：其他类型转为字符串（避免序列化报错）
        return str(data)

# ===================== 核心工具函数 =====================
def validate_timestamp(timestamp: str) -> str:
    """
    严格校验并格式化时间戳：
    - 必须为字符串类型
    - 格式为 14位数字（YYYYMMDDHHMMSS）或 YYYYMMDD_HHMMSS
    - 返回统一格式：YYYYMMDD_HHMMSS
    """
    if not isinstance(timestamp, str):
        raise ValueError(f"时间戳必须为字符串类型（当前类型：{type(timestamp)}）")
    
    # 去除下划线并校验长度和数字格式
    clean_ts = timestamp.replace("_", "")
    if len(clean_ts) != 14 or not clean_ts.isdigit():
        raise ValueError(
            f"时间戳格式错误！必须为14位数字（YYYYMMDDHHMMSS），当前值：{timestamp}"
        )
    
    # 统一格式为 YYYYMMDD_HHMMSS（便于文件命名）
    return f"{clean_ts[:8]}_{clean_ts[8:]}"

def resolve_file_path(file_path: str, file_type: str = "data", timestamp: str = "") -> str:
    """
    解析文件路径：优先HDFS，否则本地
    - 支持在输出路径中嵌入时间戳（保证文件唯一性）
    """
    # 1. HDFS路径优先
    if HDFS_ENABLED and hdfs_client and file_path.startswith("/"):
        try:
            if hdfs_client.status(file_path, strict=False):
                return file_path
        except Exception as e:
            print(f"⚠️ HDFS路径解析失败，降级到本地：{str(e)}")
    
    # 2. dataset:// 内置数据集路径
    if file_path.startswith("dataset://"):
        dataset_id = file_path.replace("dataset://", "")
        
        # HDFS数据集路径
        if HDFS_ENABLED and hdfs_client:
            hdfs_dataset_path = f"{HDFS_ROOT}/datasets/{dataset_id}.xlsx"
            if hdfs_client.status(hdfs_dataset_path, strict=False):
                return hdfs_dataset_path
        
        # 本地数据集映射
        dataset_mapping = {
            "maoershan_2nd_survey": os.path.join(settings.BASE_DATA_DIR, "maoershan_2.xlsx"),
            "default": os.path.join(settings.BASE_DATA_DIR, "111.xlsx")
        }
        if dataset_id in dataset_mapping:
            return dataset_mapping[dataset_id]
        else:
            local_dataset_path = os.path.join(settings.BASE_DATA_DIR, "datasets", f"{dataset_id}.xlsx")
            if os.path.exists(local_dataset_path):
                return local_dataset_path
            raise ValueError(f"内置数据集 {dataset_id} 不存在！")
    
    # 3. 输出目录：自动嵌入时间戳（保证唯一性）
    if file_type == "output":
        # HDFS输出路径
        if HDFS_ENABLED and hdfs_client and file_path.startswith(f"{HDFS_ROOT}/"):
            output_path = f"{file_path}_{timestamp}" if timestamp else file_path
            # 确保HDFS目录存在
            if not hdfs_client.status(os.path.dirname(output_path), strict=False):
                hdfs_client.makedirs(os.path.dirname(output_path))
            return output_path
        
        # 本地输出路径
        if not os.path.isabs(file_path):
            file_path = os.path.join(settings.BASE_DATA_DIR, file_path)
        
        # 嵌入时间戳（避免文件覆盖）
        if timestamp:
            file_path = f"{file_path}_{timestamp}"
        
        # 确保本地目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        return file_path
    
    # 4. 本地绝对路径直接返回
    return file_path

def cleanup_task_temp_files(task_id: str):
    """
    安全清理任务临时文件：
    - 清理本地临时目录
    - 清理HDFS临时文件（如果存在）
    """
    # 清理本地临时目录
    if task_id in task_temp_dirs:
        temp_dir = task_temp_dirs[task_id]
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                print(f"🗑️ 清理任务 {task_id} 本地临时目录：{temp_dir}")
        except Exception as e:
            print(f"⚠️ 清理任务 {task_id} 临时目录失败：{str(e)}")
        finally:
            del task_temp_dirs[task_id]
    
    # 清理HDFS临时文件（如果有）
    if HDFS_ENABLED and hdfs_client:
        hdfs_temp_path = f"{HDFS_ROOT}/temp/task_{task_id}"
        try:
            if hdfs_client.status(hdfs_temp_path, strict=False):
                hdfs_client.delete(hdfs_temp_path, recursive=True)
                print(f"🗑️ 清理任务 {task_id} HDFS临时文件：{hdfs_temp_path}")
        except Exception as e:
            print(f"⚠️ 清理任务 {task_id} HDFS临时文件失败：{str(e)}")

# ===================== 核心业务函数 =====================
def create_task(algorithm: str, params: Dict[str, Any]) -> str:
    """
    创建任务：
    1. 严格校验前端透传的时间戳（无则抛错）
    2. 解析并格式化输入输出路径
    3. 创建临时目录（HDFS/本地）
    4. 强制保留前端时间戳到任务参数
    """
    temp_dir = None
    try:
        print("🔥 create_task 收到的 params：", params)
        # 1. 严格校验时间戳（核心：无时间戳不创建任务）
        timestamp = params.get("timestamp")
        if not timestamp:
            raise ValueError("❌ 前端未传入有效时间戳，任务创建失败！")
        
        # 格式化时间戳（统一格式）
        formatted_ts = validate_timestamp(timestamp)
        print(f"📌 任务创建 - 前端时间戳：{timestamp} → 格式化后：{formatted_ts}")
        
        # 2. 生成唯一任务ID
        task_id = str(uuid.uuid4())
        
        # 3. 校验必要参数
        input_path = params.get("input_path")
        if not input_path:
            raise ValueError("❌ 前端未传入input_path参数，任务创建失败！")
        
        # 4. 解析输入输出路径（输出路径嵌入时间戳）
        processed_input_path = resolve_file_path(input_path, "data")
        output_dir = params.get("output_dir", settings.DEFAULT_OUTPUT_DIR)
        processed_output_dir = resolve_file_path(output_dir, "output", formatted_ts)
        
        # 5. 创建临时目录（仅HDFS模式需要）
        temp_dir = None
        if HDFS_ENABLED and hdfs_client:
            # 本地临时目录（用于HDFS文件中转）
            temp_dir = tempfile.mkdtemp(prefix=f"task_{task_id}_")
            task_temp_dirs[task_id] = temp_dir
            print(f"📌 为任务 {task_id} 创建本地临时目录：{temp_dir}")
            
            # HDFS临时目录（提前创建）
            hdfs_temp_dir = f"{HDFS_ROOT}/temp/task_{task_id}"
            if not hdfs_client.status(hdfs_temp_dir, strict=False):
                hdfs_client.makedirs(hdfs_temp_dir)
        
        # 6. 组装最终参数（强制保留格式化后的时间戳）
        processed_params = {
            **params,
            "input_path": processed_input_path,
            "output_dir": processed_output_dir,
            "temp_dir": temp_dir,
            "hdfs_enabled": HDFS_ENABLED,
            "timestamp": formatted_ts,  # 强制覆盖为格式化后的时间戳
            "original_timestamp": timestamp  # 保留原始输入（便于排查）
        }
        
        # 7. 存储任务信息（使用枚举值）
        task_storage[task_id] = {
            "task_id": task_id,
            "algorithm": algorithm,
            "params": processed_params,
            "status": TaskStatus.RUNNING.value,  # 使用枚举值
            "result": None,
            "error": None,
            "create_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "update_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "hdfs_enabled": HDFS_ENABLED,
            "frontend_timestamp": formatted_ts,  # 存储格式化后的前端时间戳
            "original_frontend_timestamp": timestamp  # 保留原始时间戳
        }
        
        print(f"✅ 任务 {task_id} 创建成功，算法：{algorithm}，时间戳：{formatted_ts}")
        return task_id
    
    except ValueError as ve:
        # 参数/时间戳校验失败
        print(f"❌ 任务创建失败：{str(ve)}")
        raise ve
    except Exception as e:
        # 其他系统异常
        error_msg = f"❌ 任务创建系统异常：{str(e)}"
        print(error_msg)
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        raise Exception(error_msg)

def run_algorithm_task(task_id: str) -> Dict[str, Any]:
    """
    执行算法任务：
    1. 强制透传格式化后的时间戳到算法管道
    2. 捕获所有异常并更新任务状态
    3. 【核心新增】训练成功后自动上传模型文件到 HDFS
    """
    # 🔥 初始化默认结果
    result = {
        "status": TaskStatus.FAILED.value,
        "error": "任务未执行",
        "timestamp": "",
        "task_id": task_id
    }

    try:
        # 1. 校验任务存在性
        if task_id not in task_storage:
            error_msg = f"❌ 任务 {task_id} 不存在，执行失败"
            print(error_msg)
            result["error"] = error_msg
            return result
        
        task = task_storage[task_id]
        algorithm = task["algorithm"]
        params = task["params"]
        
        # 2. 校验时间戳
        timestamp = params.get("timestamp")
        if not timestamp:
            raise ValueError(f"❌ 任务 {task_id} 执行时丢失时间戳参数")
        validate_timestamp(timestamp)
        
        print(f"🚀 开始执行任务 {task_id}，算法：{algorithm}，时间戳：{timestamp}")
        
        processed_params = prepare_hdfs_inputs(task_id, params)

        # 3. 执行对应算法
        if algorithm == "biomass_prediction":
            # 运行核心预测
            result = run_biomass_prediction(processed_params)
            
            if result.get("status") == "success":
                timestamp = processed_params.get("timestamp", "")
                
                # ✅ 修复：保持 model_metrics 为列表格式
                raw_metrics = result.get("model_metrics", [])
                if isinstance(raw_metrics, list):
                    for item in raw_metrics:
                        if "feature_count" not in item and "使用的特征数" not in item:
                            item["feature_count"] = 0 
                            item["使用的特征数"] = 0
                    result["model_metrics"] = raw_metrics
                else:
                    result["model_metrics"] = []

                # 数据序列化过滤
                result = filter_serializable(result)
                
                if not isinstance(result, dict):
                    result = {
                        "status": TaskStatus.FAILED.value,
                        "error": "算法返回非字典格式结果",
                        "timestamp": timestamp,
                        "task_id": task_id
                    }
                else:
                    result["timestamp"] = timestamp
                    result["task_id"] = task_id

                # 🔥🔥🔥【核心新增】自动上传模型到 HDFS🔥🔥🔥
                if HDFS_ENABLED and hdfs_client:
                    hdfs_base_dir = f"{HDFS_RESULTS_ROOT}/{timestamp}"
                    try:
                        # 1. 创建 HDFS 目录
                        if not hdfs_client.status(hdfs_base_dir, strict=False):
                            hdfs_client.makedirs(hdfs_base_dir)
                            print(f"📁 [HDFS] 创建模型目录：{hdfs_base_dir}")
                        
                        all_models = result.get("all_models", {})
                        for model_name, model_info in all_models.items():
                            local_model_path = model_info.get("model_path")
                            local_feat_path = model_info.get("feature_list_path")
                            
                            model_filename = f"{model_name}_model_{timestamp}.joblib"
                            feat_filename = f"{model_name}_feature_list_{timestamp}.joblib"
                            
                            # 上传模型
                            if local_model_path and os.path.exists(local_model_path):
                                hdfs_model_path = f"{hdfs_base_dir}/{model_filename}"
                                hdfs_client.upload(hdfs_model_path, local_model_path, overwrite=True)
                                print(f"⬆️ [HDFS] 上传模型成功：{model_filename}")
                                # 更新路径指向 HDFS (方便后续步骤直接使用)
                                model_info["hdfs_model_path"] = hdfs_model_path
                                model_info["model_path"] = f"hdfs://{HDFS_HOST}:{WEBHDFS_PORT}{hdfs_model_path}"
                            
                            # 上传特征
                            if local_feat_path and os.path.exists(local_feat_path):
                                hdfs_feat_path = f"{hdfs_base_dir}/{feat_filename}"
                                hdfs_client.upload(hdfs_feat_path, local_feat_path, overwrite=True)
                                print(f"⬆️ [HDFS] 上传特征成功：{feat_filename}")
                                model_info["hdfs_feat_path"] = hdfs_feat_path
                                model_info["feature_list_path"] = f"hdfs://{HDFS_HOST}:{WEBHDFS_PORT}{hdfs_feat_path}"
                                
                    except Exception as upload_err:
                        print(f"❌ [HDFS] 上传模型失败：{str(upload_err)}")
                        print("⚠️ 系统将继续运行，空间预测阶段将尝试回退到本地文件。")
            
            elif result.get("status") != "success":
                 # 如果算法内部返回失败，保留错误信息
                 pass

        elif algorithm == "single_target_extraction":
            result = {
                "status": TaskStatus.SUCCESS.value,
                "timestamp": timestamp,
                "task_id": task_id,
                "message": "单目标提取任务执行完成"
            }
        
        else:
            raise ValueError(f"❌ 未知算法类型：{algorithm}")
        
        # 4. 更新任务状态
        task["status"] = TaskStatus.SUCCESS.value if (result and result.get("status") == "success") else TaskStatus.FAILED.value
        task["result"] = result
        task["error"] = None if task["status"] == TaskStatus.SUCCESS.value else result.get("error")
        task["update_time"] = time.strftime("%Y-%m-%d %H:%M:%S")

        # 本地保存一份结果备份 (可选，用于调试)
        try:
            task_dir = os.path.join(settings.BASE_DATA_DIR, "task", timestamp)
            os.makedirs(task_dir, exist_ok=True)
            task_result_path = os.path.join(task_dir, f"{task_id}_result.json")
            with open(task_result_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"✅ 任务结果本地备份：{task_result_path}")
        except Exception as e:
            print(f"⚠️ 任务结果本地备份失败：{e}")
        
        print(f"✅ 任务 {task_id} 执行完成，状态：{task['status']}")
        return result
    
    except ValueError as ve:
        error_msg = str(ve)
        task = task_storage.get(task_id, {})
        if task:
            task["status"] = TaskStatus.FAILED.value
            task["error"] = error_msg
            task["update_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"❌ 任务 {task_id} 业务错误：{error_msg}")
        result["error"] = error_msg
        result["timestamp"] = params.get("timestamp", "") if 'params' in locals() else ""
        return result
    
    except Exception as e:
        error_msg = f"系统执行异常：{str(e)}"
        task = task_storage.get(task_id, {})
        if task:
            task["status"] = TaskStatus.FAILED.value
            task["error"] = error_msg
            task["update_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"❌ 任务 {task_id} 系统异常：{error_msg}")
        import traceback
        traceback.print_exc()
        result["error"] = error_msg
        result["timestamp"] = params.get("timestamp", "") if 'params' in locals() else ""
        return result
    
    finally:
        # 清理临时输入文件
        if 'params' in locals():
            temp_cleanup_paths = params.get("_hdfs_cleanup_paths", [])
            for path in temp_cleanup_paths:
                if os.path.exists(path):
                    try:
                        shutil.rmtree(path)
                        print(f"🗑️ 清理临时输入目录：{path}")
                    except: pass
        cleanup_task_temp_files(task_id)

def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """
    查询任务状态：确保返回格式与前端TaskResult完全对齐
    """
    try:
        task = task_storage.get(task_id)
        if not task:
            return {
                "task_id": task_id,
                "status": "",
                "error": "任务记录不存在",
                "create_time": "",
                "update_time": "",
                "hdfs_enabled": HDFS_ENABLED,
                "timestamp": "",
                "frontend_timestamp": "",
                "feature_count": 0,
                "train_samples": 0,
                "test_samples": 0,
                "best_model": "",
                "best_model_name": "",
                "model_metrics": [],
                "output_files": {},
                "statistics": {}
            }
        
        # 基础返回信息
        resp = {
            "task_id": task.get("task_id", task_id),
            "algorithm": task.get("algorithm", ""),
            "status": task.get("status", ""),
            "error": task.get("error"),
            "create_time": task.get("create_time", ""),
            "update_time": task.get("update_time", ""),
            "hdfs_enabled": task.get("hdfs_enabled", HDFS_ENABLED),
            "timestamp": task.get("frontend_timestamp", ""),
            "original_timestamp": task.get("original_frontend_timestamp", ""),
            "storage_type": "HDFS" if HDFS_ENABLED else "LOCAL",
            "feature_count": 0,
            "train_samples": 0,
            "test_samples": 0,
            "best_model": "",
            "best_model_name": "",
            "model_metrics": [],
            "output_files": {},
            "statistics": {}
        }

        # 补充成功任务的结果
        if task.get("status") == TaskStatus.SUCCESS.value and task.get("result"):
            result = task["result"]
            model_metrics = result.get("model_metrics", [])
            if isinstance(model_metrics, dict):
                # 兼容旧格式，转成数组
                model_metrics = [
                    {
                        "模型名称": k,
                        "R²": v.get('r2', 0),
                        "RMSE": v.get('rmse', 0),
                        "MAE": v.get('mae', 0),
                        "训练时间(s)": v.get('train_time', 0)
                    } for k, v in model_metrics.items()
                ]
            resp.update({
                "feature_count": result.get("feature_count", 0),
                "train_samples": result.get("train_samples", 0),
                "test_samples": result.get("test_samples", 0),
                "best_model": result.get("best_model_name", ""),
                "best_model_name": result.get("best_model_name", ""),
                "model_metrics": model_metrics,
                "output_files": result.get("output_files", {}),
                "statistics": result.get("statistics", {}),
                "timestamp": result.get("timestamp", resp["timestamp"])
            })

        return resp

    except Exception as e:
        return {
            "task_id": task_id,
            "status": "",
            "error": f"查询系统内部异常: {str(e)}",
            "create_time": "",
            "update_time": "",
            "hdfs_enabled": HDFS_ENABLED,
            "timestamp": "",
            "frontend_timestamp": "",
            "feature_count": 0,
            "train_samples": 0,
            "test_samples": 0,
            "best_model": "",
            "model_metrics": [],
            "output_files": {},
            "statistics": {}
        }

def cancel_task(task_id: str) -> bool:
    """
    取消任务：
    1. 更新任务状态为已取消
    2. 清理临时文件
    3. 返回取消结果
    """
    if task_id not in task_storage:
        cleanup_task_temp_files(task_id)
        print(f"⚠️ 任务 {task_id} 不存在，无需取消")
        return False
    
    task = task_storage[task_id]
    if task["status"] in [TaskStatus.RUNNING.value, TaskStatus.PENDING.value]:
        task["status"] = TaskStatus.CANCELLED.value  # 使用枚举值
        task["error"] = "任务已被用户取消"
        task["update_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"🛑 任务 {task_id} 已取消")
    
    cleanup_task_temp_files(task_id)
    return True

def list_tasks(status: Optional[str] = None, algorithm: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    列出任务：
    1. 支持按状态/算法筛选
    2. 返回包含时间戳的简化信息
    3. 按创建时间倒序排列
    """
    tasks = []
    for task_id, task in task_storage.items():
        # 状态筛选
        if status and task["status"] != status:
            continue
        # 算法筛选
        if algorithm and task["algorithm"] != algorithm:
            continue
        
        tasks.append({
            "task_id": task["task_id"],
            "algorithm": task["algorithm"],
            "status": task["status"],
            "create_time": task["create_time"],
            "update_time": task.get("update_time", ""),
            "hdfs_enabled": task.get("hdfs_enabled", HDFS_ENABLED),
            "timestamp": task.get("frontend_timestamp", ""),
            "original_timestamp": task.get("original_frontend_timestamp", ""),
            "storage_type": "HDFS" if HDFS_ENABLED else "LOCAL"
        })
    
    # 按创建时间倒序排列
    tasks.sort(key=lambda x: x["create_time"], reverse=True)
    return tasks

def cleanup_completed_tasks() -> Dict[str, Any]:
    """
    清理已完成任务：
    1. 清理成功/失败/取消的任务
    2. 清理关联的临时文件
    3. 返回清理统计信息
    """
    completed_status = [TaskStatus.SUCCESS.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value]
    cleaned_count = 0
    cleaned_task_ids = []
    
    for task_id in list(task_storage.keys()):
        task = task_storage[task_id]
        if task["status"] in completed_status:
            # 清理临时文件
            cleanup_task_temp_files(task_id)
            # 删除任务记录
            del task_storage[task_id]
            cleaned_count += 1
            cleaned_task_ids.append(task_id)
    
    print(f"🧹 清理完成：共清理 {cleaned_count} 个任务，剩余 {len(task_storage)} 个任务")
    return {
        "status": TaskStatus.SUCCESS.value,
        "cleaned_tasks": cleaned_count,
        "cleaned_task_ids": cleaned_task_ids,
        "remaining_tasks": len(task_storage)
    }

def delete_task(task_id: str) -> bool:
    """
    强制删除任务：
    1. 删除任务记录
    2. 清理临时文件
    3. 无论任务状态如何都删除
    """
    if task_id not in task_storage:
        print(f"⚠️ 任务 {task_id} 不存在，无需删除")
        return False
    
    # 清理临时文件
    cleanup_task_temp_files(task_id)
    # 删除任务记录
    del task_storage[task_id]
    print(f"🗑️ 任务 {task_id} 已强制删除")
    return True

# ===================== 新增：HDFS 文件预处理与后处理工具 =====================
def prepare_hdfs_inputs(task_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    【核心修改】在执行算法前，将 HDFS 输入文件下载到本地临时目录
    返回更新后的 params (包含本地临时路径)
    """
    if not HDFS_ENABLED or not hdfs_client:
        return params
    
    temp_dir = tempfile.mkdtemp(prefix=f"task_input_{task_id}_")
    updated_params = params.copy()
    
    # 处理 input_path
    input_path = params.get("input_path", "")
    if input_path.startswith("/"): # 假设以 / 开头的是 HDFS 绝对路径
        try:
            hdfs_status = hdfs_client.status(input_path, strict=False)
            if hdfs_status:
                local_temp_file = os.path.join(temp_dir, os.path.basename(input_path))
                print(f"📥 [HDFS] 正在下载输入文件：{input_path} -> {local_temp_file}")
                hdfs_client.download(input_path, local_temp_file, overwrite=True)
                updated_params["input_path"] = local_temp_file
                updated_params["_hdfs_cleanup_paths"] = [temp_dir] # 标记待清理
                print(f"✅ [HDFS] 输入文件准备完成")
            else:
                print(f"⚠️ [HDFS] 输入文件不存在：{input_path}")
        except Exception as e:
            print(f"❌ [HDFS] 下载输入文件失败：{str(e)}")
            raise Exception(f"HDFS 输入文件下载失败：{str(e)}")
            
    return updated_params

def archive_hdfs_outputs(task_id: str, result: Dict[str, Any], timestamp: str) -> Dict[str, Any]:
    """
    【核心修改】算法执行成功后，将本地生成的结果上传到 HDFS
    并更新 result 中的路径为 HDFS 虚拟路径
    """
    if not HDFS_ENABLED or not hdfs_client:
        return result
    
    try:
        hdfs_result_root = f"{HDFS_ROOT}/results/{timestamp}"
        if not hdfs_client.status(hdfs_result_root, strict=False):
            hdfs_client.makedirs(hdfs_result_root)
        
        files_to_upload = []
        
        # 收集需要上传的文件路径 (从 result 的不同字段中提取)
        # 1. output_files 字典
        out_files = result.get("output_files", {})
        for key, path in out_files.items():
            if path and os.path.exists(path):
                files_to_upload.append((path, f"{hdfs_result_root}/{os.path.basename(path)}"))
        
        # 2. all_models 中的路径
        all_models = result.get("all_models", {})
        for model_info in all_models.values():
            if isinstance(model_info, dict):
                for k in ["model_path", "feature_list_path"]:
                    p = model_info.get(k)
                    if p and os.path.exists(p):
                        files_to_upload.append((p, f"{hdfs_result_root}/{os.path.basename(p)}"))
        
        # 执行上传并更新路径
        print(f"📤 [HDFS] 开始上传 {len(files_to_upload)} 个结果文件...")
        for local_path, hdfs_path in files_to_upload:
            try:
                hdfs_client.upload(hdfs_path, local_path, overwrite=True)
                print(f"  ✅ 上传：{os.path.basename(local_path)}")
                
                # 更新 result 中的路径为 HDFS 路径 (或者保持虚拟路径，取决于前端需求)
                # 这里我们保持虚拟路径逻辑不变，但确保文件已归档
                # 如果需要前端直接访问 HDFS，可在此处替换 result 中的路径字符串
                # 例如：result['output_files'][key] = hdfs_path 
                # 但通常前端通过 API 代理访问，所以只需确保文件存在即可
                filename = os.path.basename(local_path)
                virtual_path = f"/biomass_results/{timestamp}/{filename}"
                # 1. 如果是 output_files 里的
                for key, path in list(result.get("output_files", {}).items()):
                    if path == local_path:
                        result["output_files"][key] = virtual_path
                
                # 2. 如果是 all_models 里的 (需要深层查找替换)
                # 注意：这里可能需要更精细的逻辑来匹配哪个模型对应哪个文件
                # 简单做法：如果 local_path 包含 model_name，则替换
                for m_name, m_info in result.get("all_models", {}).items():
                    if isinstance(m_info, dict):
                        if m_info.get("model_path") == local_path:
                            m_info["model_path"] = virtual_path # 或者存 HDFS 绝对路径，让 task.py 去解析
                        if m_info.get("feature_list_path") == local_path:
                            m_info["feature_list_path"] = virtual_path
                
                # 3. 特殊处理 geojson_path (如果它是这次上传的文件之一)
                if result.get("best_geojson_path") == local_path:
                    result["best_geojson_path"] = virtual_path
                
            except Exception as e:
                print(f"  ⚠️ 上传失败 {local_path}: {str(e)}")
        
        print(f"✅ [HDFS] 结果归档完成")
        
    except Exception as e:
        print(f"❌ [HDFS] 结果归档异常，但不影响本地结果使用：{str(e)}")
        # 不抛出异常，避免导致整个任务失败，仅记录日志
        
    return result