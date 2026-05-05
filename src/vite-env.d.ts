// src/vite-env.d.ts
/// <reference types="vite/client" />

// 声明 JSON 模块类型
declare module '*.geojson' {
  const value: any
  export default value
}