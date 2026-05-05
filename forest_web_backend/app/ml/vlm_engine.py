# -*- coding: utf-8 -*-
"""
VLM 生物量估算引擎
基于 Qwen2-VL 模型，支持大图分块推理与结构化输出
"""
import os
import logging
import json
import tempfile
import shutil
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from PIL import Image
import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling

# 引入智能文件系统
from .fs_layer import get_fs
from app.core.config import settings # 假设你的配置在这里

# VLM 依赖 (需安装: pip install transformers accelerate torch pillow)
try:
    import torch
    from transformers import AutoProcessor, AutoModelForVision2Seq
    from qwen_vl_utils import process_vision_info
except ImportError:
    torch = None
    AutoProcessor = None
    AutoModelForVision2Seq = None

logger = logging.getLogger("biomass_prediction")

# ===================== 配置常量 =====================
DEFAULT_PROMPT = (
    "你是一位专业的林业遥感专家。请分析这张卫星遥感图像，"
    "估算该区域的平均地上生物量 (AGB, 单位：吨/公顷)。"
    "请观察植被覆盖度、颜色和纹理特征。"
    "请直接返回一个 JSON 格式的结果，不要包含其他废话。"
    "JSON 格式要求：{\"estimated_agb\": float, \"confidence\": float (0-1), \"reasoning\": \"简短的分析理由\"}"
)

@dataclass
class VLMConfig:
    model_name: str = "Qwen/Qwen2-VL-7B-Instruct" # 可切换为 2B 或 72B
    max_pixels: int = 1280 * 28 * 28  # Qwen2-VL 推荐的最大像素数 (约 1M pixels)
    device: str = "cuda" if torch and torch.cuda.is_available() else "cpu"
    dtype: str = "bfloat16" if torch and torch.cuda.is_available() else "float32"
    batch_size: int = 1

# ===================== VLM 引擎类 =====================
class VLMBiomassEngine:
    def __init__(self, config: VLMConfig = None):
        self.config = config or VLMConfig()
        self.model = None
        self.processor = None
        self._initialized = False

    def load_model(self):
        """懒加载模型，避免启动时占用过多显存"""
        if self._initialized:
            return
        
        if torch is None:
            raise ImportError("未安装 torch 或 transformers。请运行: pip install torch transformers accelerate qwen-vl-utils")

        logger.info(f"正在加载 VLM 模型：{self.config.model_name} ({self.config.device})...")
        
        # 加载处理器和模型
        self.processor = AutoProcessor.from_pretrained(
            self.config.model_name, 
            trust_remote_code=True
        )
        
        self.model = AutoModelForVision2Seq.from_pretrained(
            self.config.model_name,
            torch_dtype=getattr(torch, self.config.dtype),
            device_map="auto", # 自动分配 GPU/CPU
            trust_remote_code=True
        )
        
        self.model.eval()
        self._initialized = True
        logger.info("✅ VLM 模型加载完成")

    def _preprocess_image(self, image_path: str) -> Image.Image:
        """
        预处理图像：
        1. 如果是 TIF，转换为 PNG (去除 NoData，转为 RGB)
        2. 调整大小以适应模型输入限制 (可选)
        """
        fs = get_fs(settings)
        
        # 1. 下载/读取到临时文件
        temp_dir = tempfile.mkdtemp(prefix="vlm_input_")
        local_path = os.path.join(temp_dir, "input.png")
        
        try:
            # 处理 TIF 转 PNG 逻辑
            if image_path.lower().endswith('.tif') or image_path.lower().endswith('.tiff'):
                # 从文件系统读取字节或路径
                # 这里为了简单，先下载到本地再处理
                fs.download(image_path, local_path) if not os.path.exists(image_path) else shutil.copy(image_path, local_path)
                
                with rasterio.open(local_path) as src:
                    # 读取第一个波段作为灰度，或者合成假彩色
                    # 策略：取前三个波段作为 RGB，如果没有则复制单波段
                    bands = src.read()
                    if bands.shape[0] >= 3:
                        rgb_data = np.stack([bands[0], bands[1], bands[2]], axis=-1)
                    elif bands.shape[0] == 1:
                        rgb_data = np.stack([bands[0]] * 3, axis=-1)
                    else:
                        # 兜底：取可用波段重复
                        rgb_data = np.stack([bands[0]] * 3, axis=-1)
                    
                    # 归一化到 0-255 (简单的线性拉伸，实际项目中可根据直方图优化)
                    min_val, max_val = np.nanpercentile(rgb_data, [1, 99])
                    rgb_data = np.clip((rgb_data - min_val) / (max_val - min_val + 1e-6) * 255, 0, 255).astype(np.uint8)
                    
                    # 处理 NoData
                    mask = np.any(bands[0] == src.nodata, axis=0)
                    rgb_data[mask] = [0, 0, 0] # 背景设为黑色

                    img = Image.fromarray(rgb_data)
            else:
                # 直接打开 PNG/JPG
                fs.download(image_path, local_path) if not os.path.exists(image_path) else shutil.copy(image_path, local_path)
                img = Image.open(local_path).convert('RGB')
            
            return img
        finally:
            # 清理临时下载的文件 (保留转换后的 img 对象在内存中)
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def _resize_for_model(self, image: Image.Image) -> Image.Image:
        """如果图片过大，进行缩放以符合模型像素限制"""
        width, height = image.size
        total_pixels = width * height
        
        if total_pixels > self.config.max_pixels:
            scale = (self.config.max_pixels / total_pixels) ** 0.5
            new_width = int(width * scale)
            new_height = int(height * scale)
            logger.info(f"图像过大 ({width}x{height})，缩放至 {new_width}x{new_height}")
            return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        return image

    def predict(self, image_path: str, prompt: str = DEFAULT_PROMPT) -> Dict[str, Any]:
        """
        执行单次推理
        :param image_path: 图像路径 (本地绝对路径 / 虚拟路径 / HDFS 路径)
        :param prompt: 提示词
        :return: 解析后的 JSON 字典
        """
        self.load_model()
        
        logger.info(f"开始 VLM 推理：{image_path}")
        
        # 1. 预处理图像
        image = self._preprocess_image(image_path)
        image = self._resize_for_model(image)
        
        # 2. 构建消息
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        
        # 3. 准备输入
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages)
        
        inputs = self.processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt"
        )
        inputs = inputs.to(self.model.device)
        
        # 4. 生成
        with torch.no_grad():
            generated_ids = self.model.generate(**inputs, max_new_tokens=512)
        
        generated_ids_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        
        output_text = self.processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0]
        
        logger.info(f"VLM 原始输出：{output_text}")
        
        # 5. 解析 JSON
        return self._parse_json_response(output_text)

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """提取并解析 JSON，具备容错能力"""
        import re
        try:
            # 尝试直接加载
            return json.loads(text)
        except json.JSONDecodeError:
            # 尝试提取代码块中的 JSON
            match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except:
                    pass
            
            # 尝试提取大括号内容
            match = re.search(r"\{.*?\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except:
                    pass
        
        # 如果都失败，返回默认结构
        logger.warning("无法解析 VLM 输出的 JSON，返回默认结构")
        return {
            "estimated_agb": 0.0,
            "confidence": 0.0,
            "reasoning": f"模型输出解析失败：{text[:200]}..."
        }

# ===================== 对外接口函数 =====================
def run_vlm_biomass_estimation(
    image_path: str,
    output_json_path: str,
    prompt: str = DEFAULT_PROMPT,
    model_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    主入口函数：运行 VLM 估算并保存结果
    """
    config = VLMConfig()
    if model_name:
        config.model_name = model_name
        
    engine = VLMBiomassEngine(config)
    
    try:
        result = engine.predict(image_path, prompt)
        
        # 保存结果到文件系统
        fs = get_fs(settings)
        
        # 将结果写入临时文件然后上传
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(result, temp_file, ensure_ascii=False, indent=2)
        temp_file.close()
        
        fs.upload(temp_file.name, output_json_path)
        os.remove(temp_file.name)
        
        logger.info(f"VLM 估算完成，结果已保存至：{output_json_path}")
        return result
        
    except Exception as e:
        logger.error(f"VLM 估算失败：{str(e)}", exc_info=True)
        raise

# ===================== 测试入口 =====================
if __name__ == "__main__":
    # 测试用例
    test_img = "/data/raster/NDVI.tif" # 虚拟路径
    test_out = "/data/results/vlm_result.json"
    
    try:
        res = run_vlm_biomass_estimation(test_img, test_out)
        print("结果:", res)
    except Exception as e:
        print("测试失败:", e)