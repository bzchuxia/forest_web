// src/types/global.d.ts
declare global {
  interface Window {
    Cesium: typeof import('cesium')
  }
}
export {}