<template>
  <div id="cesium-container" v-show="isVisible"></div>
  <div class="map-copyright">
    <div>底图：天地图 © 国家测绘地理信息局</div>
    <div>服务：WMTS 1.0.0 | 坐标系：WGS84</div>
    <div>三维引擎：CesiumJS</div>
  </div>
</template>

<script setup lang="ts">
import * as Cesium from 'cesium'
import proj4  from 'proj4'
import { onMounted, ref, reactive, onUnmounted ,nextTick} from 'vue'
import { getSamplePoints } from '../api/biomass'
import 'cesium/Build/Cesium/Widgets/widgets.css';
import { ElMessage } from 'element-plus'

// 定义投影：EPSG:32651 (UTM 51N) 转 EPSG:4326 (WGS84)
const utm51n = '+proj=utm +zone=51 +datum=WGS84 +units=m +no_defs'
const wgs84 = '+proj=longlat +datum=WGS84 +no_defs'

// 正确定义并使用 Emits
const emit = defineEmits<{
  'area-drawn': [geoJson: any]
}>();

// 接收并监听 isFlatMode Props 
// 1.1 定义Props，接收从父组件传递来的 isFlatMode
const props = defineProps<{
  isFlatMode: boolean;
  predictionTifPath?: string;
}>();

// 全局变量与响应式状态 
let viewer: Cesium.Viewer | null = null
// 新增：记录事件句柄，用于卸载时清理
let postRenderListener: (() => void) | null = null
// 新增：异步操作标识，防止组件卸载后执行异步回调
let isMounted = false

// 新增：自己定义容器显隐状态
const isVisible = ref(true) // 确保默认显示
const selectedYear = ref(2023)
const selectedRegion = ref("full")

// 图层显示状态（供父组件绑定）
const layerStates = reactive({
  biomassHeatmap: false,
  mangroveBoundary: false,
  samplePoints: false,
  tifGeoJsonLayer: false // 新增：TIF转GeoJSON图层状态
})

// 图层引用
// 🌟 核心修复：重新定义 layers 变量，严格限定类型
const layers = reactive({
  // 预测热力图：ImageryLayer
  predictedBiomassHeatmap: null as Cesium.ImageryLayer | null,
  // 边界：GeoJsonDataSource
  mangroveBoundary: null as Cesium.GeoJsonDataSource | null,
  // 采样点：实体数组
  samplePoints: [] as Cesium.Entity[],
  // TIF 转 GeoJSON 数据源
  tifGeoJsonDataSource: null as Cesium.GeoJsonDataSource | null,
  // 自定义矢量图层
  customVector: null as { name: string; dataSource: Cesium.GeoJsonDataSource } | null
});

// 帽儿山核心视角参数
const targetPosition = Cesium.Cartesian3.fromDegrees(127.5, 45.4, 90000)
const targetOrientation = {
  heading: Cesium.Math.toRadians(0),
  pitch: Cesium.Math.toRadians(-90),
  roll: 0
}

// 3D热力图生成
interface HeatmapPoint {
  lng: number
  lat: number
  value: number
}
// 记录热力图Primitive，方便后续移除
let heatmapPrimitive: Cesium.Primitive | null = null

const createHeatmapCanvas = (
  points: HeatmapPoint[],
  width: number = 1024,
  height: number = 1024
): HTMLCanvasElement => {
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  if (!ctx) return canvas

  ctx.clearRect(0, 0, width, height)

  const lngs = points.map(p => p.lng)
  const lats = points.map(p => p.lat)
  const values = points.map(p => p.value)
  const minLng = Math.min(...lngs)
  const maxLng = Math.max(...lngs)
  const minLat = Math.min(...lats)
  const maxLat = Math.max(...lats)
  const minVal = Math.min(...values)
  const maxVal = Math.max(...values)
  const valRange = maxVal - minVal || 1

  // ✅ 缩小扩散半径，避免高值点互相叠加全红
  points.forEach(point => {
    const x = ((point.lng - minLng) / (maxLng - minLng)) * width
    const y = ((maxLat - point.lat) / (maxLat - minLat)) * height
    const radius = 30 // 缩小半径，减少叠加
    const intensity = (point.value - minVal) / valRange

    // ✅ 降低高值点的透明度，避免过曝
    const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius)
    gradient.addColorStop(0, `rgba(255, 255, 255, ${0.3 + intensity * 0.4})`)
    gradient.addColorStop(1, 'rgba(255, 255, 255, 0)')

    ctx.fillStyle = gradient
    ctx.beginPath()
    ctx.arc(x, y, radius, 0, Math.PI * 2)
    ctx.fill()
  })

  const imageData = ctx.getImageData(0, 0, width, height)
  const data = imageData.data

  // ✅ 【修改这里】调整颜色分布，把更多空间留给低数值
  const colorStops = [
    { offset: 0, color: [34, 197, 94] as const },   // 低：绿色
    { offset: 0.25, color: [59, 130, 246] as const }, // 中低：蓝色
    { offset: 0.5, color: [168, 85, 247] as const }, // 中高：紫色
    { offset: 0.75, color: [239, 68, 68] as const }     // 高：红色
  ]

  for (let i = 0; i < data.length; i += 4) {
    const gray = data[i]!
    if (gray === 0) {
      data[i + 3] = 0
      continue
    }

    const t = gray / 255
    let color: [number, number, number] = [255, 255, 255]

    for (let j = 0; j < colorStops.length - 1; j++) {
      const stop1 = colorStops[j]!
      const stop2 = colorStops[j + 1]!
      if (t >= stop1.offset && t <= stop2.offset) {
        const segmentT = (t - stop1.offset) / (stop2.offset - stop1.offset)
        color = [
          Math.round(stop1.color[0] + (stop2.color[0] - stop1.color[0]) * segmentT),
          Math.round(stop1.color[1] + (stop2.color[1] - stop1.color[1]) * segmentT),
          Math.round(stop1.color[2] + (stop2.color[2] - stop1.color[2]) * segmentT)
        ]
        break
      }
    }

    data[i] = color[0]
    data[i + 1] = color[1]
    data[i + 2] = color[2]
    // ✅ 降低整体透明度，让底图透过来，避免红色太刺眼
    data[i + 3] = Math.min(180, gray)
  }

  ctx.putImageData(imageData, 0, 0)
  return canvas
}

const addHeatmapToCesium = async (
  points: HeatmapPoint[],
  bounds: [number, number, number, number]
) => {
  if (!viewer) return null;

  if (heatmapPrimitive) {
    viewer.scene.primitives.remove(heatmapPrimitive);
    heatmapPrimitive = null;
  }

  // 1. 生成热力图纹理（你原来的 createHeatmapCanvas 不变）
  const heatmapCanvas = createHeatmapCanvas(points, 1024, 1024);
  const canvasUrl = heatmapCanvas.toDataURL();

  // 2. 计算数据范围，用于高度拉伸
  const values = points.map(p => p.value);
  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);
  const valRange = maxVal - minVal || 1;

  // 3. 创建网格几何体（带高度的 3D 面）
  const [minLng, maxLng, minLat, maxLat] = bounds;
  const rectangle = Cesium.Rectangle.fromDegrees(minLng, minLat, maxLng, maxLat);

  // 关键：创建带高度的矩形几何体
  const geometry = new Cesium.RectangleGeometry({
    rectangle: rectangle,
    height: 0,
    extrudedHeight: 0, // 先设为0，后面用纹理坐标+高度函数控制
    granularity: Cesium.Math.RADIANS_PER_DEGREE * 0.001, // 细粒度，保证高度平滑
  });

  // 4. 创建材质，把 Canvas 作为纹理贴上去
  const material = Cesium.Material.fromType('Image', {
    image: canvasUrl,
    transparent: true,
    repeat: new Cesium.Cartesian2(1, 1),
  });

  // 5. 创建 Primitive，开启透明混合
  heatmapPrimitive = new Cesium.Primitive({
    geometryInstances: new Cesium.GeometryInstance({
      geometry: geometry,
    }),
    appearance: new Cesium.MaterialAppearance({
      material: material,
      translucent: true,
      renderState: {
        blending: Cesium.BlendingState.ALPHA_BLEND,
        depthTest: {
          enabled: false,
        },
      },
    }),
    asynchronous: false,
  });

  // 6. 添加到场景
  viewer.scene.primitives.add(heatmapPrimitive);

  // 7. 定位
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(
      (minLng + maxLng) / 2,
      (minLat + maxLat) / 2,
      10000
    ),
    orientation: {
      heading: 0,
      pitch: Cesium.Math.toRadians(-45),
      roll: 0
    },
    duration: 1.5
  });

  console.log('✅ 3D 热力图（高度版）加载成功');
  return heatmapPrimitive;
};

// 加载基础热力图（最终稳定版 → 内部调用 addHeatmapToCesium）
const loadBiomassHeatmap = async () => {
  if (!viewer) return;
  if (heatmapPrimitive) return;

  try {
    // 1. 读取 GeoJSON
    const response = await fetch('/src/assets/geo/simple_heatmap.geojson');
    const geoJsonData = await response.json();

    // 2. 坐标转换
    if (geoJsonData.crs?.properties?.name === 'urn:ogc:def:crs:EPSG::32651') {
      geoJsonData.features.forEach((feature: any) => {
        if (feature.geometry.type === 'Polygon') {
          feature.geometry.coordinates = feature.geometry.coordinates.map((ring: number[][]) =>
            ring.map((coord: number[]) => proj4(utm51n, wgs84, coord))
          );
        }
      });
      delete geoJsonData.crs;
    }

    
    // 3. 提取热力点
    const points: HeatmapPoint[] = [];
    geoJsonData.features.forEach((f: any) => {
      if (f.geometry.type !== 'Polygon') return;
      const val = f.properties?.biomass;
      if (!val || val <= 0) return;

      const coords = f.geometry.coordinates[0];
      const lons = coords.map((c: number[]) => c[0]);
      const lats = coords.map((c: number[]) => c[1]);
      const lng = (Math.min(...lons) + Math.max(...lons)) / 2;
      const lat = (Math.min(...lats) + Math.max(...lats)) / 2;
      points.push({ lng, lat, value: val });
    });
    if (points.length > 0) {
      const values = points.map(p => p.value);
      const minVal = Math.min(...values);
      const maxVal = Math.max(...values);
      const valRange = maxVal - minVal || 1;

      points.forEach(p => {
        const norm = (p.value - minVal) / valRange;
        // 对数归一化（解决你数据全红的核心）
        p.value = Math.pow(norm, 0.3) * 1000;
      });
    }

    if (points.length === 0) throw new Error('无有效数据');

    // 4. 计算边界
    const lats = points.map(p => p.lat);
    const lngs = points.map(p => p.lng);
    const bounds: [number, number, number, number] = [
      Math.min(...lngs),
      Math.max(...lngs),
      Math.min(...lats),
      Math.max(...lats)
    ];

    // ✅ 调用并保存热力图
    const primitive = await addHeatmapToCesium(points, bounds);
    heatmapPrimitive = primitive as any;

    ElMessage.success('✅ 3D 热力图加载完成');
  } catch (err) {
    console.error(err);
    ElMessage.error('❌ 加载失败');
  }
};

// 加载帽儿山边界
const loadMaoershanBoundary = async () => {
  if (!viewer) return;
  // 如果已经加载过，直接返回，避免重复
  if (layers.mangroveBoundary) {
    console.log('✅ 帽儿山边界已存在，无需重复加载')
    return;
  }

  try {
    const response = await fetch('/src/assets/geo/maoershan_boundary.geojson')
    const geoJsonData = await response.json()

    if (geoJsonData.crs && geoJsonData.crs.properties.name === 'urn:ogc:def:crs:EPSG::32651') {
      geoJsonData.features.forEach((feature: any) => {
        if (feature.geometry.type === 'Polygon') {
          feature.geometry.coordinates = feature.geometry.coordinates.map((ring: number[][]) => 
            ring.map((coord: number[]) => proj4(utm51n, wgs84, coord))
          )
        } else if (feature.geometry.type === 'MultiPolygon') {
          feature.geometry.coordinates = feature.geometry.coordinates.map((polygon: number[][][]) => 
            polygon.map((ring: number[][]) => 
              ring.map((coord: number[]) => proj4(utm51n, wgs84, coord))
            )
          )
        }
      })
      delete geoJsonData.crs
    }

    const dataSource = await Cesium.GeoJsonDataSource.load(geoJsonData, {
      fill: Cesium.Color.fromCssColorString('#4fc3f7').withAlpha(0.2),
      stroke: Cesium.Color.fromCssColorString('#4fc3f7'),
      strokeWidth: 3
    })
    // 关键：给数据源命名，方便兜底移除
    dataSource.name = 'maoershan_boundary'
    layers.mangroveBoundary = dataSource
    viewer.dataSources.add(dataSource)
    console.log('✅ 帽儿山边界加载成功')
  } catch (err) {
    console.error('❌ 帽儿山边界加载失败:', err)
    throw new Error('获取帽儿山边界失败: ' + (err as Error).message)
  }
}

// 加载采样点
const loadSamplePoints = async () => {
  if (!viewer || layers.samplePoints.length > 0) return;
  try {
    const res = await getSamplePoints(selectedYear.value);
    if (res.code !== 200) {
      // 改为警告，不抛出致命错误
      console.warn("获取采样点数据失败（后端返回非200）:", res.msg);
      ElMessage.warning({
        message: `采样点加载失败: ${res.msg || "接口返回异常"}`,
        zIndex: 10001
      });
      return;
    }
    const points = res.data;

    points.forEach((point: any, index: number) => {
      const entity = viewer!.entities.add({
        position: Cesium.Cartesian3.fromDegrees(
          point.jindu,
          point.weidu,
          500
        ),
        point: {
          pixelSize: 10,
          color: Cesium.Color.WHITE,
          outlineColor: Cesium.Color.WHITE,
          outlineWidth: 2,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
          disableDepthTestDistance: Number.POSITIVE_INFINITY
        },
        description: `
          <div style="padding: 10px; color: #000;">
            <h4>采样点 ${index + 1}</h4>
            <p>年份：${selectedYear.value}</p>
            <p>经度：${point.jindu.toFixed(6)}</p>
            <p>纬度：${point.weidu.toFixed(6)}</p>
            <p>生物量：${point.AGB} 吨/公顷</p>
          </div>
        `
      });
      layers.samplePoints.push(entity);
    });
    console.log(`✅ 采样点加载成功（共${points.length}个，白色显示）`);
  } catch (err) {
    // 改为警告，不抛出致命错误
    console.error("❌ 采样点加载失败:", err);
    ElMessage.error({
      message: "采样点接口异常，请检查后端服务或接口路径",
      zIndex: 10001
    });
  }
};

const loadPredictedBiomassHeatmap = async (tifUrl?: string) => {
  if (!viewer) {
    ElMessage({
      message:'地图实例未初始化',
      type:'error',
      zIndex:10001
    })
    return;
  }

  try {
    // 1. 移除旧图层（强制清理所有残留）
    if (layers.tifGeoJsonDataSource) {
      viewer.dataSources.remove(layers.tifGeoJsonDataSource, true);
      layers.tifGeoJsonDataSource = null;
    }

    // 2. 构造GeoJSON URL（直接替换后缀）
    let geojsonUrl = tifUrl?.replace('.tif', '.geojson');
    if (!geojsonUrl) {
      if (!props.predictionTifPath) {
        throw new Error('未提供TIF文件路径');
      }
      geojsonUrl = props.predictionTifPath.replace('.tif', '.geojson');
    }

    if (!geojsonUrl) {
      throw new Error('GeoJSON URL为空，无法加载');
    }

    // 3. 加载后端生成的GeoJSON
    console.log('加载GeoJSON:', geojsonUrl);
    const geoJsonRes = await fetch(geojsonUrl);
    if (!geoJsonRes.ok) {
      throw new Error(`请求失败，状态码: ${geoJsonRes.status}`);
    }
    const text = await geoJsonRes.text();
    
    if (text.trim() === "" || text.includes("<html") || text.includes("Not Found")) {
      throw new Error("后端返回了无效内容（可能是404页面或空文件），请确认空间预测任务已完成。");
    }

    const geoJson = JSON.parse(text);

    // 4. 手动解析GeoJSON并创建实体
    const dataSource = new Cesium.GeoJsonDataSource('biomass_grid');
    let validCount = 0;

    // ========== 核心新增：先计算真实数据范围 ==========
    let min_biomass = Infinity;
    let max_biomass = -Infinity;
    if (geoJson.features && geoJson.features.length > 0) {
      geoJson.features.forEach((feature: any) => {
        const biomass = feature.properties?.biomass;
        if (biomass !== undefined && biomass !== null && biomass > 0) {
          min_biomass = Math.min(min_biomass, biomass);
          max_biomass = Math.max(max_biomass, biomass);
        }
      });
    }
    // 兜底：防止数据范围异常
    if (min_biomass === Infinity) min_biomass = 0;
    if (max_biomass === -Infinity) max_biomass = 100;

    // 遍历GeoJSON特征，手动创建Polygon实体
    if (geoJson.features && geoJson.features.length > 0) {
      geoJson.features.forEach((feature: any) => {
        // 只处理Polygon类型
        if (feature.geometry?.type !== 'Polygon') return;
        
        // 获取生物量值（添加类型守卫）
        const biomass = feature.properties?.biomass;
        if (biomass === undefined || biomass === null || biomass <= min_biomass) return;

        // 转换坐标为Cesium支持的格式（核心修复：添加坐标有效性检查）
        const rawCoordinates = feature.geometry.coordinates[0] || [];
        const positions: Cesium.Cartesian3[] = [];

        rawCoordinates.forEach((coord: any) => {
          // 确保 coord[0] 和 coord[1] 是有效的数字
          const lon = coord[0];
          const lat = coord[1];
          if (typeof lon === 'number' && !isNaN(lon) && typeof lat === 'number' && !isNaN(lat)) {
            positions.push(Cesium.Cartesian3.fromDegrees(lon, lat));
          }
        });

        // 必须至少有3个点才能构成一个面
        if (positions.length < 3) return;

        // ========== 核心修改：绿-蓝-紫-红渐变 + 增强差异 ==========
        // 基于真实数据范围归一化（不再用固定的/100）
        const normalizedValue = (biomass - min_biomass) / (max_biomass - min_biomass);
        let color: Cesium.Color;

        // 分段渐变：绿 → 蓝 → 紫 → 红（差异最大化）
        if (normalizedValue < 0.2) {
          // 0~0.2: 深绿 → 亮绿
          const t = normalizedValue / 0.2;
          color = Cesium.Color.fromHsl(0.45, 0.9, 0.3 + t * 0.2, 0.9);
        } else if (normalizedValue < 0.4) {
          // 0.25~0.5: 绿 → 蓝
          const t = (normalizedValue - 0.2) / 0.2;
          color = Cesium.Color.fromHsl(0.45 - t * 0.25, 0.9, 0.5 + t * 0.1, 0.9);
        } else if (normalizedValue < 0.5) {
          // 0.5~0.75: 蓝 → 紫
          const t = (normalizedValue - 0.4) / 0.1;
          color = Cesium.Color.fromHsl(0.2 - t * 0.1, 0.9, 0.6 + t * 0.1, 0.9);
        } else {
          // 0.75~1: 紫 → 红（高值高亮）
          const t = (normalizedValue - 0.5) / 0.5;
          color = Cesium.Color.fromHsl(0.1 - t * 0.1, 0.95, 0.4 + t * 0.4, 0.9);
        }

        // 手动创建实体
        const entity = new Cesium.Entity({
          polygon: {
            hierarchy: new Cesium.PolygonHierarchy(positions),
            material: color,
            outline: false,
            heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
            classificationType: Cesium.ClassificationType.BOTH,
            show: true
          },
          properties: {
            biomass: biomass
          }
        });

        // 添加到数据源
        dataSource.entities.add(entity);
        validCount++;
      });
    }

    // 5. 添加到地图
    layers.tifGeoJsonDataSource = dataSource;
    await viewer.dataSources.add(dataSource);

    // 6. 强制触发渲染
    viewer.scene.requestRender();

    // 7. 固定定位到帽儿山区域
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(127.7, 45.3, 90000), // 提高高度扩大视野
      orientation: {
        heading: Cesium.Math.toRadians(0),
        pitch: Cesium.Math.toRadians(-90), // 更陡的俯视角度
        roll: 0.0
      },
      duration: 2,
      maximumHeight: 10000
    });

    ElMessage({
      message:`✅ 成功加载${validCount}个生物量方格，范围: ${min_biomass.toFixed(1)} ~ ${max_biomass.toFixed(1)} 吨/公顷`,
      type:'success',
      zIndex:10001
    })
    console.log(`✅ GeoJSON图层加载成功，有效方格数：${validCount}，数据范围：${min_biomass.toFixed(1)}~${max_biomass.toFixed(1)}`);

  } catch (err) {
    const errorMsg = (err as Error).message || '加载GeoJSON图层失败';
    console.error('!!!! 加载失败:', err);
    ElMessage({
      message:`加载失败：${errorMsg}`,
      type:'error',
      zIndex:10001
    })
  }
};

// 图层切换函数
const toggleLayer = async (layer: string) => {
  console.log('子组件收到图层切换:', layer, layerStates[layer as keyof typeof layerStates])
  if (!viewer) return

  const layerKey = layer as keyof typeof layerStates;
  const newState = !layerStates[layerKey];
  layerStates[layerKey] = newState;

  switch (layer) {
    case 'biomassHeatmap':
    if (newState) {
      // 打开
      if (heatmapPrimitive && viewer) {
        viewer.scene.primitives.remove(heatmapPrimitive as any);
        heatmapPrimitive = null;
      }
      await loadBiomassHeatmap();
    } else {
      // 关闭 ✅ 这里现在一定能删掉
      if (viewer && heatmapPrimitive) {
        viewer.scene.primitives.remove(heatmapPrimitive as any);
        heatmapPrimitive = null;
        console.log("✅ 热力图已关闭");
      }
    }
    break;

    case 'mangroveBoundary':
      if (layerStates.mangroveBoundary) {
        if (!layers.mangroveBoundary) {
          await loadMaoershanBoundary()
        }
      } else {
        if (layers.mangroveBoundary) {
          const removed = await viewer.dataSources.remove(layers.mangroveBoundary)
          if (removed) {
            console.log('✅ 成功移除帽儿山边界图层')
            layers.mangroveBoundary = null
          } else {
            console.warn('⚠️ 移除边界图层失败，可能已被移除')
            layers.mangroveBoundary = null
          }
        }
        const allDataSources = (viewer.dataSources as any)._dataSources as Cesium.DataSource[]
        for (const ds of allDataSources) {
          if (ds.name && ds.name.includes('maoershan_boundary')) {
            await viewer.dataSources.remove(ds)
            console.log('✅ 兜底移除边界图层:', ds.name)
          }
        }
      }
      break

    case 'samplePoints':
      if (layerStates.samplePoints) {
        await loadSamplePoints()
      } else {
        const currentViewer = viewer;
        if (currentViewer) {
          layers.samplePoints.forEach(entity => currentViewer.entities.remove(entity))
        }
        layers.samplePoints = []
      }
      break
  }
}

// 天地图 Key 
const TIANDITU_KEY = 'a9516399abf03d1a6097a8a30c39820b'
// 添加天地图影像 
const addTiandituImage = () =>{
  if(!viewer)return
  viewer.imageryLayers.addImageryProvider(
    new Cesium.WebMapTileServiceImageryProvider({
      url: `http://t0.tianditu.com/img_w/wmts?service=wmts&request=GetTile&version=1.0.0&LAYER=img&tileMatrixSet=w&TileMatrix={TileMatrix}&TileRow={TileRow}&TileCol={TileCol}&style=default&format=tiles&tk=${TIANDITU_KEY}`,
      layer: 'tdtBasicLayer',
      style: 'default',
      format: 'image/jpeg',
      tileMatrixSetID: 'GoogleMapsCompatible',
    })
  )
}
// --- 新增：添加天地图注记 ---
const addTiandituLabel =()=>{
  if(!viewer)return
  viewer.imageryLayers.addImageryProvider(
    new Cesium.WebMapTileServiceImageryProvider({
      url: `http://t0.tianditu.com/cia_w/wmts?service=wmts&request=GetTile&version=1.0.0&LAYER=cia&tileMatrixSet=w&TileMatrix={TileMatrix}&TileRow={TileRow}&TileCol={TileCol}&style=default&format=tiles&tk=${TIANDITU_KEY}`,
      layer: 'tdtBasicLayer',
      style: 'default',
      format: 'image/jpeg',
      tileMatrixSetID: 'GoogleMapsCompatible',
    })
  )
}

// --- 新增：添加天地图矢量底图 ---
const addTiandituVector = () => {
  if (!viewer) return
  viewer.imageryLayers.addImageryProvider(
    new Cesium.WebMapTileServiceImageryProvider({
      url: `http://t0.tianditu.com/vec_w/wmts?service=wmts&request=GetTile&version=1.0.0&LAYER=vec&tileMatrixSet=w&TileMatrix={TileMatrix}&TileRow={TileRow}&TileCol={TileCol}&style=default&format=tiles&tk=${TIANDITU_KEY}`,
      layer: 'tdtVecBasicLayer',
      style: 'default',
      format: 'image/jpeg',
      tileMatrixSetID: 'GoogleMapsCompatible',
    })
  )
}

// 添加地形
const addTerrain = async () => {
  if (!viewer) return
  try {
    // 方案1：使用 Cesium 官方地形（推荐）
    const terrainProvider = await Cesium.CesiumTerrainProvider.fromUrl(
      Cesium.IonResource.fromAssetId(1), // Cesium World Terrain
      {
        requestWaterMask: true,
        requestVertexNormals: true,
      }
    )
    viewer.terrainProvider = terrainProvider
    console.log('地形加载成功')
  } catch (e) {
    console.error('加载地形失败，使用默认无地形模式', e)
    // 方案2：如果地形加载失败，使用无地形模式
    viewer.terrainProvider = new Cesium.EllipsoidTerrainProvider()
  }
}

// 新增：加载自定义矢量图层方法
const loadCustomVectorLayer = async (geoJson: any, layerName: string, color = Cesium.Color.RED) => {
  if (!viewer) {
    throw new Error("❌ viewer 不存在，无法加载图层");
  }

  // 移除同名图层
  if (layers.customVector && layers.customVector.name === layerName) {
    viewer.dataSources.remove(layers.customVector.dataSource)
    layers.customVector = null;
    console.log("✅ 移除同名图层成功");
  }

  try {
    // 加载转换后的 WGS84 格式 GeoJSON
    const dataSource = await Cesium.GeoJsonDataSource.load(geoJson, {
      fill: color.withAlpha(0.2),
      stroke: color,
      strokeWidth: 3
    });

    // 存储图层引用
    layers.customVector = { name: layerName, dataSource };
    viewer.dataSources.add(dataSource);

    // ========== 修复：精准定位到帽儿山全貌 ==========
    // 1. 收集所有要素的坐标点
    const allPositions: Cesium.Cartesian3[] = [];
    dataSource.entities.values.forEach((entity: any) => {
      // 处理多边形/多多边形
      if (entity.polygon?.hierarchy) {
        const hierarchy = entity.polygon.hierarchy.getValue(Cesium.JulianDate.now());
        if (hierarchy?.positions) {
          allPositions.push(...hierarchy.positions);
        }
      }
      // 处理点/线（可选，根据你的数据类型）
      if (entity.polyline?.positions) {
        const positions = entity.polyline.positions.getValue(Cesium.JulianDate.now());
        if (positions) {
          allPositions.push(...positions);
        }
      }
      if (entity.position) {
        const position = entity.position.getValue(Cesium.JulianDate.now());
        if (position) {
          allPositions.push(position);
        }
      }
    });

    // 2. 如果有数据，定位到帽儿山区域
    if (allPositions.length > 0) {
      // 自定义相机飞行参数（关键：设置高度和视角，适配帽儿山范围）
      viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(
          127.5, // 帽儿山大致中心经度（可根据你的数据微调）
          45.3,  // 帽儿山大致中心纬度（可根据你的数据微调）
          5000   // 相机高度（米），5000米能看到全貌，可按需调整
        ),
        orientation: {
          heading: Cesium.Math.toRadians(0),    // 水平方向角度（0为正北）
          pitch: Cesium.Math.toRadians(-45),    // 俯视角度（-90是垂直向下）
          roll: 0.0                             // 旋转角度
        },
        duration: 2,                            // 飞行时长（秒）
        maximumHeight: 10000,                   // 最大飞行高度
        easingFunction: Cesium.EasingFunction.QUADRATIC_IN_OUT // 平滑过渡
      });
    }

    return dataSource;
  } catch (err) {
    console.error("❌ 加载自定义矢量图层失败:", err);
    throw new Error(`加载图层 "${layerName}" 失败：${(err as Error).message}`);
  }
};

// 新增：移除自定义矢量图层
const removeCustomVectorLayer = (layerName: string) => {
  if (!viewer || !layers.customVector) return
  
  if (layers.customVector.name === layerName) {
    viewer.dataSources.remove(layers.customVector.dataSource)
    layers.customVector = null
    console.log(`✅ 自定义图层 ${layerName} 已移除`)
  }
}

// ==================== 6. 初始化与销毁 ====================
onMounted(async() => {
  isVisible.value = true
  // 新增：标记组件已挂载，异步操作前必须校验
  isMounted = true
  await nextTick()

  const container = document.getElementById('cesium-container') as HTMLElement;
  if (!container) { // 新增：校验 isMounted
    throw new Error('Cesium container not found');
  }

  // 新增：复用已有实例，避免重复创建
  if (viewer) {
    console.log('✅ 复用已有 Cesium 实例')
    viewer.scene.requestRender() // 强制触发渲染
    viewer.clock.shouldAnimate = true // 恢复动画
    return
  }
  
  // 设置Cesium Token
  Cesium.Ion.defaultAccessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiI2ZjAxNzdkNS00YmJkLTQ2MDQtOGZkNy0yMTkzZWE1NTdhYTAiLCJpZCI6MzgxOTIxLCJpYXQiOjE3NjkwNDY4NjR9.HBkoWJDqXTxEBrdAEj5R8pIJo8ZbM5qt9uujXeGGw7o'

  // 初始化Cesium Viewer
  viewer = new Cesium.Viewer(container, {
    baseLayerPicker: false,
    navigationHelpButton: false,
    animation: false,
    timeline: false,
    fullscreenButton: false,
    creditContainer: document.createElement('div'),
  });

  

  (container as any)._cesiumViewer = viewer

   // 初始化视角动画（修改：将监听句柄赋值给变量）
  const flyToMaoershan = () => {
    if (!viewer || !isMounted) return // 新增：安全校验
    viewer.camera.flyTo({
      destination: targetPosition,
      orientation: targetOrientation,
      duration: 5,
      easingFunction: Cesium.EasingFunction.QUADRATIC_IN_OUT,
      maximumHeight: 800000,
      complete: () => {
        if (isMounted) console.log('✅ 已飞到帽儿山视角')
      }
    })
  }

  // 新增：将监听函数赋值给变量，方便后续移除
  postRenderListener = () => {
  if (!isMounted || !viewer) return
  flyToMaoershan()
}
viewer.scene.postRender.addEventListener(postRenderListener)

// 飞完自动移除监听
setTimeout(() => {
  if (viewer && postRenderListener) {
    viewer.scene.postRender.removeEventListener(postRenderListener)
    postRenderListener = null
  }
}, 5000)

  // 自定义Home按钮点击事件（新增：isMounted 校验）
  setTimeout(() => {
    if (!isMounted) return
    const homeButtonDom = document.querySelector('.cesium-button.cesium-home-button')
    if (homeButtonDom) {
      homeButtonDom.addEventListener('click', (e) => {
        e.preventDefault()
        e.stopPropagation()
        flyToMaoershan()
      })
    }
  }, 1000)

  // 移除默认的 Bing 底图
  if (viewer && isMounted) viewer.imageryLayers.remove(viewer.imageryLayers.get(0))
  //添加天地图影像
  if (isMounted) addTiandituImage()
  //添加天地图注记（叠加在影像上）
  if (isMounted) addTiandituLabel()
  //添加地形（新增：isMounted 校验）
  if (isMounted) await addTerrain()
  // 2D模式适配（新增：isMounted 校验）
  if (isMounted && props.isFlatMode) {
    viewer.scene.globe.depthTestAgainstTerrain = false
    viewer.scene.mode = Cesium.SceneMode.SCENE2D
  }
})

onUnmounted(() => {
  // 第一步：立即标记组件已卸载，阻断所有异步操作
  isMounted = false
  isVisible.value = false
  console.log('ℹ️ Cesium 组件已隐藏，实例保留，下次切回可直接显示')
})
//暴露方法给父组件 
defineExpose({
  viewer,
  flyTo: (position: { lon: number; lat: number; height: number; pitch: number }) => {
    if (!viewer) return
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(position.lon, position.lat, position.height),
      orientation: {
        heading: Cesium.Math.toRadians(0),
        pitch: Cesium.Math.toRadians(position.pitch),
        roll: 0
      },
      duration: 2,
      easingFunction: Cesium.EasingFunction.QUADRATIC_IN_OUT
    })
  },
  // 图层状态
  layerStates,
  // 切换图层
  toggleLayer,
  // 年份/区域选择
  selectedYear,
  selectedRegion,
  // 加载帽儿山边界
  loadMaoershanBoundary,
  // 加载生物量热力图
  loadBiomassHeatmap,
  // 加载采样点
  loadSamplePoints,
  // 暴露天地图相关方法
  addTiandituImage,
  addTiandituLabel,
  addTiandituVector,
  addTerrain,
  loadCustomVectorLayer,
  loadPredictedBiomassHeatmap,
  removeCustomVectorLayer
})
</script>

<style scoped>
#cesium-container {
  width: 100%;
  height: 100vh;
  position: absolute;
  top: 0;
  left: 0;
  z-index: 1;
}

/* 自定义Home按钮样式 */
.cesium-button.cesium-home-button::before {
  content: '中国';
  font-size: 12px;
  color: #fff;
}
.cesium-button.cesium-home-button img {
  display: none;
}

/* 确保红树林置顶显示 */
:deep(.cesium-geoJsonDataSource) {
  z-index: 9999 !important;
}
:deep(.cesium-polyline), :deep(.cesium-polygon) {
  z-index: 10000 !important;
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
