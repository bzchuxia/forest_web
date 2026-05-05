from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.fast_trainer import quick_train_and_evaluate

router = APIRouter()

class TrainPreviewRequest(BaseModel):
    modelType: str
    epochs: int
    learningRate: float
    depth: int
    regCoef: float
    testRatio: float = 0.2

class SaveConfigRequest(BaseModel):
    config: dict
    taskId: str

# 全局变量存储最新保存的配置 (在实际生产中应存入数据库或 Redis)
saved_configs = {}

@router.post("/preview")
async def preview_training(req: TrainPreviewRequest):
    """实时预览训练结果"""
    try:
        result = quick_train_and_evaluate(req.dict())
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/save-config")
async def save_current_config(req: SaveConfigRequest):
    """保存当前调优的参数配置"""
    config_id = f"config_{req.taskId}"
    saved_configs[config_id] = req.config
    # 这里也可以写入数据库，标记为 "待执行的分析任务参数"
    print(f"✅ 配置已保存：{config_id} -> {req.config}")
    return {"success": True, "message": "配置已保存，可在处理分析页面使用"}

@router.get("/get-saved-config/{task_id}")
async def get_saved_config(task_id: str):
    """供处理分析页面获取保存的配置"""
    config_id = f"config_{task_id}"
    if config_id in saved_configs:
        return {"success": True, "data": saved_configs[config_id]}
    return {"success": False, "message": "未找到保存的配置"}