from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Optional
import os
import io
import subprocess
import sys
from datetime import datetime
from hdfs import InsecureClient  # Hadoop HDFS 客户端

router = APIRouter()

# ===================== HDFS 核心配置 =====================
# 与 file.py/task.py 保持一致的 HDFS 配置
HDFS_URL = "http://localhost:9870"       # NameNode 地址
HDFS_USER = "hadoop"                     # Hadoop 用户名
HDFS_ROOT = "/forest"                    # HDFS 根目录

# HDFS 目录映射
HDFS_RASTER_DIR = f"{HDFS_ROOT}/raster"          # 特征栅格 HDFS 路径
HDFS_RESULT_DIR = f"{HDFS_ROOT}/results"         # 预测结果 HDFS 路径
HDFS_MODEL_DIR = f"{HDFS_ROOT}/results"          # 模型文件 HDFS 路径

# 初始化 HDFS 客户端
try:
    hdfs_client = InsecureClient(HDFS_URL, user=HDFS_USER)
    # 确保 HDFS 目录存在
    for hdfs_path in [HDFS_RASTER_DIR, HDFS_RESULT_DIR, HDFS_MODEL_DIR]:
        if not hdfs_client.status(hdfs_path, strict=False):
            hdfs_client.makedirs(hdfs_path)
    print(f"✅ 成功连接 HDFS 集群：{HDFS_URL}")
except Exception as e:
    hdfs_client = None
    print(f"⚠️ HDFS 连接失败，降级为本地模式：{str(e)}")

# ===================== 本地路径配置（降级备用） =====================
# 动态计算本地路径
CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(CURRENT_FILE_DIR)
PROJECT_ROOT = os.path.dirname(APP_DIR)

# 本地目录定义
LOCAL_RASTER_DIR = os.path.join(PROJECT_ROOT, "data", "特征栅格")
LOCAL_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "biomass_results")
LOCAL_MODEL_DIR = LOCAL_OUTPUT_DIR
LOCAL_PREDICT_SCRIPT_PATH = os.path.join(PROJECT_ROOT, "app", "ml", "biomass_pred.py")

# 确保本地目录存在
for local_dir in [LOCAL_RASTER_DIR, LOCAL_OUTPUT_DIR]:
    os.makedirs(local_dir, exist_ok=True)

# 前端访问前缀
FRONTEND_FILE_PREFIX = "http://localhost:8000/api/file/"

# ===================== Pydantic 模型 =====================
class PredictionRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())  # 解决命名空间冲突
    task_id: str
    model_metrics: List[Dict]

class PredictionResponse(BaseModel):
    code: int
    msg: str
    data: Optional[Dict] = None

# ===================== 核心工具函数 =====================
def download_from_hdfs(hdfs_path: str, local_temp_path: str):
    """从 HDFS 下载文件到本地临时路径"""
    if not hdfs_client:
        raise Exception("HDFS 客户端未初始化")
    
    try:
        hdfs_client.download(hdfs_path, local_temp_path, overwrite=True)
        print(f"✅ 从 HDFS 下载文件成功：{hdfs_path} -> {local_temp_path}")
        return local_temp_path
    except Exception as e:
        raise Exception(f"从 HDFS 下载文件失败：{hdfs_path}，错误：{str(e)}")

def upload_to_hdfs(local_path: str, hdfs_path: str):
    """将本地文件上传到 HDFS"""
    if not hdfs_client:
        raise Exception("HDFS 客户端未初始化")
    
    try:
        hdfs_client.upload(hdfs_path, local_path, overwrite=True)
        print(f"✅ 上传文件到 HDFS 成功：{local_path} -> {hdfs_path}")
        return hdfs_path
    except Exception as e:
        raise Exception(f"上传文件到 HDFS 失败：{local_path}，错误：{str(e)}")

def get_hdfs_file_list(hdfs_dir: str) -> List[str]:
    """获取 HDFS 目录下的文件列表"""
    if not hdfs_client:
        return []
    
    try:
        return hdfs_client.list(hdfs_dir)
    except Exception as e:
        print(f"⚠️ 获取 HDFS 目录列表失败：{hdfs_dir}，错误：{str(e)}")
        return []

# ===================== 筛选最优模型（兼容 HDFS） =====================
def select_best_model(model_metrics: List[Dict]) -> tuple:
    if not model_metrics:
        raise ValueError("无模型指标数据")
    
    # 1. 筛选最优模型名称
    sorted_by_r2 = sorted(model_metrics, key=lambda x: float(x["R²"]), reverse=True)
    top3_r2 = sorted_by_r2[:3]
    sorted_by_rmse = sorted(top3_r2, key=lambda x: float(x["RMSE"]))
    best_candidates = sorted(sorted_by_rmse[:1], key=lambda x: float(x["训练时间(s)"]) if x["训练时间(s)"] else float("inf"))
    best_model_name = best_candidates[0]["模型名称"]
    
    # 2. 优先从 HDFS 查找模型文件
    best_model_path = None
    best_feature_list_path = None
    temp_model_path = None
    temp_feature_path = None
    
    if hdfs_client:
        print(f"\n📂 优先从 HDFS 模型目录查找：{HDFS_MODEL_DIR}")
        hdfs_files = get_hdfs_file_list(HDFS_MODEL_DIR)
        for file in hdfs_files:
            print(f"  - HDFS 文件：{file}")
        
        # 查找 HDFS 中的模型文件
        for file in hdfs_files:
            if file.startswith(f"{best_model_name}_model_") and file.endswith(".joblib"):
                # 下载到本地临时文件
                temp_model_path = os.path.join(LOCAL_MODEL_DIR, file)
                download_from_hdfs(f"{HDFS_MODEL_DIR}/{file}", temp_model_path)
                best_model_path = temp_model_path
            elif file.startswith(f"{best_model_name}_feature_list_") and file.endswith(".joblib"):
                # 下载到本地临时文件
                temp_feature_path = os.path.join(LOCAL_MODEL_DIR, file)
                download_from_hdfs(f"{HDFS_MODEL_DIR}/{file}", temp_feature_path)
                best_feature_list_path = temp_feature_path
    
    # 3. 降级到本地查找
    if not best_feature_list_path:
        print(f"\n📂 HDFS 未找到模型文件，降级到本地目录：{LOCAL_MODEL_DIR}")
        for file in os.listdir(LOCAL_MODEL_DIR):
            print(f"  - 本地文件：{file}")
        
        for file in os.listdir(LOCAL_MODEL_DIR):
            if file.startswith(f"{best_model_name}_model_") and file.endswith(".joblib"):
                best_model_path = os.path.join(LOCAL_MODEL_DIR, file)
            elif file.startswith(f"{best_model_name}_feature_list_") and file.endswith(".joblib"):
                best_feature_list_path = os.path.join(LOCAL_MODEL_DIR, file)
    
    # 4. 验证文件存在性
    if not best_feature_list_path or not os.path.exists(best_feature_list_path):
        raise FileNotFoundError(
            f"最优模型特征列表不存在：{best_model_name}_feature_list_*.joblib\n"
            f"HDFS 路径：{HDFS_MODEL_DIR}\n"
            f"本地路径：{LOCAL_MODEL_DIR}"
        )
    
    print(f"✅ 筛选出最优模型：{best_model_name}")
    print(f"   - 模型路径：{best_model_path}")
    print(f"   - 特征列表路径：{best_feature_list_path}")
    return best_model_path, best_feature_list_path

# ===================== 空间预测函数（兼容 HDFS） =====================
def run_spatial_prediction(model_path: str, feature_list_path: str) -> Dict:
    # 1. 验证预测脚本存在
    predict_script_path = LOCAL_PREDICT_SCRIPT_PATH
    if not os.path.exists(predict_script_path):
        raise FileNotFoundError(f"❌ 预测脚本不存在：{predict_script_path}")
    
    # 2. 生成时间戳和输出路径
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    local_tif_output = os.path.join(LOCAL_OUTPUT_DIR, f"Biomass_Prediction_{timestamp}.tif")
    hdfs_tif_output = f"{HDFS_RESULT_DIR}/Biomass_Prediction_{timestamp}.tif"
    
    # 3. 确定栅格数据目录（优先 HDFS 下载到本地）
    raster_dir = LOCAL_RASTER_DIR
    if hdfs_client:
        # 将 HDFS 栅格文件下载到本地临时目录
        temp_raster_dir = os.path.join(LOCAL_RASTER_DIR, f"temp_{timestamp}")
        os.makedirs(temp_raster_dir, exist_ok=True)
        
        try:
            hdfs_client.download(HDFS_RASTER_DIR, temp_raster_dir, overwrite=True)
            raster_dir = temp_raster_dir
            print(f"✅ HDFS 栅格文件已下载到本地：{temp_raster_dir}")
        except Exception as e:
            print(f"⚠️ HDFS 栅格文件下载失败，使用本地栅格目录：{str(e)}")
            raster_dir = LOCAL_RASTER_DIR
    
    # 4. 构造调用命令
    cmd = [
        sys.executable,
        "-u",
        predict_script_path,
        "--model_path", model_path,
        "--feature_list_path", feature_list_path,
        "--raster_dir", raster_dir,
        "--output_path", local_tif_output
    ]
    
    try:
        # 5. 执行预测脚本
        print(f"\n🚀 开始执行空间预测脚本：{' '.join(cmd)}")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # 将 stderr 重定向到 stdout
            encoding="utf-8",
            errors="replace",
            cwd=os.path.dirname(predict_script_path)
        )
        
        # 实时打印输出
        output = []
        print("📝 预测脚本实时日志：")
        while process.poll() is None:
            line = process.stdout.readline()
            if line:
                print(line.strip())
                output.append(line)
        
        # 检查返回码
        if process.returncode != 0:
            raise subprocess.CalledProcessError(
                process.returncode, 
                cmd, 
                output=''.join(output)
            )
        
        # 6. 将预测结果上传到 HDFS（如果可用）
        storage_type = "LOCAL"
        if hdfs_client and os.path.exists(local_tif_output):
            try:
                upload_to_hdfs(local_tif_output, hdfs_tif_output)
                storage_type = "HDFS"
            except Exception as e:
                print(f"⚠️ 预测结果上传 HDFS 失败：{str(e)}")
        
        # 7. 构造返回结果
        tif_filename = os.path.basename(local_tif_output)
        png_filename = f"Biomass_Prediction_{timestamp}_渲染图.png"
        
        result = {
            "tif_local_path": local_tif_output,
            "tif_hdfs_path": hdfs_tif_output if hdfs_client else "",
            "tif_path": FRONTEND_FILE_PREFIX + tif_filename,
            "png_path": FRONTEND_FILE_PREFIX + png_filename,
            "timestamp": timestamp,
            "storage_type": storage_type,
            "raster_source": "HDFS" if raster_dir != LOCAL_RASTER_DIR else "LOCAL"
        }
        
        print(f"\n✅ 空间预测完成！")
        print(f"   - 本地文件：{local_tif_output}")
        print(f"   - HDFS 文件：{hdfs_tif_output if storage_type == 'HDFS' else '未上传'}")
        print(f"   - 存储类型：{storage_type}")
        
        return result
    
    except subprocess.TimeoutExpired:
        raise Exception("空间预测超时（超过1小时）")
    except subprocess.CalledProcessError as e:
        error_msg = f"""
        脚本执行失败！
        返回码：{e.returncode}
        命令：{' '.join(cmd)}
        执行输出：{''.join(output)}
        """
        print(error_msg)
        raise Exception(f"预测脚本执行失败：{error_msg}")
    except Exception as e:
        raise Exception(f"空间预测失败：{str(e)}")
    finally:
        # 清理临时栅格目录
        if 'temp_raster_dir' in locals() and os.path.exists(temp_raster_dir):
            import shutil
            try:
                shutil.rmtree(temp_raster_dir)
                print(f"🗑️ 清理临时栅格目录：{temp_raster_dir}")
            except Exception as e:
                print(f"⚠️ 清理临时目录失败：{str(e)}")

# ===================== API 接口 =====================
@router.post("/spatial-prediction", response_model=PredictionResponse)
async def spatial_prediction(req: PredictionRequest):
    try:
        # 1. 筛选最优模型
        best_model_path, best_feature_list_path = select_best_model(req.model_metrics)
        
        # 2. 执行空间预测
        prediction_result = run_spatial_prediction(best_model_path, best_feature_list_path)
        
        # 3. 返回结果
        return {
            "code": 200,
            "msg": f"空间预测成功（存储类型：{prediction_result['storage_type']}）",
            "data": prediction_result
        }
    except Exception as e:
        print(f"❌ 空间预测接口异常：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ===================== 新增：预测状态查询接口 =====================
@router.get("/prediction-status/{timestamp}", response_model=PredictionResponse)
async def get_prediction_status(timestamp: str):
    """查询指定时间戳的预测结果状态"""
    try:
        # 检查本地文件
        local_tif = os.path.join(LOCAL_OUTPUT_DIR, f"Biomass_Prediction_{timestamp}.tif")
        local_exists = os.path.exists(local_tif)
        
        # 检查 HDFS 文件
        hdfs_tif = f"{HDFS_RESULT_DIR}/Biomass_Prediction_{timestamp}.tif"
        hdfs_exists = False
        if hdfs_client:
            hdfs_exists = hdfs_client.status(hdfs_tif, strict=False) is not None
        
        status = "completed" if local_exists or hdfs_exists else "failed"
        storage_type = "HDFS" if hdfs_exists else "LOCAL" if local_exists else "UNKNOWN"
        
        return {
            "code": 200,
            "msg": f"查询预测状态成功",
            "data": {
                "timestamp": timestamp,
                "status": status,
                "storage_type": storage_type,
                "local_path": local_tif if local_exists else "",
                "hdfs_path": hdfs_tif if hdfs_exists else "",
                "access_url": FRONTEND_FILE_PREFIX + f"Biomass_Prediction_{timestamp}.tif" if local_exists or hdfs_exists else ""
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询预测状态失败：{str(e)}")