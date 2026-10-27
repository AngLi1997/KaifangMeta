import type { TagProps } from 'naive-ui'

export const TASK_STATUS: Record<Entity.AnnotationTaskStatus, { label: string, type: TagProps['type'] }> = {
  CREATED: { label: '待上传', type: 'default' },
  READY: { label: '待标注', type: 'info' },
  LABELING: { label: '标注中', type: 'warning' },
  COMPLETED: { label: '已完成', type: 'success' },
}

export const ITEM_STATUS: Record<Entity.AnnotationItem['status'], { label: string, type: TagProps['type'] }> = {
  PENDING: { label: '待标注', type: 'default' },
  LABELED: { label: '已标注', type: 'success' },
}

export const MODALITY: Record<Entity.AnnotationModality, string> = {
  image: '图像',
  document: '文档',
  text: '文本',
  video: '视频',
  audio: '音频',
}

export function toOptions(map: Record<string, string | { label: string }>) {
  return Object.entries(map).map(([value, v]) => ({ value, label: typeof v === 'string' ? v : v.label }))
}
