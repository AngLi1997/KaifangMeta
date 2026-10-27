import type { InjectionKey, Ref } from 'vue'

export interface WorkbenchItem {
  id?: number
  name: string
  index: number
  total: number
}

/** 工作台向各组件提供的运行时上下文 */
export interface WorkbenchContext {
  run: (action: string) => void
  item: Ref<WorkbenchItem | undefined>
  hasPrev: Ref<boolean>
  hasNext: Ref<boolean>
  loading: Ref<boolean>
  logs: Ref<string[]>
  /** 表单值：表单名 → 字段名 → 值 */
  forms: Record<string, Record<string, unknown>>
  canvas: { config: Ref<string>, data: Ref<Record<string, unknown>>, result: Ref<Record<string, unknown>[]> }
  setCanvas: (el: unknown) => void
}

export const WORKBENCH: InjectionKey<WorkbenchContext> = Symbol('workbench')
