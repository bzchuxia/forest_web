<template>
  <div ref="cesiumContainer" class="cesium-viewer"></div>
  <div class="map-copyright">
     <div>底图：天地图 © 国家测绘地理信息局</div>
     <div>服务：WMTS 1.0.0 | 坐标系：WGS84</div>
     <div>三维引擎：CesiumJS</div>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as Cesium from 'cesium'
import 'cesium/Build/Cesium/Widgets/widgets.css'

const props = defineProps<{
  viewMode: 'satellite' | 'species' | 'elevation'
}>()

const cesiumContainer = ref<HTMLElement | null>(null)
let viewer: Cesium.Viewer | null = null
let treeEntities: Cesium.Entity[] = []

// 帽儿山坐标
const MAOERSHAN = {
  lon: 127.5100,
  lat: 45.2750,
  height: 350
}

// 颜色配置
const speciesColorMap: Record<string, string> = {
  '红松': '#FF4D4F',
  '落叶松': '#FF7D00',
  '白桦': '#F5F5DC',
  '水曲柳': '#36CFC9',
  '紫椴': '#722ED1'
}

const elevationColorRamp = [
  { max: 350, color: '#36a849' },
  { max: 450, color: '#67c23a' },
  { max: 550, color: '#fadb14' },
  { max: 650, color: '#ff7d00' },
  { max: 9999, color: '#f44336' }
]

// 初始化 Cesium
async function initCesium() {
  if (!cesiumContainer.value) return

  try {
    // 配置 Cesium Ion（使用默认密钥）
    Cesium.Ion.defaultAccessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiI4NDNkOWYyZS0zYjY2LTRiMGEtYTM0ZS0wZTJiODNlMzg5YmYiLCJpZCI6MzgxOTIxLCJpYXQiOjE3NjkwNDY2NDB9.rXB7m-xSmR9HK-E7oTvXCF3XrQfsq5CUhD67Q4BGpnw'
    viewer = new Cesium.Viewer(cesiumContainer.value, {
      timeline: false,
      animation: false,
      baseLayerPicker: false,
      geocoder: false,
      homeButton: false,
      sceneModePicker: false,
      navigationHelpButton: false,
      fullscreenButton: false,
      infoBox: false,
      selectionIndicator: false,
      shouldAnimate: false,
      terrainProvider: await Cesium.createWorldTerrainAsync({
        requestVertexNormals: true,
        requestWaterMask: true
      })
    })

    // 3D场景配置
    viewer.scene.globe.enableLighting = true
    viewer.scene.globe.depthTestAgainstTerrain = true
    viewer.scene.screenSpaceCameraController.minimumZoomDistance = 100
    viewer.scene.fog.enabled = false

    // ========== 新增：调亮画面 ==========
    // 增强方向光
    viewer.scene.light = new Cesium.DirectionalLight({
      direction: new Cesium.Cartesian3(0.5, -0.5, -1.0)
    })
    
    // 提高基础亮度
    viewer.scene.globe.baseColor = Cesium.Color.WHITE
    
    // 调整大气效果
    if (viewer.scene.skyAtmosphere) {
      viewer.scene.skyAtmosphere.show = true
      viewer.scene.skyAtmosphere.brightnessShift = 0.2
      viewer.scene.skyAtmosphere.saturationShift = 0.1
    }
    
    if (viewer.scene.sun) {
      viewer.scene.sun.show = true
    }

    // 创建森林
    await createForest()
    
    // 飞行到帽儿山
    flyToMaoershan()

  } catch (error) {
    console.error('Cesium 初始化失败:', error)
  }
}

// 飞行到帽儿山
function flyToMaoershan() {
  if (!viewer) return
  
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(MAOERSHAN.lon, MAOERSHAN.lat, 2000),
    orientation: {
      heading: Cesium.Math.toRadians(0),
      pitch: Cesium.Math.toRadians(-45),
      roll: 0
    },
    duration: 2,
  })
}

// 创建森林
async function createForest() {
  if (!viewer) return
  
  const count = 500
  
  // 获取所有物种名称数组
  const speciesNames = Object.keys(speciesColorMap)
  
  for (let i = 0; i < count; i++) {
    const lon = MAOERSHAN.lon + (Math.random() - 0.5) * 0.08
    const lat = MAOERSHAN.lat + (Math.random() - 0.5) * 0.08
    
    const carto = Cesium.Cartographic.fromDegrees(lon, lat)
    const positions: Cesium.Cartographic[] = [carto]
    
    try {
      // 修复：确保 terrainProvider 存在
      if (!viewer || !viewer.terrainProvider) {
        console.warn('terrainProvider 未就绪')
        continue
      }
      
      await Cesium.sampleTerrainMostDetailed(viewer.terrainProvider, positions)
      
      // 修复：确保 positions[0] 存在
      const sampledHeight = positions[0]?.height
      if (sampledHeight === undefined) {
        console.warn('无法获取地形高度')
        continue
      }
      
      const h = sampledHeight + 10 + Math.random() * 15
      
      const position = Cesium.Cartesian3.fromDegrees(lon, lat, h)
      
      // 修复：确保随机索引有效
      const randomIndex = Math.floor(Math.random() * speciesNames.length)
      const species = speciesNames[randomIndex]
      
      if (!species) {
        console.warn('无法获取物种名称')
        continue
      }
      
      // 使用圆柱体创建简单的树
      const treeHeight = 10 + Math.random() * 15
      const trunkHeight = treeHeight * 0.3
      const crownHeight = treeHeight * 0.7
      
      // 修复：安全获取物种颜色
      const speciesColorStr = speciesColorMap[species] || '#FFFFFF'
      const speciesColor = Cesium.Color.fromCssColorString(speciesColorStr)
      
      const entity = viewer.entities.add({
        position: position,
        properties: {
          species: species,
          elevation: h
        } as any,
        // 树干
        cylinder: {
          length: trunkHeight,
          topRadius: 0.8,
          bottomRadius: 1.0,
          material: Cesium.Color.SADDLEBROWN as any,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
        } as any,
        // 树冠（使用椭球体）
        ellipsoid: {
          radii: new Cesium.Cartesian3(3.0, 3.0, crownHeight),
          material: speciesColor as any,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
        } as any
      })
      
      treeEntities.push(entity)
      
    } catch (error) {
      console.warn('创建树木失败:', error)
    }
  }
  
  // 添加标注
  addLabels()
  
  // 应用当前视图模式
  switchViewMode(props.viewMode)
}

// 添加标注
function addLabels() {
  if (!viewer) return
  
  viewer.entities.add({
    position: Cesium.Cartesian3.fromDegrees(MAOERSHAN.lon, MAOERSHAN.lat, 500),
    label: {
      text: '帽儿山',
      font: '20px sans-serif',
      fillColor: Cesium.Color.WHITE as any,
      outlineColor: Cesium.Color.BLACK as any,
      outlineWidth: 2,
      style: Cesium.LabelStyle.FILL_AND_OUTLINE as any,
      verticalOrigin: Cesium.VerticalOrigin.BOTTOM as any,
      pixelOffset: new Cesium.Cartesian2(0, -20)
    } as any
  })
}

// 切换视图模式
function switchViewMode(mode: 'satellite' | 'species' | 'elevation') {
  if (!viewer || treeEntities.length === 0) return
  
  treeEntities.forEach(entity => {
    const p = (entity.properties as any)?.getValue(Cesium.JulianDate.now())
    if (!p) return
    
    let color: Cesium.Color
    
    if (mode === 'satellite') {
      color = Cesium.Color.WHITE
    } else if (mode === 'species') {
      // 修复：安全获取物种颜色
      const speciesColorStr = speciesColorMap[p.species] || '#FFFFFF'
      color = Cesium.Color.fromCssColorString(speciesColorStr)
    } else {
      // 海拔颜色
      color = Cesium.Color.WHITE
      for (const item of elevationColorRamp) {
        if (p.elevation <= item.max) {
          color = Cesium.Color.fromCssColorString(item.color)
          break
        }
      }
    }
    
    // 更新树冠颜色
    if (entity.ellipsoid) {
      (entity.ellipsoid as any).material = color
    }
  })
}

// 监听模式切换
watch(() => props.viewMode, (newMode) => {
  switchViewMode(newMode)
})

// 暴露方法
defineExpose({ 
  switchViewMode, 
  flyToMaoershan 
})

onMounted(() => {
  initCesium()
})

onUnmounted(() => {
  if (viewer) {
    viewer.entities.removeAll()
    treeEntities = []
    viewer.destroy()
    viewer = null
  }
})
</script>

<style scoped>
.cesium-viewer {
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 0;
  overflow: hidden;
  position: relative;
}

/* 隐藏 Cesium 版权信息 */
:deep(.cesium-widget-credits) {
  display: none !important;
}

/* 确保 Cesium 容器填满 */
:deep(.cesium-viewer) {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
}

:deep(.cesium-viewer-toolbar) {
  display: none !important;
}
.map-copyright {
  position: absolute;
  right: 12px;
  bottom: 12px;
  z-index: 99999;
  background: rgba(0,0,0,0.65);
  color: #fff;
  padding: 8px 14px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.5;
  pointer-events: none;
}
</style>