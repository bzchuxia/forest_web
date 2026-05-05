// src/utils/tableConfig.ts
/**
 * 表结构配置文件（和后端table_config.py一一对应）
 * 修改表/字段时，只需改这里，无需改业务代码
 */
export const TABLE_CONFIG = {
  // 红树林矢量分布（对应后端public.kongjian表，适配实际字段）
  mangroveDistribution: {
    tableName: "public.kongjian",    // 后端表名（前端仅做标识，无实际操作）
    geomField: "geom",               // 后端几何字段
    idField: "gid",                  // 后端主键字段（表中实际主键）
    properties: ["gid", "id_1", "id", "省", "市", "区", "类型", "面积", "year"],  // 表中实际属性字段
    coordType: "WGS84"               // 坐标系（适配Cesium）
  },
  // 生物量热力图（按需扩展，保留原有配置）
  biomassHeatmap: {
    lonField: "lon",
    latField: "lat",
    valueField: "biomass_value"
  },
  // 红树林边界（按需扩展，保留原有配置）
  mangroveBoundary: {
    geomField: "geom",
    regionField: "region"
  },
  // 采样点（按需扩展，保留原有配置）
  samplePoints: {
    lonField: "lon",
    latField: "lat",
    sampleIdField: "sample_id",
    biomassField: "biomass"
  }
} as const;

// 定义每个配置项的类型，方便类型推断
type MangroveDistributionConfig = typeof TABLE_CONFIG['mangroveDistribution'];
type BiomassHeatmapConfig = typeof TABLE_CONFIG['biomassHeatmap'];
type SamplePointsConfig = typeof TABLE_CONFIG['samplePoints'];


/**
 * 通用数据解析工具（适配不同表结构）
 * 核心逻辑完全保留，仅适配新字段的映射
 */
// 解析GeoJSON数据（适配红树林分布/边界）
export const parseGeoJSON = (rawData: any, configKey: keyof typeof TABLE_CONFIG) => {
  const config = TABLE_CONFIG[configKey] as MangroveDistributionConfig;
  if (!rawData || !rawData.features) return { type: "FeatureCollection", features: [] };
  
  // 统一格式，确保Cesium能识别（保留原有逻辑，仅适配新字段）
  return rawData.features.map((feature: any) => ({
    type: "Feature",
    geometry: feature.geometry,
    properties: {
      // 按配置映射字段，兼容不同表结构
      ...feature.properties,
      id: feature.properties[config.idField || "gid"] || feature.properties.gid  // 适配实际主键gid
    }
  }));
};

// 解析热力点/采样点数据（适配数组格式，保留原有逻辑）
export const parsePointData = (rawData: any, configKey: keyof typeof TABLE_CONFIG) => {
  const config = TABLE_CONFIG[configKey];
  if (!Array.isArray(rawData)) return [];

  // 类型守卫：判断是否为热力图配置
  function isBiomassHeatmapConfig(c: typeof config): c is BiomassHeatmapConfig {
    return (c as BiomassHeatmapConfig).valueField !== undefined;
  }

  // 类型守卫：判断是否为采样点配置
  function isSamplePointsConfig(c: typeof config): c is SamplePointsConfig {
    return (c as SamplePointsConfig).sampleIdField !== undefined;
  }

  if (isBiomassHeatmapConfig(config)) {
    // 处理热力图数据
    return rawData.map((item: any) => ({
      lon: item[config.lonField],
      lat: item[config.latField],
      value: item[config.valueField],
      sample_id: "N/A",
      biomass: "N/A"
    }));
  } else if (isSamplePointsConfig(config)) {
    // 处理采样点数据
    return rawData.map((item: any) => ({
      lon: item[config.lonField],
      lat: item[config.latField],
      value: "N/A",
      sample_id: item[config.sampleIdField],
      biomass: item[config.biomassField]
    }));
  } else {
    return [];
  }
};