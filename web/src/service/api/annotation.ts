import { request } from '../http'

interface Page { page?: number, page_size?: number }

// ---- 场景模板 ----
export function fetchAnnotationTemplatePage(params: Page & { name?: string, modality?: string | null }) {
  return request.Get<Service.PageResult<Entity.AnnotationTemplate>>('/annotation/template/list', { params })
}
export function fetchAnnotationTemplate(id: number) {
  return request.Get<Service.ResponseResult<Entity.AnnotationTemplate>>('/annotation/template/get', { params: { id } })
}
export function fetchCreateAnnotationTemplate(data: Partial<Entity.AnnotationTemplate>) {
  return request.Post<Service.ResponseResult<Entity.AnnotationTemplate>>('/annotation/template/create', data)
}
export function fetchUpdateAnnotationTemplate(data: Partial<Entity.AnnotationTemplate>) {
  return request.Post<Service.ResponseResult<Entity.AnnotationTemplate>>('/annotation/template/update', data)
}

// ---- 标注工单 ----
export function fetchAnnotationTaskPage(params: Page & { name?: string, status?: string | null }) {
  return request.Get<Service.PageResult<Entity.AnnotationTask>>('/annotation/task/list', { params })
}
export function fetchAnnotationTask(id: number) {
  return request.Get<Service.ResponseResult<Entity.AnnotationTask>>('/annotation/task/get', { params: { id } })
}
export function fetchCreateAnnotationTask(data: { name: string, template_id: number }) {
  return request.Post<Service.ResponseResult<Entity.AnnotationTask>>('/annotation/task/create', data)
}
/** FormData：task_id + file */
export function fetchUploadAnnotationItem(data: FormData) {
  return request.Post<Service.ResponseResult<Entity.AnnotationItem>>('/annotation/task/upload', data)
}

// ---- 标注条目 ----
export function fetchAnnotationItemPage(params: Page & { task_id: number, status?: string | null, name?: string }) {
  return request.Get<Service.PageResult<Entity.AnnotationItem>>('/annotation/item/list', { params })
}
/** 不传 id 时取第一个待标注条目 */
export function fetchAnnotationWorkItem(task_id: number, id?: number) {
  return request.Get<Service.ResponseResult<Entity.AnnotationWorkItem>>('/annotation/item/get', { params: id ? { task_id, id } : { task_id } })
}
export function fetchSaveAnnotationItem(data: { id: number, result: Record<string, unknown>[] }) {
  return request.Post<Service.ResponseResult<null>>('/annotation/item/save', data)
}
