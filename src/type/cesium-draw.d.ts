// src/types/cesium-draw.d.ts
declare module 'cesium-draw' {
  import * as Cesium from 'cesium';

  // 声明绘图实例的配置项
  interface DrawStyle {
    polygon?: {
      material: Cesium.MaterialProperty | Cesium.Color;
      outlineColor: Cesium.Color;
      outlineWidth: number;
      clampToGround: boolean;
    };
    rectangle?: {
      material: Cesium.MaterialProperty | Cesium.Color;
      outlineColor: Cesium.Color;
      outlineWidth: number;
      clampToGround: boolean;
    };
    circle?: {
      material: Cesium.MaterialProperty | Cesium.Color;
      outlineColor: Cesium.Color;
      outlineWidth: number;
      clampToGround: boolean;
    };
  }

  // 声明绘图回调参数
  interface DrawOptions {
    onEnd: (entity: Cesium.Entity) => void;
    onCancel: () => void;
  }

  // 声明 Draw 类
  class Draw {
    constructor(viewer: Cesium.Viewer, options: { style: DrawStyle });
    draw(type: 'polygon' | 'rectangle' | 'circle', options: DrawOptions): void;
    cancel(): void;
  }

  export default Draw;
}