<template>
  <div class="data-search-page">
    <!-- 新增：右上角悬浮图层控制面板 -->
    <div class="layer-panel" :class="{ expanded: isLayerPanelExpanded }">
      <button class="layer-toggle-btn" @click="toggleLayerPanel">
        <i class="fas" :class="isLayerPanelExpanded ? 'fa-times' : 'fa-layer-group'"></i>
        {{ isLayerPanelExpanded ? '收起' : '视图控制' }}
      </button>
      <div class="layer-content" v-show="isLayerPanelExpanded">
        <h4 class="section-title">数据图层</h4>
        <div class="layer-options">
          <label class="layer-label">
            <input type="checkbox" v-model="localLayerStates.biomassHeatmap" @change="handleLayerChange('biomassHeatmap')" /> 
            生物量热力图
          </label>
          <label class="layer-label">
            <input type="checkbox" v-model="localLayerStates.mangroveBoundary" @change="handleLayerChange('mangroveBoundary')"/> 
            分布边界
          </label>
          <label class="layer-label">
            <input type="checkbox" v-model="localLayerStates.samplePoints" @change="handleLayerChange('samplePoints')"/> 
            采样点位置
          </label>
        </div>
      </div>
    </div>
    <!-- 原左侧侧边栏 -->
    <div class="sidebar" :class="{ collapsed: isSidebarCollapsed }">
      <div class="sidebar-header">
        <h3>数据操作面板</h3>
        <button class="collapse-btn" @click="toggleSidebar">
          {{ isSidebarCollapsed ? '展开' : '收起' }}
        </button>
      </div>

      <div class="sidebar-content" v-show="!isSidebarCollapsed">

        <!-- 检索区域 -->
        <div class="sidebar-section">
          <h4 class="section-title">检索区域</h4>
          <div class="region-options">
            <label class="option-item">
              <input type="radio" v-model="regionMode" value="input" />
              <span class="option-text">请输入要检索的区域</span>
            </label>
            <label class="option-item">
              <input type="radio" v-model="regionMode" value="select" />
              <span class="option-text">请选择行政区</span>
              <select class="region-select" v-if="regionMode === 'select'">
                <option value="heilongjiang">黑龙江省</option>
                <option value="guangdong">广东省</option>
                <option value="hainan">海南省</option>
              </select>
            </label>

            <div class="option-item-wrapper" :class="{ active: regionMode === 'draw' }">
              <!-- 头部：单选框 + 标题 (保持高度与其他选项一致) -->
              <label class="option-item draw-header" @click.prevent="regionMode = 'draw'">
                <input type="radio" v-model="regionMode" value="draw" />
                <span class="option-text">
                  <i class="fas fa-paint-brush option-icon-small"></i> 圈选区域
                </span>
              </label>
              
              <!-- 下部：绘图工具按钮 (仅在选中时显示) -->
              <div class="draw-tools-container" v-show="regionMode === 'draw'">
                <div class="draw-buttons">
                  <button 
                    class="draw-btn" 
                    :class="{ active: currentDrawType === 'polygon' }"
                    @click.stop="startDraw('polygon')"
                  >
                    <i class="fas fa-draw-polygon"></i> 多边形
                  </button>
                  <button 
                    class="draw-btn" 
                    :class="{ active: currentDrawType === 'rectangle' }"
                    @click.stop="startDraw('rectangle')"
                  >
                    <i class="fas fa-square"></i> 矩形
                  </button>
                  <button 
                    class="draw-btn" 
                    :class="{ active: currentDrawType === 'circle' }"
                    @click.stop="startDraw('circle')"
                  >
                    <i class="fas fa-circle"></i> 圆形
                  </button>
                  <button 
                    class="draw-btn btn-clear" 
                    @click.stop="clearAllDrawings"
                  >
                    <i class="fas fa-trash"></i> 清空
                  </button>
                </div>
              </div>
            </div>
            </div>
            <!-- 独立的上传文件按钮 -->
          <div class="upload-btn-wrapper" style="margin-top: 12px;">
            <button class="upload-btn" @click="handleUploadClick">
              <i class="fas fa-upload"></i> 上传文件
              <span class="upload-desc">上传矢量文件进行检索</span>
            </button>
          </div>
        </div>
        
        <!-- 采集时间 -->
        <div class="sidebar-section">
          <h4 class="section-title">采集时间</h4>
          <div class="time-range-horizontal">
            <div class="time-item">
              <span class="time-item-label">开始日期</span>
              <div class="time-item-input-wrapper" ref="startWrapperRef">
                <input 
                  type="text" 
                  v-model="formattedStartDate" 
                  class="time-item-input" 
                  placeholder="YYYY/MM/DD"
                  readonly
                  @click="toggleDatePicker('start')"
                />
             
                <input 
                  v-if="activePicker === 'start'"
                  ref="startRealPickerRef"
                  type="date" 
                  v-model="startDate" 
                  class="real-date-picker"
                  @change="handleDateChange('start')"
                  @blur="closeDatePicker"
                />
              </div>
            </div>
            <span class="time-separator">→</span>
            <div class="time-item">
              <span class="time-item-label">结束日期</span>
              <div class="time-item-input-wrapper" ref="endWrapperRef">
                <input 
                  type="text" 
                  v-model="formattedEndDate" 
                  class="time-item-input" 
                  placeholder="YYYY/MM/DD"
                  readonly
                  @click="toggleDatePicker('end')"
                />
            
                <input 
                  v-if="activePicker === 'end'"
                  ref="endRealPickerRef"
                  type="date" 
                  v-model="endDate" 
                  class="real-date-picker"
                  @change="handleDateChange('end')"
                  @blur="closeDatePicker"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 合并后的操作按钮区：重置、引用、检索、保存 -->
      <div class="sidebar-actions" v-show="!isSidebarCollapsed">
        <button class="action-btn reset" @click="handleReset">重置</button>
        <button class="action-btn quote" @click="handleQuote">引用</button>
        <button class="action-btn quote" @click="handleSearch">检索</button>
        <button class="action-btn save" @click="handleSaveData"
          :disabled="!drawnEntities.length && !uploadedLayerName"
        >
          <i class="fas fa-save"></i> 保存
        </button>
      </div>
    </div>

    <!-- 原右侧 Cesium 容器 -->
    <div class="cesium-wrapper">
      <CesiumViewer ref="cesiumViewerRef" :is-flat-mode="isFlatMode"/>
    </div>
  </div>

  <!-- 新增：文件上传隐藏input -->
<input ref="fileInputRef" type="file" accept=".geojson,.shp,.zip,.kml,.csv,.xlsx" class="hidden-file-input" @change="handleFileUpload" />
  
  <!-- 新增：保存数据弹窗 -->
  <div class="modal" v-if="showSaveModal">
    <div class="modal-content">
      <h3>保存数据集</h3>
      <div class="form-item">
        <label>数据集名称</label>
        <input 
          v-model="saveForm.name" 
          type="text" 
          placeholder="请输入数据集名称"
          required
        />
      </div>
      <div class="form-item">
        <label>描述</label>
        <textarea 
          v-model="saveForm.description" 
          placeholder="请输入数据集描述（可选）"
        ></textarea>
      </div>
      <div class="modal-actions">
        <button @click="confirmSave">确认保存</button>
        <button @click="showSaveModal = false">取消</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted ,onUnmounted, nextTick} from 'vue'
import CesiumViewer from '../../components/CesiumViewer.vue'
import * as Cesium from 'cesium'
import { useDataStore } from '../../store/dataStore'
import { ElMessage} from 'element-plus'
import shp from 'shpjs'
import proj4 from 'proj4'; // 引入投影转换库
import { useRouter, useRoute } from 'vue-router'
import * as XLSX from 'xlsx'
import { DOMParser } from 'xmldom'
import { kml } from '@tmcw/togeojson'
import Papa from 'papaparse'

export interface CesiumChildInstance {
  viewer: Cesium.Viewer | undefined;
  layerStates: {
    biomassHeatmap: boolean;
    mangroveBoundary: boolean;
    samplePoints: boolean;
  };
  selectedYear: number;
  selectedRegion: string;
  flyTo: (position: { lon: number; lat: number; height: number; pitch: number }) => void;
  toggleLayer: (layer: string) => Promise<void>;
  loadMaoershanBoundary: () => Promise<void>;
  loadBiomassHeatmap: () => Promise<void>;
  loadSamplePoints: () => Promise<void>;
  addTiandituImage: () => void;
  addTiandituLabel: () => void;
  addTiandituVector: () => void;
  addTerrain: () => Promise<void>;
  loadCustomVectorLayer: (geoJson: any, layerName: string, color: Cesium.Color) => Promise<Cesium.GeoJsonDataSource>;
  removeCustomVectorLayer: (layerName: string) => void;
  loadPredictedBiomassHeatmap: (tifUrl?: string) => Promise<void>
}

const router = useRouter()
const route = useRoute()
// 初始化数据存储
const dataStore = useDataStore()

// 新增响应式变量
const fileInputRef = ref<HTMLInputElement | null>(null)
const uploadedLayerName = ref('') // 已上传的图层名称
const showSaveModal = ref(false)
const saveForm = ref({
  name: '',
  description: ''
})
const startWrapperRef = ref<HTMLElement | null>(null)
const endWrapperRef = ref<HTMLElement | null>(null)
const startRealPickerRef = ref<HTMLInputElement | null>(null)
const endRealPickerRef = ref<HTMLInputElement | null>(null)

// 修改状态变量：用一个变量控制当前激活的是哪个 picker
const activePicker = ref<'start' | 'end' | null>(null)

// 修正 cesiumViewerRef 的类型：
const cesiumViewerRef = ref<CesiumChildInstance | null>(null)

const isSidebarCollapsed = ref(false)
const isLayerPanelExpanded = ref(false)
const regionMode = ref('draw')

const startDate = ref('2023-01-01')
const endDate = ref('2023-12-31')
const formattedStartDate = ref('2023/01/01')
const formattedEndDate = ref('2023/12/31')
const showStartDatePicker = ref(false)
const showEndDatePicker = ref(false)
const isFlatMode = ref(false)

// 绘画相关变量 - 替换为 Cesium 原生实现
const currentDrawType = ref<'polygon' | 'rectangle' | 'circle' | ''>('')
const drawnEntities = ref<Cesium.Entity[]>([])
let handler: Cesium.ScreenSpaceEventHandler | null = null
let tempEntity: Cesium.Entity | null = null
let drawPoints: Cesium.Entity[] = [] //点击加点

const localLayerStates = reactive({
  biomassHeatmap: false,
  mangroveBoundary: false,
  samplePoints: false,
})

const regionPositions = {
  full: { lon: 127.5, lat: 45.4, height: 90000, pitch: -90 },
}

// 新增：切换日期选择器
const toggleDatePicker = async (type: 'start' | 'end') => {
  // 如果点击的是当前已打开的，则关闭
  if (activePicker.value === type) {
    activePicker.value = null
    return
  }
  
  // 打开新的
  activePicker.value = type
  
  // 等待 DOM 更新后，尝试聚焦或触发选择器
  await nextTick()
  
  const pickerRef = type === 'start' ? startRealPickerRef.value : endRealPickerRef.value
  if (pickerRef) {
    // 现代浏览器支持 showPicker() API，可以强制弹出日历
    if (typeof pickerRef.showPicker === 'function') {
      try {
        pickerRef.showPicker()
        return
      } catch (e) {
        // 如果不支持或失败，至少聚焦它
        console.warn('showPicker not supported or failed', e)
      }
    } 
    pickerRef.focus()
    
  }
}

// 新增：关闭选择器
const closeDatePicker = () => {
  activePicker.value = null
}

// 修改：统一的日期变化处理
const handleDateChange = (type: 'start' | 'end') => {
  if (type === 'start') {
    formatStartDate()
  } else {
    formatEndDate()
  }
  // 选择后自动关闭
  activePicker.value = null
}


// 初始化绘图工具（原生 Cesium 无需初始化第三方库）
const initDrawTool = () => {}

// 开始绘制（Cesium 原生实现）
const startDraw = (type: 'polygon' | 'rectangle' | 'circle') => {
  // 第一步：获取真正的 Cesium Viewer 实例（替换原来的 cesiumViewerRef.value?.viewer）
  const viewer = cesiumViewerRef.value?.viewer
  if (!viewer) {
    console.error('❌ 找不到 Cesium Viewer 实例！')
    return
  }
  
  stopDraw()
  currentDrawType.value = type

  // 新增：禁用 Cesium 默认左键事件，防止冲突
  viewer.cesiumWidget.screenSpaceEventHandler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_CLICK)
  viewer.cesiumWidget.screenSpaceEventHandler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_DOWN)
  viewer.cesiumWidget.screenSpaceEventHandler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_UP)
  viewer.cesiumWidget.screenSpaceEventHandler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_DOUBLE_CLICK)

  handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas)
  // 多边形绘制
  if (type === 'polygon') {
    const positions: Cesium.Cartesian3[] = []
    let isDrawingComplete = false
    
    // 左键点击添加点
    handler.setInputAction((click: Cesium.ScreenSpaceEventHandler.PositionedEvent) => {
      const ray = viewer.camera.getPickRay(click.position)
      const position = ray ? viewer.scene.globe.pick(ray, viewer.scene) : viewer.camera.pickEllipsoid(click.position)
      if (position) {
        positions.push(position)
        
        // 新增：添加明显的点标记（红色大圆点）
        const pointEntity = viewer.entities.add({
          position: position,
          point: {
            pixelSize: 10, // 点大小（可调整）
            color: Cesium.Color.RED, // 点颜色
            outlineColor: Cesium.Color.RED, // 点描边
            outlineWidth: 2, // 描边宽度
            heightReference: Cesium.HeightReference.CLAMP_TO_GROUND, // 贴地显示
            disableDepthTestDistance: Number.POSITIVE_INFINITY
          }
        })
        drawPoints.push(pointEntity) // 存入点数组，方便后续清理

        // 实时预览（优化逻辑）
        if (positions.length === 2) {
          // 当只有2个点时，渲染一条线，而不是尝试渲染多边形
          if (tempEntity) viewer.entities.remove(tempEntity)
          tempEntity = viewer.entities.add({
            polyline: {
              positions: positions,
              width: 3,
              material: Cesium.Color.RED.withAlpha(0.8),
              clampToGround: true
            }
          })
        } else if (positions.length > 2) {
          // 当有3个及以上点时，再渲染多边形
          if (tempEntity) viewer.entities.remove(tempEntity)
          tempEntity = viewer.entities.add({
            polygon: {
              hierarchy: new Cesium.PolygonHierarchy(positions),
              material: Cesium.Color.RED.withAlpha(0.2),
              outline: true,
              outlineColor: Cesium.Color.RED,
              outlineWidth: 2,
              // 可选：添加 perPositionHeight 以确保高度正确
              perPositionHeight: true
            }
          })
        }
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK)

   // 双击结束绘制
    handler.setInputAction(() => {
      if (isDrawingComplete) return
      if (tempEntity && positions.length > 2) {
        isDrawingComplete = true;
        viewer.entities.remove(tempEntity)
        const finalEntity = viewer.entities.add({
          polygon: {
            hierarchy: new Cesium.PolygonHierarchy(positions),
            material: Cesium.Color.RED.withAlpha(0.2),
            outline: true,
            outlineColor: Cesium.Color.RED,
            outlineWidth: 2,
          }
        })
        drawnEntities.value.push(finalEntity)
        drawPoints.forEach(point => viewer.entities.remove(point))
        drawPoints = []
        currentDrawType.value = '' // 只在绘制完成后清空
      }
      stopDraw()
    }, Cesium.ScreenSpaceEventType.LEFT_DOUBLE_CLICK)
  } 
  // 矩形绘制
  else if (type === 'rectangle') {
    let startPosition: Cesium.Cartesian3 | null = null
    
    // 左键按下确定起点
  handler.setInputAction((click: Cesium.ScreenSpaceEventHandler.PositionedEvent) => {
  const ray = viewer.camera.getPickRay(click.position)
  const picked = ray ? viewer.scene.globe.pick(ray, viewer.scene) : viewer.camera.pickEllipsoid(click.position)
  // 用 ?? null 把 undefined 转为 null
  startPosition = picked ?? null
}, Cesium.ScreenSpaceEventType.LEFT_DOWN)

    // 鼠标移动预览矩形
handler.setInputAction((move: Cesium.ScreenSpaceEventHandler.MotionEvent) => {
  if (startPosition) {
    const endPosition = viewer.camera.pickEllipsoid(move.endPosition, viewer.scene.globe.ellipsoid)
    if (endPosition) { // 确保 endPosition 存在
      if (tempEntity) viewer.entities.remove(tempEntity)
      tempEntity = viewer.entities.add({
        rectangle: {
          coordinates: Cesium.Rectangle.fromCartesianArray([startPosition, endPosition]),
          material: Cesium.Color.BLUE.withAlpha(0.2),
          outline: true,
          outlineColor: Cesium.Color.BLUE,
          outlineWidth: 2
        }
      })
    }
  }
}, Cesium.ScreenSpaceEventType.MOUSE_MOVE)

    // 左键抬起结束绘制
    handler.setInputAction(() => {
      if (tempEntity) {
        viewer.entities.remove(tempEntity)
        const finalEntity = viewer.entities.add({
          rectangle: {
            coordinates: tempEntity.rectangle!.coordinates,
            material: Cesium.Color.BLUE.withAlpha(0.2),
            outline: true,
            outlineColor: Cesium.Color.BLUE,
            outlineWidth: 2,
          }
        })
        drawnEntities.value.push(finalEntity)
        currentDrawType.value = '' // 只在绘制完成后清空
      }
      stopDraw()
    }, Cesium.ScreenSpaceEventType.LEFT_UP)
  } 
  // 圆形绘制
  else if (type === 'circle') {
    let center: Cesium.Cartesian3 | null = null
    let radius = 0
    let isSettingCenter = true // 新增：标记是否在设置圆心
    // 圆形绘制 - 确定圆心
    handler.setInputAction((click: Cesium.ScreenSpaceEventHandler.PositionedEvent) => {
      const ray = viewer.camera.getPickRay(click.position)
      const picked = ray ? viewer.scene.globe.pick(ray, viewer.scene) : viewer.camera.pickEllipsoid(click.position)
      if (isSettingCenter && picked) {
        // 第一次点击：设圆心
        center = picked as Cesium.Cartesian3
        isSettingCenter = false
      } else if (!isSettingCenter && tempEntity) {
        // 第二次点击：完成绘制
        viewer.entities.remove(tempEntity)
        const finalEntity = viewer.entities.add({
          position: center || undefined,
          ellipse: {
            semiMajorAxis: radius,
            semiMinorAxis: radius,
            material: Cesium.Color.GREEN.withAlpha(0.2),
            outline: true,
            outlineColor: Cesium.Color.GREEN,
            outlineWidth: 2,
          }
        })
        drawnEntities.value.push(finalEntity)
        // 重置状态
        center = null
        radius = 0
        tempEntity = null
        isSettingCenter = true
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK)

    // 鼠标移动预览半径
    handler.setInputAction((move: Cesium.ScreenSpaceEventHandler.MotionEvent) => {
      if (center) {
        const edge = viewer.camera.pickEllipsoid(move.endPosition, viewer.scene.globe.ellipsoid)
        if (edge) {
          const radius = Cesium.Cartesian3.distance(center, edge)
          if (tempEntity) viewer.entities.remove(tempEntity)
          tempEntity = viewer.entities.add({
            position: center,
            ellipse: {
              semiMajorAxis: radius,
              semiMinorAxis: radius,
              material: Cesium.Color.GREEN.withAlpha(0.2),
              outline: true,
              outlineColor: Cesium.Color.GREEN,
              outlineWidth: 2,
            }
          })
        }
      }
    }, Cesium.ScreenSpaceEventType.MOUSE_MOVE)

    // 再次点击结束绘制
    handler.setInputAction(() => {
      if (tempEntity) {
        viewer.entities.remove(tempEntity)
        const finalEntity = viewer.entities.add({
          position: tempEntity.position,
          ellipse: {
            semiMajorAxis: tempEntity.ellipse!.semiMajorAxis,
            semiMinorAxis: tempEntity.ellipse!.semiMinorAxis,
            material: Cesium.Color.GREEN.withAlpha(0.2),
            outline: true,
            outlineColor: Cesium.Color.GREEN,
            outlineWidth: 2,
          }
        })
        drawnEntities.value.push(finalEntity)
        currentDrawType.value = '' // 只在绘制完成后清空
      }
      stopDraw()
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK)
  }
}

// 停止绘制
const stopDraw = () => {
  if (handler) {
    handler.destroy()
    handler = null
  }
  if (tempEntity && cesiumViewerRef.value?.viewer) {
    cesiumViewerRef.value.viewer.entities.remove(tempEntity)
    tempEntity = null
  }
  // 新增：清理绘制点标记
  if (cesiumViewerRef.value?.viewer) {
    const viewer = cesiumViewerRef.value.viewer;
    if (tempEntity) {
      viewer.entities.remove(tempEntity);
      tempEntity = null;
    }
    // 清理绘制点标记
    drawPoints.forEach(point => viewer.entities.remove(point));
    drawPoints = [];
  }
}

// 清空所有绘图
const clearAllDrawings = () => {
  // 先判断 cesiumViewerRef.value 和 viewer 都存在
  if (cesiumViewerRef.value?.viewer) {
    const viewer = cesiumViewerRef.value.viewer;
    // 现在可以安全访问 viewer.entities
    drawnEntities.value.forEach(entity => {
      viewer.entities.remove(entity);
    });
    drawnEntities.value = [];
    drawPoints.forEach(point => viewer.entities.remove(point))
    if (tempEntity) viewer.entities.remove(tempEntity)
    tempEntity = null
    currentDrawType.value = '';
  }
}

// 处理上传文件按钮点击
const handleUploadClick = () => {
  stopDraw()
  regionMode.value = 'upload'
  fileInputRef.value?.click() // 触发文件选择框
}

// 处理文件上传 (更新版)
const handleFileUpload = async (e: Event) => {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  try {
    console.log("🔍 开始处理文件:", file.name, "类型:", file.type);
    let geoJson: any
    const fileName = file.name
    uploadedLayerName.value = fileName

    // 1. 处理 GeoJSON 文件
    if (fileName.endsWith('.geojson') || fileName.endsWith('.json')) {
      const text = await file.text();
      geoJson = JSON.parse(text);
      // 核心修复：处理非WGS84坐标系
      geoJson = await convertGeoJsonToWGS84(geoJson);
    }

    // 2. 处理 SHP 文件（ZIP包）
    else if (fileName.endsWith('.zip') || fileName.endsWith('.shp')) {
      const arrayBuffer = await file.arrayBuffer();
      geoJson = await shp(arrayBuffer);
      // SHP 可能包含投影，这里简单处理，复杂的需后端支持
    }

    // 3. 处理 KML 文件
    else if (fileName.endsWith('.kml')) {
      const text = await file.text();
      const kmlDoc = new DOMParser().parseFromString(text)
      geoJson = kml(kmlDoc)
      
    }

    // 4. 处理 Excel 文件 (.xlsx)
    else if (fileName.endsWith('.xlsx')) {
      const data = await file.arrayBuffer()
      const workbook = XLSX.read(data)

      if (workbook.SheetNames.length === 0) {
        ElMessage.warning('Excel 文件为空，没有工作表')
        return
      }

      const firstSheetName = workbook.SheetNames[0]!
      const worksheet = workbook.Sheets[firstSheetName]
      // 转为 JSON 数组
      const jsonData = XLSX.utils.sheet_to_json(worksheet!)

      const points = jsonData.map((row: any) => {
        // 尝试匹配常见的经纬度列名
        const lon = row['经度'] || row['longitude'] || row['lng'] || row['lon']
        const lat = row['纬度'] || row['latitude'] || row['lat']
        if (lon && lat) {
          return {
            type: 'Feature',
            properties: row,
            geometry: {
              type: 'Point',
              coordinates: [parseFloat(lon), parseFloat(lat)]
            }
          }
        }
        return null
      }).filter((item: any) => item !== null)

      geoJson = { type: 'FeatureCollection', features: points }
    }

    // 5. 处理 CSV 文件
    else if (fileName.endsWith('.csv')) {
      const text = await file.text();
      const result = Papa.parse(text, { header: true, skipEmptyLines: true })
      
      const points = result.data.map((row: any) => {
        // 尝试匹配常见的经纬度列名
        const lon = row['经度'] || row['longitude'] || row['lng'] || row['lon']
        const lat = row['纬度'] || row['latitude'] || row['lat']
        if (lon && lat) {
          return {
            type: 'Feature',
            properties: row,
            geometry: {
              type: 'Point',
              coordinates: [parseFloat(lon), parseFloat(lat)]
            }
          }
        }
        return null
      }).filter((item: any) => item !== null)

      geoJson = { type: 'FeatureCollection', features: points }
    }

    // 6. 不支持的格式
    else {
      ElMessage.error({ message: '仅支持 GeoJSON, SHP, KML, XLSX, CSV 格式', zIndex: 10001 });
      return;
    }

    // 7. 加载到 Cesium (通用逻辑)
    if (cesiumViewerRef.value && geoJson.features && geoJson.features.length > 0) {
      console.log("🔍 调用 cesiumViewerRef.loadCustomVectorLayer...", geoJson);
      await cesiumViewerRef.value.loadCustomVectorLayer(
        geoJson,
        fileName,
        Cesium.Color.BLUE
      );
      ElMessage.success({ message: `文件 ${fileName} 上传并加载成功`, zIndex: 10001 });
    } else {
      ElMessage.warning({ message: '文件解析成功，但未找到有效数据', zIndex: 10001 });
    }

    // 清空文件选择框
    target.value = '';
    
  } catch (error) {
    console.error("❌ 文件上传失败，详细错误堆栈:", error);
    ElMessage.error({ message: `文件上传失败: ${(error as Error).message}`, zIndex: 10001 });
    target.value = '';
  }
}

// 处理保存数据
const handleSaveData = () => {
  saveForm.value = {
    name: '',
    description: ''
  }
  showSaveModal.value = true
}

// 确认保存
const confirmSave = () => {
  if (!saveForm.value.name) {
    ElMessage.warning({message:'请输入数据集名称',  zIndex: 10001 });
    return
  }

  let geoJson: any = null
  let dataType: 'upload' | 'draw' = 'draw'
  let layerName = ''

  // 处理绘制的区域
  if (drawnEntities.value.length) {
    dataType = 'draw'
    layerName = `绘制区域_${Date.now()}`
    
    // 将Cesium实体转换为GeoJSON
    geoJson = {
      type: 'FeatureCollection',
      features: drawnEntities.value.map((entity, idx) => {
        let geometry: any = {}
        
        if (entity.polygon) {
          const positions = entity.polygon.hierarchy?.getValue(Cesium.JulianDate.now())?.positions
          if (positions) {
            geometry = {
              type: 'Polygon',
              coordinates: [positions.map((pos: Cesium.Cartesian3) => {
                const cartographic = Cesium.Cartographic.fromCartesian(pos)
                return [
                  Cesium.Math.toDegrees(cartographic.longitude),
                  Cesium.Math.toDegrees(cartographic.latitude)
                ]
              })]
            }
          }
        } else if (entity.rectangle) {
          const rect = entity.rectangle.coordinates?.getValue(Cesium.JulianDate.now())
          if (rect) {
            geometry = {
              type: 'Polygon',
              coordinates: [[
                [Cesium.Math.toDegrees(rect.west), Cesium.Math.toDegrees(rect.south)],
                [Cesium.Math.toDegrees(rect.east), Cesium.Math.toDegrees(rect.south)],
                [Cesium.Math.toDegrees(rect.east), Cesium.Math.toDegrees(rect.north)],
                [Cesium.Math.toDegrees(rect.west), Cesium.Math.toDegrees(rect.north)],
                [Cesium.Math.toDegrees(rect.west), Cesium.Math.toDegrees(rect.south)]
              ]]
            }
          }
        } else if (entity.ellipse) {
          // 简化处理：圆转为多边形
          const center = entity.position?.getValue(Cesium.JulianDate.now())
          const radius = entity.ellipse.semiMajorAxis?.getValue(Cesium.JulianDate.now())
          if (center && radius) {
            const cartographic = Cesium.Cartographic.fromCartesian(center)
            const centerLon = Cesium.Math.toDegrees(cartographic.longitude)
            const centerLat = Cesium.Math.toDegrees(cartographic.latitude)
            
            // 生成圆形多边形坐标
            const coordinates = []
            for (let i = 0; i < 36; i++) {
              const angle = Cesium.Math.toRadians(i * 10)
              const dest = Cesium.Cartesian3.fromDegrees(
                centerLon + (radius / 111000) * Math.cos(angle),
                centerLat + (radius / 111000) * Math.sin(angle)
              )
              const destCartographic = Cesium.Cartographic.fromCartesian(dest)
              coordinates.push([
                Cesium.Math.toDegrees(destCartographic.longitude),
                Cesium.Math.toDegrees(destCartographic.latitude)
              ])
            }
            coordinates.push(coordinates[0]) // 闭合
            
            geometry = {
              type: 'Polygon',
              coordinates: [coordinates]
            }
          }
        }

        return {
          type: 'Feature',
          properties: {
            id: idx,
            name: saveForm.value.name
          },
          geometry
        }
      })
    }
  } 
  // 处理上传的图层
  else if (uploadedLayerName.value) {
    dataType = 'upload'
    layerName = uploadedLayerName.value
    // 这里需要从Cesium获取上传的GeoJSON数据
    // 简化处理：实际项目中需要存储原始GeoJSON
    geoJson = {
      type: 'FeatureCollection',
      features: [],
      metadata: {
        source: uploadedLayerName.value
      }
    }
  }

  if (!geoJson) {
    ElMessage.error({
    message: '仅支持GeoJSON和SHP(ZIP)格式',
    zIndex: 10001
    });
    return
  }

  // 保存到Pinia
  const datasetId = dataStore.addDataset({
    name: saveForm.value.name,
    type: dataType,
    layerName,
    geoJson,
    description: saveForm.value.description
  })

  ElMessage.success({message:`数据集 "${saveForm.value.name}" 保存成功 (ID: ${datasetId})`,  zIndex: 10001 });
  showSaveModal.value = false
}

// 获取绘制坐标
const getDrawCoordinates = (entity: Cesium.Entity, type: string) => {
  const ellipsoid = Cesium.Ellipsoid.WGS84
  switch (type) {
    // 获取绘制坐标 - 多边形
case 'polygon':
  const hierarchy = entity.polygon?.hierarchy?.getValue(Cesium.JulianDate.now())
  return hierarchy?.positions?.map((pos: Cesium.Cartesian3) => {
    const cartographic = ellipsoid.cartesianToCartographic(pos)
    return cartographic ? [
      Cesium.Math.toDegrees(cartographic.longitude),
      Cesium.Math.toDegrees(cartographic.latitude)
    ] : []
  }) || []
    // 获取绘制坐标 - 矩形
case 'rectangle':
  const rect = entity.rectangle?.coordinates?.getValue(Cesium.JulianDate.now())
  if (rect) {
    return [
      [Cesium.Math.toDegrees(rect.west), Cesium.Math.toDegrees(rect.south)],
      [Cesium.Math.toDegrees(rect.east), Cesium.Math.toDegrees(rect.south)],
      [Cesium.Math.toDegrees(rect.east), Cesium.Math.toDegrees(rect.north)],
      [Cesium.Math.toDegrees(rect.west), Cesium.Math.toDegrees(rect.north)]
    ]
  }
  return []
    case 'circle':
      const centerPos = entity.position?.getValue(Cesium.JulianDate.now()) as Cesium.Cartesian3 | undefined
      if (centerPos && entity.ellipse) {
        const center = ellipsoid.cartesianToCartographic(centerPos)
        if (center) {
          return {
            center: [
              Cesium.Math.toDegrees(center.longitude),
              Cesium.Math.toDegrees(center.latitude)
            ],
            radius: entity.ellipse.semiMajorAxis
          }
        }
      }
      return null
    default:
      return null
  }
}

const toggleSidebar = () => {
  isSidebarCollapsed.value = !isSidebarCollapsed.value
}

const formatStartDate = () => {
  if (!startDate.value) {
    formattedStartDate.value = ''
    return
  }
  
  // 直接分割字符串 "YYYY-MM-DD" -> "YYYY/MM/DD"
  // 这样既避免了 new Date() 的时区问题，也避免了 toISOString 的类型报错
  const parts = startDate.value.split('-')
  if (parts.length === 3) {
    formattedStartDate.value = `${parts[0]}/${parts[1]}/${parts[2]}`
  } else {
    // 如果格式不对，清空
    formattedStartDate.value = ''
  }
}

const formatEndDate = () => {
  if (!endDate.value) {
    formattedEndDate.value = ''
    return
  }

  // 同上，直接处理字符串
  const parts = endDate.value.split('-')
  if (parts.length === 3) {
    formattedEndDate.value = `${parts[0]}/${parts[1]}/${parts[2]}`
  } else {
    formattedEndDate.value = ''
  }
}

const handleReset = () => {
  startDate.value = '2023-01-01'
  endDate.value = '2023-12-31'
  formattedStartDate.value = '2023/01/01'
  formattedEndDate.value = '2023/12/31'
  regionMode.value = 'draw'
  showStartDatePicker.value = false
  showEndDatePicker.value = false
  activePicker.value = null
  console.log('已重置检索条件')
}

const handleQuote = () => {
  console.log('复用上次检索条件')
}

const handleSearch = () => {
  console.log('开始检索:', {
    regionMode: regionMode.value,
    startDate: startDate.value,
    endDate: endDate.value,
    drawnRegions: drawnEntities.value.map((entity, idx) => 
      getDrawCoordinates(entity, currentDrawType.value || 'polygon')
    )
  })
}

const toggleLayerPanel = () =>{
  isLayerPanelExpanded.value = !isLayerPanelExpanded.value
}

// 新增：GeoJSON 坐标系转换核心方法（EPSG:32651 → EPSG:4326）
const convertGeoJsonToWGS84 = async (geoJson: any) => {
  // 1. 移除 Cesium 不识别的 crs 声明（避免报错）
  if (geoJson.crs) {
    delete geoJson.crs;
  }

  // 2. 定义投影转换规则：EPSG:32651（UTM 51N）→ EPSG:4326（WGS84）
  proj4.defs("EPSG:32651", "+proj=utm +zone=51 +datum=WGS84 +units=m +no_defs");
  proj4.defs("EPSG:4326", "+proj=longlat +datum=WGS84 +no_defs");
  const transform = proj4("EPSG:32651", "EPSG:4326");

  // 3. 递归遍历坐标，实现转换
  const transformCoordinates = (coords: any[]): any[] => {
    // 终止条件：坐标点 [x, y]（EPSG:32651是米，转后是经纬度）
    if (typeof coords[0] === 'number' && typeof coords[1] === 'number') {
      const [lon, lat] = transform.forward([coords[0], coords[1]]);
      return [lon, lat]; // Cesium 要求 [经度, 纬度] 顺序
    }
    // 递归处理嵌套数组（适配 MultiPolygon/Polygon/LineString 等）
    return coords.map(transformCoordinates);
  };

  // 4. 遍历所有要素，转换几何坐标
  if (geoJson.features && Array.isArray(geoJson.features)) {
    geoJson.features = geoJson.features.map((feature: any) => {
      if (feature.geometry && feature.geometry.coordinates) {
        feature.geometry.coordinates = transformCoordinates(feature.geometry.coordinates);
      }
      return feature;
    });
  }

  return geoJson;
};

watch(
  () => cesiumViewerRef.value?.layerStates,
  (newVal) => {
    if (newVal) {
      // 深度拷贝，避免引用问题
      localLayerStates.biomassHeatmap = newVal.biomassHeatmap;
      localLayerStates.mangroveBoundary = newVal.mangroveBoundary;
      localLayerStates.samplePoints = newVal.samplePoints;
    }
  },
  { deep: true, immediate: true }
)

const flyTo = (region: keyof typeof regionPositions) => {
  if (cesiumViewerRef.value) {
    cesiumViewerRef.value.selectedRegion = region
    cesiumViewerRef.value.flyTo(regionPositions[region])
  }
}

watch(cesiumViewerRef, (val) => val && flyTo('full'), { immediate: true })

const handleLayerChange = async (layerName: keyof typeof localLayerStates) => {
  console.log('✅ 手动触发图层切换:', layerName, localLayerStates[layerName]);
  const viewerInstance = cesiumViewerRef.value;
  
  if (!viewerInstance) {
    console.error('❌ 子组件 CesiumViewer 未挂载或引用为空');
    return;
  }

  // 关键修复：先调用子组件的 toggleLayer，由子组件自己管理状态
  await viewerInstance.toggleLayer(layerName);
  
  // 同步子组件状态到父组件（确保勾选框状态正确）
  localLayerStates[layerName] = viewerInstance.layerStates[layerName];
};
const checkLoginStatus = () => {
  const token = localStorage.getItem('token')
  if (!token) {
    ElMessage?.({ type: 'warning', message: '请先登录后再访问', zIndex: 10001 })
    router.push({ path: '/login', query: { redirect: route.fullPath } })
    return false
  }
  try {
    const parts = token.split('.')
    if (parts.length < 2 || !parts[1]) throw new Error('Invalid token')
    const payload = JSON.parse(atob(parts[1]))
    const expTime = payload.exp * 1000
    if (Date.now() > expTime) {
      localStorage.removeItem('token')
      ElMessage?.({ type: 'warning', message: '登录已过期，请重新登录', zIndex: 10001 })
      router.push({ path: '/login', query: { redirect: route.fullPath } })
      return false
    }
  } catch (e) {
    localStorage.removeItem('token')
    router.push('/login')
    return false
  }
  return true
}

onMounted(() => {
  checkLoginStatus()

  formatStartDate()
  formatEndDate()
  const sidebar = document.querySelector('.sidebar')
  sidebar?.addEventListener('wheel', e => e.stopPropagation(), { passive: true })
  // 新增下面这段：等待子组件挂载，获取真正的 Viewer 实例
  nextTick(() => {
    if (cesiumViewerRef.value) {
      // 从 DOM 中兜底获取 Cesium 实例（子组件初始化时挂载到 container 上）
      const cesiumContainer = document.getElementById('cesium-container')
      if (cesiumContainer && !cesiumViewerRef.value.viewer) {
        cesiumViewerRef.value.viewer = (cesiumContainer as any)._cesiumViewer
      }
    }
  })
})

onUnmounted(() => {
  stopDraw()
  clearAllDrawings()
})
</script>

<style scoped>
.data-search-page {
  width: 100%;
  height: 100%;
  display: flex;
  background: #000;
}

/* 侧边栏 - 缩小宽度 */
.sidebar {
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  width: 280px;
  background: rgba(0, 20, 50, 0.95);
  border-radius: 0 12px 12px 0;
  z-index: 999;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  overflow: hidden;
}

.sidebar.collapsed {
  width: 60px;
}

.sidebar-header {
  padding: 15px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-header h3 {
  color: #4fc3f7;
  font-size: 16px;
  margin: 0;
}

.collapse-btn {
  background: transparent;
  border: none;
  color: #4fc3f7;
  cursor: pointer;
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.2s;
}

.collapse-btn:hover {
  background: rgba(79, 195, 247, 0.1);
}

.sidebar-content {
  padding: 16px;
  flex: 1;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(79, 195, 247, 0.3) transparent;
}

.sidebar-content::-webkit-scrollbar {
  width: 6px;
}

.sidebar-content::-webkit-scrollbar-track {
  background: transparent;
}

.sidebar-content::-webkit-scrollbar-thumb {
  background: rgba(79, 195, 247, 0.3);
  border-radius: 3px;
}

.sidebar-section {
  margin-bottom: 24px;
  padding: 14px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.section-title {
  color: #4fc3f7;
  font-size: 14px;
  margin: 0 0 12px 0;
  font-weight: 600;
}

/* ================= 检索区域核心样式修改 ================= */

.region-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* 通用选项项样式 - 确保所有选项基础高度一致 */
.option-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid transparent;
  min-height: 42px; /* 🔥 关键：强制最小高度，确保与带下拉框的选项一致 */
  width: 100%;
  box-sizing: border-box;
  margin: 0;
  user-select: none;
}

.option-item:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(79, 195, 247, 0.3);
}

/* 选中状态高亮 (通过 :has 或父类控制) */
.option-item:has(input:checked) {
  background: rgba(79, 195, 247, 0.15);
  border-color: rgba(79, 195, 247, 0.5);
}

/* 隐藏原生 Radio 但保留功能 */
.option-item input[type="radio"] {
  accent-color: #4fc3f7;
  cursor: pointer;
  margin: 0;
  width: 16px;
  height: 16px;
}

.option-text {
  color: #fff;
  font-size: 13px;
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.option-icon-small {
  color: #4fc3f7;
  font-size: 14px;
  width: 16px;
  text-align: center;
}

/* 🔥 圈选区域专用包装器 */
.option-item-wrapper {
  display: flex;
  flex-direction: column;
  gap: 0;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  border: 1px solid transparent;
  overflow: hidden;
  transition: all 0.3s ease;
}

/* 当圈选被激活时，整个包装器高亮 */
.option-item-wrapper.active {
  background: rgba(79, 195, 247, 0.15);
  border-color: rgba(79, 195, 247, 0.5);
}

/* 圈选区域的头部 (模拟 option-item) */
.draw-header {
  border: none !important;
  background: transparent !important;
  margin: 0;
  border-radius: 6px 6px 0 0;
  min-height: 42px; /* 🔥 保持与兄弟元素高度一致 */
}

.draw-header:hover {
  background: transparent !important;
}

/* 🔥 绘图工具容器 (默认隐藏，选中显示) */
.draw-tools-container {
  padding: 0 12px 12px 34px; /* 左 padding 34px 是为了对齐文字内容，避开 radio 宽度 */
  animation: slideDown 0.3s ease-out;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  margin-top: 2px;
}

@keyframes slideDown {
  from { 
    opacity: 0; 
    transform: translateY(-5px); 
    max-height: 0;
  }
  to { 
    opacity: 1; 
    transform: translateY(0); 
    max-height: 200px;
  }
}

.draw-buttons {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.draw-btn {
  flex: 1;
  min-width: 60px;
  padding: 6px 4px;
  background: rgba(0, 0, 0, 0.3);
  color: #cbd5e1;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  transition: all 0.2s ease;
  line-height: 1.2;
}

.draw-btn i {
  font-size: 14px;
  margin-bottom: 2px;
}

.draw-btn:hover {
  background: rgba(79, 195, 247, 0.2);
  border-color: rgba(79, 195, 247, 0.4);
  color: #fff;
}

.draw-btn.active {
  background: #4fc3f7;
  color: #0f172a;
  border-color: #4fc3f7;
  font-weight: 600;
  box-shadow: 0 0 8px rgba(79, 195, 247, 0.4);
}

.draw-btn.btn-clear {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.3);
}

.draw-btn.btn-clear:hover {
  background: rgba(239, 68, 68, 0.2);
  border-color: rgba(239, 68, 68, 0.5);
  color: #fff;
}

/* 行政区下拉框样式微调 */
.region-select {
  margin-left: auto;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  outline: none;
  cursor: pointer;
  max-width: 100px;
  transition: border-color 0.2s;
}

.region-select:focus {
  border-color: #4fc3f7;
}

/* ================= 上传按钮样式 ================= */

.upload-btn-wrapper {
  width: 100%;
}

.upload-btn {
  width: 100%;
  padding: 10px 14px;
  background: rgba(79, 195, 247, 0.1);
  color: #4fc3f7;
  border: 1px solid rgba(79, 195, 247, 0.2);
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.3s ease;
}

.upload-btn:hover {
  background: rgba(79, 195, 247, 0.2);
  border-color: rgba(79, 195, 247, 0.4);
  transform: translateY(-1px);
}

.upload-btn .upload-desc {
  margin-left: auto;
  font-size: 12px;
  color: #94a3b8;
}

/* ================= 采集时间样式 (已修复) ================= */

.time-range-horizontal {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 14px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.time-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}

.time-item-label {
  font-size: 12px;
  color: #94a3b8;
}

.time-item-input-wrapper {
  position: relative; /* 必须设置为 relative，作为子元素绝对定位的参考 */
  display: flex;
  align-items: center;
  z-index: 100; /* 适度层级，避免干扰内部绝对定位元素的层级计算 */
}

.time-item-input {
  width: 100%;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #fff;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 13px;
  transition: border-color 0.3s ease;
  cursor: pointer;
  caret-color: transparent;
}

.time-item-input:focus {
  border-color: #4fc3f7;
  outline: none;
}

.time-item-icon {
  position: absolute;
  right: 12px;
  top: 50%; /* 垂直居中关键 */
  transform: translateY(-50%); /* 垂直居中关键 */
  background: transparent;
  border: none;
  color: #4fc3f7;
  cursor: pointer;
  font-size: 14px;
  padding: 4px;
  transition: color 0.2s;
  z-index: 2; /* 确保图标在输入框之上 */
}

.time-item-icon:hover {
  color: #6ed7f7;
}

/* 🔥 核心修复：真实的日期选择器样式 */
/* 替代原来的 .hidden-date-picker */
.real-date-picker {
  position: absolute;
  top: 40px;
  left: 0;
  width: 100%;
  height: 100%;
  opacity: 0; /* 完全透明但保留交互能力 */
  cursor: pointer;
  z-index: 999999; /* 极高的层级，确保覆盖 Cesium 和其他元素 */
  pointer-events: auto; /* 确保能接收点击事件 */
  /* 关键：设置与下方 input 一致的字体和颜色，防止某些浏览器渲染异常 */
  font-size: 13px;
  color: transparent; /* 文字透明 */
  background: transparent; /* 背景透明 */
  border: none;
  padding: 0;
  margin: 0;
  
  /* 针对 Webkit 浏览器去除默认样式 */
  -webkit-appearance: none;
  -moz-appearance: none;
  appearance: none;
}

.time-separator {
  color: #4fc3f7;
  font-weight: bold;
  font-size: 18px;
  margin-bottom: 8px;
}
/* 针对 Safari/Chrome 的特殊处理，确保它能被点击 */
.real-date-picker::-webkit-calendar-picker-indicator {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  opacity: 0; /* 连原生的小图标也隐藏，完全靠我们的 icon */
  cursor: pointer;
  background: none;
}

.time-separator {
  color: #4fc3f7;
  font-weight: bold;
  font-size: 18px;
  margin-bottom: 8px;
}
/* ================= 底部操作按钮 ================= */

.sidebar-actions {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  background: rgba(0, 15, 40, 0.95);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  flex-shrink: 0;
  z-index: 5;
}

.action-btn {
  flex: 1;
  padding: 10px 0;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.3s ease;
  font-weight: 500;
  min-height: 40px;
  box-sizing: border-box;
  white-space: nowrap;
}

.reset {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.reset:hover {
  background: rgba(255, 255, 255, 0.15);
}

.quote {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.quote:hover {
  background: rgba(255, 255, 255, 0.15);
}

.search {
  background: #4fc3f7;
  color: #000;
}

.search:hover {
  background: #6ed7f7;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(79, 195, 247, 0.3);
}

.action-btn.save {
  background: #4CAF50;
  color: white;
}

.action-btn.save:hover {
  background: #45a049;
}

.action-btn.save:disabled {
  background: #666;
  cursor: not-allowed;
  opacity: 0.7;
}

/* ================= 右上角图层面板 ================= */

.layer-panel {
  position: absolute;
  top: 90px;
  right: 20px;
  z-index: 1000;
  background: rgba(0, 20, 50, 0.95);
  border-radius: 8px;
  border: 1px solid rgba(79, 195, 247, 0.2);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
  transition: all 0.3s ease;
  min-width: 160px;
}

.layer-toggle-btn {
  width: 100%;
  padding: 8px 12px;
  background: rgba(79, 195, 247, 0.1);
  color: #4fc3f7;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.3s ease;
}

.layer-toggle-btn:hover {
  background: rgba(79, 195, 247, 0.2);
}

.layer-content {
  padding: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.layer-options {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.layer-label {
  display: block;
  color: #fff;
  font-size: 12px;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 4px;
  transition: background 0.2s ease;
  display: flex;
  align-items: center;
}

.layer-label:hover {
  background: rgba(255, 255, 255, 0.05);
}

.layer-label input {
  margin-right: 8px;
  accent-color: #4fc3f7;
  cursor: pointer;
}

.base-layer-controls-inline {
  display: flex;
  gap: 8px;
  margin-top: 14px;
}

.layer-btn-inline {
  flex: 1;
  padding: 8px 0;
  background: rgba(6, 182, 212, 0.8);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 13px;
  font-weight: 500;
}

.layer-btn-inline:hover {
  background: #06b6d4;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(6, 182, 212, 0.3);
}

/* ================= Cesium 容器 ================= */

.cesium-wrapper {
  flex: 1;
  position: relative;
  height: 100%;
  background: #000;
}

.cesium-wrapper :deep(.cesium-viewer-container) {
  width: 100% !important;
  height: 100% !important;
  position: absolute !important;
  top: 0 !important;
  left: 0 !important;
}

/* ================= 其他辅助样式 ================= */

.map-info {
  position: fixed;
  bottom: 10px;
  right: 20px;
  color: #fff;
  font-size: 11px;
  background: rgba(0, 20, 50, 0.8);
  padding: 6px 12px;
  border-radius: 6px;
  z-index: 999;
  border: 1px solid rgba(255, 255, 255, 0.1);
  pointer-events: none;
}

.hidden-file-input {
  position: absolute;
  opacity: 0;
  z-index: -1;
}

/* 模态框样式 */
.modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  backdrop-filter: blur(4px);
}

.modal-content {
  background: #1e293b;
  padding: 24px;
  border-radius: 12px;
  width: 400px;
  color: white;
  border: 1px solid rgba(79, 195, 247, 0.2);
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
}

.modal-content h3 {
  margin: 0 0 20px 0;
  color: #4fc3f7;
  font-size: 18px;
  text-align: center;
}

.form-item {
  margin-bottom: 15px;
}

.form-item label {
  display: block;
  margin-bottom: 8px;
  color: #94a3b8;
  font-size: 13px;
}

.form-item input, 
.form-item textarea {
  width: 100%;
  padding: 10px;
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  color: white;
  font-size: 14px;
  box-sizing: border-box;
  transition: border-color 0.3s;
}

.form-item input:focus, 
.form-item textarea:focus {
  outline: none;
  border-color: #4fc3f7;
}

.form-item textarea {
  resize: vertical;
  min-height: 80px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 24px;
}

.modal-actions button {
  padding: 8px 20px;
  background: #4fc3f7;
  color: #0f172a;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
}

.modal-actions button:hover {
  background: #38bdf8;
  transform: translateY(-1px);
}

.modal-actions button:last-child {
  background: transparent;
  color: #94a3b8;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.modal-actions button:last-child:hover {
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
  transform: none;
}
</style>