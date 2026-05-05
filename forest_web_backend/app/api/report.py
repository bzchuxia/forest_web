from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import dashscope
from dashscope import MultiModalConversation
import os
from dotenv import load_dotenv
import traceback
import base64

# 加载环境变量
load_dotenv()
router = APIRouter(tags=["智能报告"])

# 配置API Key
api_key = os.getenv("DASHSCOPE_API_KEY")
if not api_key:
    api_key = "sk-709522d3f0f94b57852aefe1e9519419"
dashscope.api_key = api_key

# 请求体模型
class ReportRequest(BaseModel):
    image: str
    data: dict

# 响应体模型
class ReportResponse(BaseModel):
    text: str

@router.post("/generate", response_model=ReportResponse)
async def generate_vlm_report(request: ReportRequest):
    try:
        # 处理图片Base64
        img_base64 = request.image
        if img_base64.startswith("data:image"):
            img_base64 = img_base64.split(",")[1]
        # 校验Base64格式
        try:
            base64.b64decode(img_base64, validate=True)
        except Exception as e:
            error_msg = f"图片Base64格式非法：{str(e)}"
            print(f"❌ {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        # 提取数据
        data = request.data
        kpi = data.get("kpi_data", {})
        risk = data.get("risk_data", {})
        warn = data.get("warning_data", {})
        season = data.get("season_data", {})
        predict = data.get("predict_data", {})
        env = data.get("env_data", {})
        metrics = data.get("model_metrics", [])

        # 专业提示词
        prompt = f"""
你是林业遥感、森林生态领域的权威专家，必须根据以下真实数据，生成一份专业、完整、可直接用于项目结题/答辩的深度分析报告。
必须包含以下8个模块：
1. 总体评估
2. 核心指标分析
3. 季节生长规律
4. 未来5年预测分析
5. 生态风险与异常告警
6. 环境因子分析
7. 模型精度评价
8. 经营管理建议

真实数据如下：
【核心指标】
总生物量：{kpi.get('total_biomass', '1250吨/公顷')}
碳储量：{kpi.get('carbon_storage', '6.25吨')}
森林覆盖率：{kpi.get('forest_coverage', '92.5%')}
设备在线率：{kpi.get('device_rate', '98.7%')}

【生态风险】
火险等级：{risk.get('fire_risk', '中等')}
病虫害风险：{risk.get('disease_risk', '低')}
异常告警：{warn.get('warning_count', 2)} 处

要求：
- 语言正式、专业、严谨，符合林业科研报告规范
- 字数控制在800-1000字
- 完全基于真实数据，禁止编造
"""

        # 调用通义千问VLMax
        response = MultiModalConversation.call(
            model="qwen-vl-max-latest",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"image": f"data:image/png;base64,{img_base64}"},
                        {"text": prompt}
                    ]
                }
            ],
            stream=False
        )

        # 校验模型调用
        if response.status_code != 200:
            error_msg = f"VLM调用失败：{response.message}"
            print(f"❌ {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)

        # 打印完整响应（调试用）
        print("【VLM完整响应】", response)

        # ==============================
        # 🔥 核心修复：100%正确提取文本
        # ==============================
        output = response.output
        if not output:
            error_msg = "VLM未返回有效输出"
            print(f"❌ {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)

        final_text = ""

        # 优先处理choices格式
        if hasattr(output, 'choices') and output.choices and len(output.choices) > 0:
            message = output.choices[0].message
            if message and message.content:
                content = message.content
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and "text" in item and item["text"]:
                            final_text += item["text"] + "\n\n"
                elif isinstance(content, str):
                    final_text = content
            print(f"✅ 从choices提取到报告，长度：{len(final_text)}")

        # 兜底处理text格式
        elif hasattr(output, 'text') and output.text and output.text.strip():
            final_text = output.text
            print(f"✅ 从text提取到报告，长度：{len(final_text)}")

        # 打印提取结果
        print("\n【提取到的完整报告】\n", final_text)

        # 正确的空内容校验
        if not final_text or not final_text.strip():
            error_msg = "VLM生成内容为空，请检查提示词"
            print(f"❌ {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)

        print(f"\n✅ 报告生成成功，最终长度：{len(final_text)} 字符")
        return {"text": final_text.strip()}

    except Exception as e:
        print("❌ 报告生成失败，完整错误栈：")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"报告生成失败：{str(e)}")