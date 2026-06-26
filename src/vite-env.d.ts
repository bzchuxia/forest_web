// src/vite-env.d.ts
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly DEV: boolean
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

// 声明 geojson 模块类型
declare module '*.geojson' {
  const value: any
  export default value
}