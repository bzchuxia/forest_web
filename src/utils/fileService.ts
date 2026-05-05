import { ElMessage } from "element-plus"

/**
 * 下载服务器上的结果文件
 * @param filePath 服务器文件路径（支持：/data/biomass_results/xxx.csv、biomass_results/xxx.joblib、dataset://xxx 格式）
 */
export const downloadFileApi = async (filePath: string) => {
  // 1. 入参校验
  if(!filePath || typeof filePath !== 'string'){
    ElMessage.error('下载失败：路径无效（不能为空或非字符串）')
    return;
  }

  try {
    // 2. 路径标准化处理（核心修复：适配Windows/Linux路径 + 保留biomass_results完整路径）
    let requestPath = filePath
      .replace(/\\/g, '/')          // 统一将Windows反斜杠转为正斜杠
      .replace(/^\/data\//, '')     // 移除开头的 /data/ 前缀（后端BASE_DATA_DIR已包含data）
      .replace(/^\/+/, '');         // 移除开头多余的斜杠
      // 移除 .replace(/^data\//, '')：避免误删 models/ 或 biomass_results/ 前缀

    // 3. 处理dataset://特殊格式
    if (requestPath.startsWith('dataset://')) {
      const datasetId = requestPath.replace('dataset://', '');
      requestPath = `biomass_results/dataset_${datasetId}.csv`;
    }

    // 4. 最终路径校验（防止空路径）
    if (!requestPath) {
      throw new Error('处理后路径为空，请检查原始路径是否正确');
    }

    // 5. 构造请求（优先使用专用接口，避免根接口307重定向）
    let fetchUrl: string
    if (requestPath.startsWith('biomass_results/')) {
      // 优先调用biomass_results专用接口（兼容.csv/.joblib/.geojson等）
      const filename = requestPath.replace('biomass_results/', '')
      fetchUrl = `http://localhost:8000/api/file/biomass_results/${encodeURIComponent(filename)}`;
    } else {
      // 其他文件用根接口（兼容老路径）
      const url = new URL('http://localhost:8000/api/file');
      url.searchParams.set('path', requestPath); // URLSearchParams自动处理编码
      fetchUrl = url.toString();
    }

    // 6. 发起下载请求
    const response = await fetch(fetchUrl, {
      method: 'GET',
      headers: {
        'Accept': 'application/octet-stream',
        'Cache-Control': 'no-cache'
      }
    });

    // 7. 响应状态校验
    if (!response.ok) {
      // 尝试解析后端返回的JSON错误信息
      let errorMsg = `HTTP错误: ${response.status} ${response.statusText}`
      try {
        const errData = await response.json()
        if (errData.detail) errorMsg = errData.detail // 显示后端返回的具体错误（如文件不存在）
      } catch (e) {
        // 非JSON响应（如HTML错误页），用默认提示
      }
      throw new Error(errorMsg);
    }

    // 8. 处理文件下载（适配.joblib文件名）
    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    
    // 提取文件名（优先从响应头获取，兜底用路径最后一段）
    const filenameFromHeader = response.headers.get('Content-Disposition')?.match(/filename\*?=UTF-8''([^;]+)/)?.[1]
    const defaultFilename = requestPath.split('/').pop() || 'biomass_file' // 兜底文件名兼容所有后缀
    link.download = decodeURIComponent(filenameFromHeader || defaultFilename);
    
    link.href = downloadUrl;
    document.body.appendChild(link);
    link.click();

    // 9. 清理资源
    window.URL.revokeObjectURL(downloadUrl);
    document.body.removeChild(link);
    ElMessage.success(`文件 ${link.download} 下载成功`);

  } catch (error) {
    console.error('文件下载失败详情:', error);
    ElMessage.error(`文件下载失败：${(error as Error).message || '未知错误'}`);
  }
}