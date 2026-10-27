<script setup lang="ts">
// 标注工作台运行时：解析模板布局、提供上下文、实现公共命令；组件说明见 docs/platform/annotation/components/
import type { WorkbenchItem } from './context'
import { message } from '@/utils'
import type AnnotationCanvas from '../AnnotationCanvas.vue'
import { WORKBENCH } from './context'
import { checkLayout, extractCanvas, mockRows, parseLayout, toYaml, walk } from './layout'
import WorkbenchNode from './WorkbenchNode.vue'

type Result = Record<string, unknown>[]
const props = defineProps<{
  /** 模板 XML：<Workbench> 布局或旧的 <View> */
  config: string
  /** 条目数据（编辑器 task.data） */
  data: Record<string, unknown>
  /** 已有标注结果（含表单值） */
  result?: Result | null
  item?: WorkbenchItem
  hasPrev?: boolean
  hasNext?: boolean
  /** 保存 / 提交进行中 */
  loading?: boolean
  /** 模板预览：只渲染，保存、提交、翻页不触发 */
  preview?: boolean
}>()

const emit = defineEmits<{
  save: [result: Result]
  submit: [result: Result]
  prev: []
  next: []
}>()

/** 表单值、可编辑表格的行随标注结果保存，用这两个 type 与 Label Studio 结果区分 */
const FORM_RESULT = 'km.form'
const TABLE_RESULT = 'km.table'

const parsed = computed(() => {
  try {
    const root = parseLayout(props.config)
    const empty = walk(root).length === 1
    return { root, canvas: extractCanvas(props.config), empty, error: empty ? '' : checkLayout(root) }
  }
  catch (e) {
    return { root: null, canvas: '', empty: false, error: (e as Error).message }
  }
})
const nodes = computed(() => parsed.value.root ? walk(parsed.value.root) : [])
const formNodes = computed(() => nodes.value.filter(n => n.type === 'Form'))
const tableNodes = computed(() => nodes.value.filter(n => n.type === 'DataTable'))
const editableTables = computed(() => tableNodes.value.filter(t => t.attrs.editable === 'true'))
const hasCanvas = computed(() => nodes.value.some(n => n.type === 'Canvas'))

// 表单值：按表单名建好对象，切换条目或模板时从结果里回填
const forms = reactive<Record<string, Record<string, unknown>>>({})
watch([formNodes, () => props.result], () => {
  const saved = Object.fromEntries((props.result ?? []).filter(r => r.type === FORM_RESULT).map(r => [r.from_name, r.value]))
  for (const k of Object.keys(forms)) delete forms[k]
  for (const f of formNodes.value)
    forms[f.attrs.name] = { ...(saved[f.attrs.name] as object) }
}, { immediate: true })

// 表格行：可编辑表格从结果回填，否则用样例数据
const tables = reactive<Record<string, Record<string, unknown>[]>>({})
watch([tableNodes, () => props.result], () => {
  const saved = Object.fromEntries((props.result ?? []).filter(r => r.type === TABLE_RESULT).map(r => [r.from_name, (r.value as { rows: Record<string, unknown>[] }).rows]))
  for (const k of Object.keys(tables)) delete tables[k]
  for (const t of tableNodes.value)
    tables[t.attrs.name] = t.attrs.editable === 'true' && saved[t.attrs.name] ? JSON.parse(JSON.stringify(saved[t.attrs.name])) : mockRows(t.columns ?? [])
}, { immediate: true })

const canvasRef = ref<InstanceType<typeof AnnotationCanvas> | null>(null)
const canvasResult = computed(() => (props.result ?? []).filter(r => r.type !== FORM_RESULT && r.type !== TABLE_RESULT))

/** 提交给业务的结果：Label Studio 结果 + 每个表单一条 + 每个可编辑表格一条；画布未就绪时为 null */
function getResult(): Result | null {
  const canvas = hasCanvas.value ? canvasRef.value?.getResult() : []
  if (!canvas)
    return null
  return [
    ...canvas,
    ...formNodes.value.map(f => ({ type: FORM_RESULT, from_name: f.attrs.name, value: { ...forms[f.attrs.name] } })),
    ...editableTables.value.map(t => ({ type: TABLE_RESULT, from_name: t.attrs.name, value: { rows: JSON.parse(JSON.stringify(tables[t.attrs.name])) } })),
  ]
}

const logs = ref<string[]>([])
function log(text: string) {
  logs.value.unshift(`${new Date().toTimeString().slice(0, 8)} ${text}`)
}
watch(() => props.item?.id, () => logs.value = [])

/** 快照：界面上可见的全部数据，查看与导出共用 */
function snapshot() {
  return {
    item: props.item ? { id: props.item.id, name: props.item.name, index: props.item.index } : null,
    data: props.data,
    forms: JSON.parse(JSON.stringify(forms)),
    tables: JSON.parse(JSON.stringify(tables)),
    result: hasCanvas.value ? (canvasRef.value?.getResult() ?? canvasResult.value) : [],
  }
}
const drawer = ref(false)
const logOpen = ref(false)
const format = ref<'json' | 'yaml'>('json')
const snapshotText = computed(() => drawer.value ? (format.value === 'yaml' ? toYaml(snapshot()) : JSON.stringify(snapshot(), null, 2)) : '')

function download(fmt: 'json' | 'yaml') {
  const text = fmt === 'yaml' ? toYaml(snapshot()) : JSON.stringify(snapshot(), null, 2)
  const a = document.createElement('a')
  a.href = URL.createObjectURL(new Blob([text], { type: 'text/plain' }))
  a.download = `${props.item?.name ?? 'snapshot'}.${fmt}`
  a.click()
  URL.revokeObjectURL(a.href)
  log(`导出 ${a.download}`)
}

const isEmpty = (v: unknown) => v === undefined || v === null || v === '' || (Array.isArray(v) && !v.length)
/** 必填字段未填时提示第一个 */
function checkRequired() {
  for (const f of formNodes.value) {
    const miss = f.fields!.find(x => x.required && isEmpty(forms[f.attrs.name][x.name]))
    if (miss) {
      message.warning(`请填写「${miss.label}」`)
      return false
    }
  }
  return true
}

/** 公共命令；按钮与宿主页面（defineExpose）都调用这里 */
const commands: Record<string, () => void> = {
  'undo': () => canvasRef.value?.undo(),
  'redo': () => canvasRef.value?.redo(),
  'view-data': () => drawer.value = true,
  'log': () => logOpen.value = true,
  'export-json': () => download('json'),
  'export-yaml': () => download('yaml'),
  'save': () => {
    const result = getResult()
    if (result && !props.preview)
      emit('save', result)
    log('保存')
  },
  'submit': () => {
    const result = getResult()
    if (!result || !checkRequired())
      return
    if (!props.preview)
      emit('submit', result)
    log('提交')
  },
  'prev': () => !props.preview && emit('prev'),
  'next': () => !props.preview && emit('next'),
}
function run(action: string) {
  commands[action]?.()
}

provide(WORKBENCH, {
  run,
  item: toRef(props, 'item'),
  hasPrev: computed(() => !!props.hasPrev),
  hasNext: computed(() => !!props.hasNext),
  loading: computed(() => !!props.loading),
  logs,
  forms,
  tables,
  canvas: { config: computed(() => parsed.value.canvas), data: toRef(props, 'data'), result: canvasResult },
  setCanvas: el => canvasRef.value = el as InstanceType<typeof AnnotationCanvas> | null,
})

defineExpose({ run, snapshot, getResult })
</script>

<template>
  <div class="flex flex-col wh-full min-h-0">
    <n-alert v-if="parsed.error" type="error" :show-icon="false" class="m-3">
      {{ parsed.error }}
    </n-alert>
    <n-empty v-if="parsed.empty" description="工作台为空" class="m-auto" />
    <WorkbenchNode v-else-if="parsed.root" :node="parsed.root" class="p-3" />
  </div>

  <FormModal v-model:show="logOpen" title="日志" readonly>
    <n-empty v-if="!logs.length" description="暂无日志" />
    <n-scrollbar v-else class="max-h-100">
      <div v-for="(l, i) in logs" :key="i" class="py-1 text-sm">
        {{ l }}
      </div>
    </n-scrollbar>
  </FormModal>

  <n-drawer v-model:show="drawer" :width="560">
    <n-drawer-content closable :native-scrollbar="false">
      <template #header>
        查看数据
        <n-radio-group v-model:value="format" size="small" class="ml-4">
          <n-radio-button value="json">
            JSON
          </n-radio-button>
          <n-radio-button value="yaml">
            YAML
          </n-radio-button>
        </n-radio-group>
      </template>
      <n-code :code="snapshotText" word-wrap />
      <template #footer>
        <n-button type="primary" @click="download(format)">
          <template #icon>
            <icon-park-outline-download />
          </template>
          导出
        </n-button>
      </template>
    </n-drawer-content>
  </n-drawer>
</template>
