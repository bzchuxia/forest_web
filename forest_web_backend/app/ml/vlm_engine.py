# -*- coding: utf-8 -*-
"""
VLM 生物量估算引擎（增强版）
支持：HDFS自动遍历、时序对比、多文件分析、变化检测、专业建议输出
"""
import os
import re
import logging
import json
import tempfile
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from PIL import Image
import numpy as np
import rasterio

from .fs_layer import get_fs
from app.core.config import settings

try:
    import torch
    from transformers import AutoProcessor, AutoModelForVision2Seq
    from qwen_vl_utils import process_vision_info
except ImportError:
    torch = None
    AutoProcessor = None
    AutoModelForVision2Seq = None

logger = logging.getLogger("biomass_prediction")

# ===================== 增强版 PROMPT =====================
COMPARISON_PROMPT = """
你是一位高级林业遥感专家。
现在你需要对比【当前时段】和【上一时段】的卫星影像与指标数据：

1. 分析生物量（AGB）、植被健康度、空间分布变化
2. 判断变化趋势：上升 / 下降 / 平稳
3. 判断变化原因：自然生长、干旱、病虫害、采伐、云量、人为干扰
4. 给出专业、可执行的林业管理建议

请输出严格的JSON格式，不要多余内容：
{
    "current_agb": 数值,
    "previous_agb": 数值,
    "change_ratio": "变化率%",
    "change_trend": "上升/下降/平稳",
    "change_reason": "原因分析",
    "suggestions": ["建议1","建议2","建议3"],
    "confidence": 0~1
}
"""

@dataclass
class VLMConfig:
    model_name: str = "Qwen/Qwen2-VL-7B-Instruct"
    max_pixels: int = 1280 * 1280
    device: str = "cuda" if torch and torch.cuda.is_available() else "cpu"
    dtype: str = "bfloat16" if torch and torch.cuda.is_available() else "float32"

# ===================== 核心引擎 =====================
class VLMBiomassEngine:
    def __init__(self, config: VLMConfig = None):
        self.config = config or VLMConfig()
        self.model = None
        self.processor = None
        self._initialized = False
        self.fs = get_fs(settings)

    def load_model(self):
        if self._initialized: return
        logger.info("加载 VLM 模型...")
        self.processor = AutoProcessor.from_pretrained(self.config.model_name, trust_remote_code=True)
        self.model = AutoModelForVision2Seq.from_pretrained(
            self.config.model_name,
            torch_dtype=getattr(torch, self.config.dtype),
            device_map="auto",
            trust_remote_code=True
        )
        self.model.eval()
        self._initialized = True

    # ------------------- 工具：获取所有时间戳目录 -------------------
    def get_all_timestamps(self, base_path: str = "/forest/results") -> List[str]:
        folders = self.fs.ls(base_path)
        ts_list = []
        for f in folders:
            name = os.path.basename(f.rstrip('/'))
            if re.match(r'^\d{10,}$', name):
                ts_list.append(name)
        ts_list = sorted(ts_list)
        return ts_list

    # ------------------- 工具：获取 当前 / 上一个 时间戳 -------------------
    def get_current_and_previous(self, base_path: str = "/forest/results") -> Tuple[Optional[str], Optional[str]]:
        ts_list = self.get_all_timestamps(base_path)
        if len(ts_list) >= 2:
            return ts_list[-1], ts_list[-2]
        elif len(ts_list) == 1:
            return ts_list[0], None
        return None, None

    # ------------------- 工具：加载一个时间戳目录下所有文件 -------------------
    def load_timestamp_data(self, ts: str, base_path: str = "/forest/results") -> Dict[str, Any]:
        root = f"{base_path}/{ts}"
        files = self.fs.ls(root)
        res = {"tif": [], "img": [], "json": [], "json_data": []}
        for f in files:
            low = f.lower()
            if low.endswith((".tif", ".tiff")):
                res["tif"].append(f)
            if low.endswith((".png", ".jpg", ".jpeg")):
                res["img"].append(f)
            if low.endswith(".json"):
                res["json"].append(f)
                try:
                    local = tempfile.mktemp(".json")
                    self.fs.download(f, local)
                    res["json_data"].append(json.load(open(local, encoding='utf-8')))
                except:
                    pass
        return res

    # ------------------- 图像预处理（HDFS 兼容） -------------------
    def _preprocess_image(self, hdfs_path: str) -> Image.Image:
        tmp = tempfile.mkdtemp()
        local = os.path.join(tmp, "input.tif")
        try:
            self.fs.download(hdfs_path, local)
            with rasterio.open(local) as src:
                bands = src.read()
                if bands.shape[0] >= 3:
                    rgb = np.stack([bands[0], bands[1], bands[2]], axis=-1)
                else:
                    rgb = np.stack([bands[0]] * 3, axis=-1)
                mi, ma = np.nanpercentile(rgb, [1, 99])
                rgb = np.clip((rgb - mi) / (ma - mi + 1e-6) * 255, 0, 255).astype(np.uint8)
                return Image.fromarray(rgb)
        finally:
            shutil.rmtree(tmp)

    def _resize(self, img: Image.Image) -> Image.Image:
        if img.size[0] * img.size[1] > self.config.max_pixels:
            scale = (self.config.max_pixels / (img.size[0] * img.size[1])) ** 0.5
            return img.resize((int(img.size[0] * scale), int(img.size[1] * scale)), Image.Resampling.LANCZOS)
        return img

    # ------------------- 双图对比推理（核心） -------------------
    def predict_compare(self, current_ts: str, prev_ts: str):
        self.load_model()
        curr_data = self.load_timestamp_data(current_ts)
        prev_data = self.load_timestamp_data(prev_ts)

        curr_img = self._resize(self._preprocess_image(curr_data["tif"][0]))
        prev_img = self._resize(self._preprocess_image(prev_data["tif"][0]))

        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": "当前时段卫星图："},
                {"type": "image", "image": curr_img},
                {"type": "text", "text": "上一时段卫星图："},
                {"type": "image", "image": prev_img},
                {"type": "text", "text": COMPARISON_PROMPT}
            ]
        }]

        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        img_inputs, _ = process_vision_info(messages)
        inputs = self.processor(text=[text], images=img_inputs, padding=True, return_tensors="pt").to(self.device)

        with torch.no_grad():
            out = self.model.generate(**inputs, max_new_tokens=1024)

        out_text = self.processor.batch_decode(out[:, inputs.input_ids.shape[1]:], skip_special_tokens=True)[0]
        return self._parse_json(out_text)

    def _parse_json(self, text: str) -> Dict:
        try:
            return json.loads(text)
        except:
            pass
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
        return {"error": "parse_failed", "raw": text[:300]}

# ===================== 对外主接口 =====================
def run_vlm_comparison_analysis(
    base_hdfs_path: str = "/forest/results",
    output_hdfs_path: str = "/forest/vlm_output/comparison_result.json"
) -> Dict[str, Any]:
    engine = VLMBiomassEngine()
    curr_ts, prev_ts = engine.get_current_and_previous(base_hdfs_path)

    if not curr_ts:
        raise Exception("未找到任何时间戳目录")
    if not prev_ts:
        raise Exception("至少需要两个时间戳才能对比")

    logger.info(f"正在对比：当前={curr_ts}  上一周期={prev_ts}")
    result = engine.predict_compare(curr_ts, prev_ts)

    # 保存到HDFS
    fs = get_fs(settings)
    tmp = tempfile.mktemp(".json")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({
            "current_timestamp": curr_ts,
            "previous_timestamp": prev_ts,
            "analysis_time": datetime.now().isoformat(),
            "analysis_result": result
        }, f, ensure_ascii=False, indent=2)
    fs.upload(tmp, output_hdfs_path)
    os.remove(tmp)

    logger.info("✅ 时序对比分析完成，结果已保存至HDFS")
    return result
def run_vlm_biomass_estimation(
    image_path: str,
    output_json_path: str,
    prompt: Optional[str] = None,
    model_name: Optional[str] = None
):
    """
    前端调用的真实 VLM 生物量估算接口
    输入：图片路径
    输出：AI 分析后的 JSON 结果
    """
    engine = VLMBiomassEngine()
    
    # 执行预测
    result = engine.predict_single_image(image_path, prompt)

    # 保存结果到文件
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 返回给前端
    return {
        "status": "success",
        "image_path": image_path,
        "output_path": output_json_path,
        "result": result
    }
def predict_single_image(self, image_path: str, prompt: Optional[str] = None):
    self.load_model()
    # 读取单张图片
    img = self._resize(self._preprocess_image(image_path))

    default_prompt = """
你是林业遥感专家，请根据这张卫星影像估算森林地上生物量AGB，只输出JSON：
{
    "AGB": 数值,
    "vegetation_health": "良好/一般/较差",
    "analysis": "简短分析"
}
"""
    user_prompt = prompt or default_prompt

    messages = [{
        "role": "user",
        "content": [
            {"type": "image", "image": img},
            {"type": "text", "text": user_prompt}
        ]
    }]

    text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    img_inputs, _ = process_vision_info(messages)
    inputs = self.processor(text=[text], images=img_inputs, padding=True, return_tensors="pt").to(self.device)

    with torch.no_grad():
        out = self.model.generate(**inputs, max_new_tokens=1024)

    out_text = self.processor.batch_decode(out[:, inputs.input_ids.shape[1]:], skip_special_tokens=True)[0]
    return self._parse_json(out_text)


# ===================== 测试 =====================
if __name__ == "__main__":
    try:
        final_result = run_vlm_comparison_analysis()
        print("最终分析结果：")
        print(json.dumps(final_result, indent=2, ensure_ascii=False))
    except Exception as e:
        print("失败：", e)