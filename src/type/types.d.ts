declare module 'xmldom' {
  export class DOMParser {
    parseFromString(xmlStr: string, mimeType?: string): Document
  }
}