# 1. 必须显式导入 Enum（解决“未定义Enum”的核心问题）
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any, List, Literal
from enum import Enum  # 👈 新增这一行，关键导入！

# ===================== 任务状态枚举类（修复：标准 Enum，替代 Literal） =====================
class TaskStatus(str, Enum):
    """
    任务状态枚举（与前端完全对齐）
    - PENDING: 待执行
    - RUNNING: 运行中
    - COMPLETED: 已完成
    - FAILED: 失败
    """
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

# ===================== 用户相关模型（保留） =====================
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="用户名，3-50个字符")
    password: str = Field(..., min_length=6, max_length=72, description="密码，6-72个字符")

class UserLogin(BaseModel):
    username: str = Field(..., description="登录用户名")
    password: str = Field(..., description="登录密码")

class UserResponse(BaseModel):
    id: int
    username: str
    create_time: datetime

    model_config = {
        "from_attributes": True,
        "protected_namespaces": (),
        "json_schema_extra": {"example": {"id": 1, "username": "admin", "create_time": "2026-02-28 12:00:00"}}
    }

class TokenResponse(BaseModel):
    token: str
    username: str

    model_config = {
        "protected_namespaces": (),
        "json_schema_extra": {"example": {"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", "username": "admin"}}
    }

# ===================== 算法任务参数模型（与前端currentParams完全对齐） =====================
class TaskParams(BaseModel):
    input_path: Optional[str] = Field("dataset://default", description="输入Excel文件路径")
    output_dir: Optional[str] = Field("/data/biomass_results", description="结果输出目录")
    test_size: Optional[float] = Field(0.2, ge=0.1, le=0.5, description="测试集比例（0.1-0.5）")
    random_state: Optional[int] = Field(42, description="随机种子")
    feature_selection: Optional[bool] = Field(True, description="是否启用特征选择")
    target: Optional[str] = Field("forest", description="单目标提取的目标类型")
    raster_dir: Optional[str] = Field(None, description="空间预测栅格目录")
    timestamp: Optional[str] = Field(None, description="前端透传时间戳（YYYYMMDDHHMMSS）")

    model_config = {
        "protected_namespaces": (),
        "json_schema_extra": {
            "example": {
                "input_path": "/data/111.xls",
                "output_dir": "/data/biomass_results",
                "feature_selection": True,
                "test_size": 0.2,
                "random_state": 42,
                "target": "forest",
                "timestamp": "20260315170000"
            }
        }
    }

# ===================== 模型评价指标模型（修复命名规范，兼容前端） =====================
class ModelMetric(BaseModel):
    model_name: str = Field(..., description="模型名称", alias="模型名称")
    r_squared: Optional[float] = Field(0.0, description="决定系数 R²", alias="R²")
    rmse: Optional[float] = Field(0.0, description="均方根误差", alias="RMSE")
    mae: Optional[float] = Field(0.0, description="平均绝对误差", alias="MAE")
    train_time: Optional[float] = Field(0.0, description="训练时间（秒）", alias="训练时间(s)")
    best_n_estimators: Optional[str] = Field("", description="最优迭代数", alias="最佳n_estimators")
    feature_count: Optional[int] = Field(0, description="使用的特征数量", alias="使用的特征数")
    feature_list: Optional[str] = Field("", description="特征列表字符串", alias="特征列表")

    model_config = {
        "protected_namespaces": (),
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "模型名称": "XGBoost",
                "R²": 0.895,
                "RMSE": 5.231,
                "MAE": 3.124,
                "训练时间(s)": 2.56,
                "最佳n_estimators": "100",
                "使用的特征数": 15,
                "特征列表": "NDVI,Slope,Aspect"
            }
        }
    }

# ===================== 输出文件模型（与前端output_files结构完全对齐） =====================
class ModelFileInfo(BaseModel):
    model_path: str = Field(..., description="模型文件完整路径")
    feature_list_path: Optional[str] = Field("", description="特征列表文件路径")
    hdfs_model_path: Optional[str] = Field("", description="HDFS模型文件路径")
    hdfs_feature_list_path: Optional[str] = Field("", description="HDFS特征列表路径")
    timestamp: Optional[str] = Field("", description="时间戳")

    model_config = {"protected_namespaces": ()}

class OutputFiles(BaseModel):
    rmse_plot: Optional[str] = Field("", description="RMSE对比图路径")
    fit_plots: Optional[Dict[str, str]] = Field({}, description="各模型拟合图路径")
    predictions_csv: Optional[str] = Field("", description="预测结果CSV路径")
    metrics_csv: Optional[str] = Field("", description="评价指标CSV路径")
    model_files: Optional[Dict[str, ModelFileInfo]] = Field({}, description="模型文件信息")
    feature_file: Optional[str] = Field("", description="特征名称文件路径")
    shap_plot: Optional[str] = Field("", description="SHAP特征重要性图路径")
    heatmap_plot: Optional[str] = Field("", description="生物量热点图路径")
    corr_heatmap_plot: Optional[str] = Field("", description="特征相关性热力图路径")
    model_path: Optional[str] = Field("", description="最佳模型路径")
    feature_list_path: Optional[str] = Field("", description="最佳模型特征列表路径")
    hdfs_enabled: Optional[bool] = Field(False, description="是否启用HDFS")
    hdfs_root: Optional[str] = Field("", description="HDFS根路径")

    model_config = {"protected_namespaces": ()}

# ===================== 空间预测结果模型 =====================
class SpatialPredictionResult(BaseModel):
    model_used: str = Field(..., description="使用的最佳模型名称")
    files: Optional[Dict[str, str]] = Field({}, description="空间预测输出文件")
    status: Literal['success', 'failed'] = Field("failed", description="空间预测状态")
    error: Optional[str] = Field("", description="空间预测错误信息")
    timestamp: Optional[str] = Field("", description="时间戳")

    model_config = {"protected_namespaces": ()}

# ===================== 统计信息模型（与前端statistics完全对齐） =====================
class Statistics(BaseModel):
    total_area: Optional[int] = Field(0, description="总面积")
    total_biomass: Optional[float] = Field(0.0, description="总生物量")
    distribution: Optional[Dict[str, int]] = Field({}, description="区域分布")
    time_series: Optional[Dict[str, int]] = Field({}, description="时间序列数据")
    carbon_storage: Optional[float] = Field(0.0, description="碳储量")
    forest_coverage: Optional[float] = Field(0.0, description="森林覆盖率")
    device_online_rate: Optional[float] = Field(0.0, description="设备在线率")
    season_growth: Optional[Dict[str, float]] = Field({}, description="季节生长量")
    tree_species: Optional[Dict[str, int]] = Field({}, description="树种分布")
    future_predict: Optional[Dict[str, Dict[str, int]]] = Field({}, description="未来预测")
    env_factors: Optional[Dict[str, List[float]]] = Field({}, description="环境因子数据")

    model_config = {"protected_namespaces": ()}

# ===================== 任务结果模型（与前端TaskResult完全对齐） =====================
class TaskResult(BaseModel):
    status: TaskStatus = Field(..., description="任务状态（使用枚举类）")  # 👈 改为 TaskStatus 枚举
    timestamp: Optional[str] = Field("", description="前端透传时间戳")
    feature_names: Optional[List[str]] = Field([], description="使用的特征名称列表")
    feature_count: Optional[int] = Field(0, description="特征数量")
    train_samples: Optional[int] = Field(0, description="训练样本数")
    test_samples: Optional[int] = Field(0, description="测试样本数")
    model_metrics: Optional[List[ModelMetric]] = Field([], description="各模型评价指标")
    output_files: Optional[OutputFiles] = Field(None, description="输出文件路径")
    best_model: Optional[str] = Field("", description="最优模型名称")
    error: Optional[str] = Field("", description="任务失败时的错误信息")
    spatial_prediction: Optional[SpatialPredictionResult] = Field(None, description="空间预测结果")
    statistics: Optional[Statistics] = Field(None, description="统计信息")
    task_id: Optional[str] = Field("", description="任务ID")
    hdfs_enabled: Optional[bool] = Field(False, description="是否启用HDFS")

    model_config = {"protected_namespaces": ()}

# ===================== 任务创建请求/响应模型 =====================
class TaskCreate(BaseModel):
    algorithm: str = Field(..., description="算法名称：biomass_prediction/single_target_extraction")
    params: TaskParams = Field(..., description="算法执行参数")

    model_config = {
        "protected_namespaces": (),
        "json_schema_extra": {
            "example": {
                "algorithm": "biomass_prediction",
                "params": {
                    "input_path": "/data/样点已提取特征V4_TableToExcel_1.xls",
                    "test_size": 0.2,
                    "timestamp": "20260315170000"
                }
            }
        }
    }

class TaskStatusResponse(BaseModel):
    task_id: str
    status: TaskStatus  # 👈 改为枚举类型，不再用 Literal
    timestamp: Optional[str] = Field("", description="时间戳")
    error: Optional[str] = Field("", description="错误信息")
    feature_names: Optional[List[str]] = Field([], description="特征名称列表")
    feature_count: Optional[int] = Field(0, description="特征数量")
    train_samples: Optional[int] = Field(0, description="训练样本数")
    test_samples: Optional[int] = Field(0, description="测试样本数")
    model_metrics: Optional[List[ModelMetric]] = Field([], description="模型评价指标")
    output_files: Optional[OutputFiles] = Field(None, description="输出文件")
    best_model: Optional[str] = Field("", description="最佳模型")
    spatial_prediction_status: Optional[str] = Field("", description="空间预测状态")
    spatial_prediction_error: Optional[str] = Field("", description="空间预测错误")
    spatial_output_files: Optional[Dict[str, str]] = Field({}, description="空间预测输出文件")
    storage_type: Optional[str] = Field("local", description="存储类型")
    create_time: Optional[str] = Field("", description="任务创建时间")
    update_time: Optional[str] = Field("", description="任务更新时间")
    statistics: Optional[Statistics] = Field(None, description="统计信息")

    model_config = {
        "from_attributes": True,
        "protected_namespaces": (),
        "json_schema_extra": {
            "example": {
                "task_id": "f8d2a7b9-1234-5678-90ab-cdef12345678",
                "status": "success",
                "timestamp": "20260228170000",
                "feature_count": 15,
                "train_samples": 800,
                "test_samples": 200,
                "best_model": "XGBoost",
                "model_metrics": [
                    {
                        "模型名称": "XGBoost",
                        "R²": 0.895,
                        "RMSE": 5.231,
                        "MAE": 3.124,
                        "训练时间(s)": 2.56
                    }
                ],
                "output_files": {
                    "rmse_plot": "/data/biomass_results/RMSE比较_20260228170000.png",
                    "predictions_csv": "/data/biomass_results/模型预测结果_20260228170000.csv",
                    "model_files": {
                        "XGBoost": {
                            "model_path": "/data/biomass_results/XGBoost_model_20260228170000.joblib",
                            "feature_list_path": "/data/biomass_results/XGBoost_feature_list_20260228170000.joblib"
                        }
                    }
                },
                "spatial_output_files": {
                    "tif_path": "/data/results/空间生物量预测_20260315170000.tif"
                },
                "storage_type": "local",
                "statistics": {
                    "total_area": 27720,
                    "total_biomass": 12.5,
                    "distribution": {"帽儿山核心区": 15000, "帽儿山东区": 8000, "帽儿山西区": 4720},
                    "time_series": {"2014": 24000, "2016": 25000, "2018": 25800, "2020": 26800, "2022": 27400, "2023": 27720}
                }
            }
        }
    }

class TaskResponse(BaseModel):
    task_id: str
    message: str
    status: TaskStatus = Field("processing", description="初始任务状态")  # 👈 改为枚举
    timestamp: Optional[str] = Field("", description="时间戳")
    storage_type: Optional[str] = Field("local", description="存储类型")

    model_config = {
        "protected_namespaces": (),
        "json_schema_extra": {
            "example": {
                "task_id": "f8d2a7b9-1234-5678-90ab-cdef12345678",
                "message": "任务已提交成功",
                "status": "processing",
                "timestamp": "20260315170000",
                "storage_type": "local"
            }
        }
    }

class ChatMessage(BaseModel):
    """前端发来的消息格式"""
    message: str
    history: Optional[List[dict]] = []  # 聊天记录（可选）

class ChatResponse(BaseModel):
    """后端返回的消息格式"""
    answer: str
    source: Optional[str] = None  # 数据来源（比如引用了哪个文件或数据库）