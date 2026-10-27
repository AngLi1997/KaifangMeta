/// <reference path="../global.d.ts"/>

namespace Entity {
  type AnnotationModality = 'image' | 'text' | 'document' | 'video' | 'audio'

  /** 场景模板：Label Studio 模板 XML */
  interface AnnotationTemplate {
    id: number
    tenant_id: string
    scope: 'system' | 'tenant'
    code: string
    name: string
    modality: AnnotationModality
    config: string
    version: number
    updated_at?: string
  }

  type AnnotationTaskStatus = 'CREATED' | 'READY' | 'LABELING' | 'COMPLETED'

  interface AnnotationTask {
    id: number
    name: string
    mode: 'assigned' | 'free'
    template_id: number
    template_name: string
    template_ref: string
    /** 建单时的模板 XML 快照，列表接口不返回 */
    config?: string
    status: AnnotationTaskStatus
    item_count: number
    labeled_count: number
    creator_name: string
    created_at: string
  }

  interface AnnotationItem {
    id: number
    task_id: number
    item_key: string
    name: string
    status: 'PENDING' | 'LABELED'
    /** 编辑器 task.data，文件字段已签发为临时地址 */
    data?: Record<string, string>
    /** Label Studio 结果（serializeAnnotation） */
    result?: Record<string, unknown>[] | null
    annotator_name: string
    annotated_at: string | null
  }

  interface AnnotationWorkItem {
    task: AnnotationTask
    item: AnnotationItem
    index: number
    prev_id: number | null
    next_id: number | null
  }
}
