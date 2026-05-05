// src/types/cesium-heatmap.d.ts
declare module 'cesium-heatmap' {
  import { ImageryProvider } from 'cesium';
  export default class HeatmapImageryProvider extends ImageryProvider {
    constructor(options: {
      heatmap: {
        radius: number;
        gradient: Record<number, string>;
      };
      data: Array<{
        longitude: number;
        latitude: number;
        intensity: number;
      }>;
    });
  }
}