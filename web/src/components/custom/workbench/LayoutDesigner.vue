<script setup lang="ts">
// 工作台拖拽布局设计器：与 XML 编辑器编辑同一份模板，v-model 为模板 XML
import type { DropdownOption } from 'naive-ui'
import type { ColumnDef, ComponentDef, FieldDef, Kind, LayoutNode } from './layout'
import { useThemeVars } from 'naive-ui'
import { confirmDialog, message } from '@/utils'
import ComponentPreview from './ComponentPreview.vue'
import DesignerNode from './DesignerNode.vue'
import { COMPONENT_ICONS } from './icons'
import { canDrop, cloneNode, COMPONENTS, CONTAINERS, createNode, defOf, FIELD_TYPES, growsIn, isHorizontalList, isLs, nodeLabel, normalizeSize, objectNames, parseLayout, serializeLayout, sizeConflict, SIZES, walk } from './layout'

const props = defineProps<{ readonly?: boolean }>()
const xml = defineModel<string>({ required: true })

const themeVars = useThemeVars()
const root = ref<LayoutNode | null>(null)
const error = ref('')
const selected = ref('')
let emitted = ''
// 由 XML 载入时不回写，只有设计器内的修改才更新 XML（旧 <View> 模板打开后不会被改写）
let loading = false

// 先注册布局监听，初次载入也会经过它并复位 loading
watch(root, (value) => {
  if (loading || !value) {
    loading = false
    return
  }
  emitted = serializeLayout(value)
  xml.value = emitted
}, { deep: true })
watch(xml, (value) => {
  if (value === emitted)
    return
  try {
    loading = true
    root.value = parseLayout(value)
    error.value = ''
  }
  catch (e) {
    root.value = null
    error.value = `XML 不能转为布局：${(e as Error).message}`
  }
}, { immediate: true })

const all = computed(() => root.value ? walk(root.value) : [])
const groups = computed(() => [...new Set(COMPONENTS.map(c => c.group))].map(g => [g, COMPONENTS.filter(c => c.group === g)] as const))
const used = (def: ComponentDef) => !!def.unique && all.value.some(n => defOf(n)?.key === def.key)
const parentOf = (id: string) => all.value.find(n => n.children?.some(c => c.id === id))
function remove(id: string) {
  const parent = parentOf(id)
  if (parent)
    parent.children = parent.children!.filter(c => c.id !== id)
  if (selected.value === id)
    selected.value = ''
}
/** 数字属性在 XML 中是字符串 */
const num = (n: LayoutNode, k: string, d: number) => Number(n.attrs[k] ?? d)
const setNum = (n: LayoutNode, k: string, v: number | null) => n.attrs[k] = String(v ?? '')

/** 列表、面板、根里会伸展的子节点可设占比 */
const sizable = (node: LayoutNode, parent: LayoutNode) => ['List', 'Workbench', 'Panel'].includes(parent.type) && growsIn(node, parent)
/** 横向列表既设了列数、子节点又设了占比时，让用户选一种布局 */
function resolveConflict(list: LayoutNode) {
  if (!sizeConflict(list))
    return
  confirmDialog({
    title: '布局冲突',
    content: '该横向列表设置了列数，其中的组件又设置了占比，使用哪种布局？',
    positiveText: '按列数',
    negativeText: '按占比',
    closable: false,
    maskClosable: false,
    onPositiveClick: () => list.children!.forEach(c => delete c.attrs.size),
    onNegativeClick: () => {
      delete list.attrs.columns
    },
  })
}
function setSize(node: LayoutNode, parent: LayoutNode, value?: string | null) {
  const size = value ? normalizeSize(value) : ''
  if (value && !size)
    return message.warning('占比请输入 1–100 之间的百分比')
  if (size)
    node.attrs.size = size
  else
    delete node.attrs.size
  resolveConflict(parent)
}
function setColumns(list: LayoutNode, v: number | null) {
  if (v)
    list.attrs.columns = String(v)
  else
    delete list.attrs.columns
  resolveConflict(list)
}

// 右键菜单：结构操作与跨行 / 跨列、占比的快捷设置
const menu = reactive({ show: false, x: 0, y: 0, id: '' })
function openMenu(e: MouseEvent, id: string) {
  if (props.readonly)
    return
  selected.value = id
  Object.assign(menu, { show: true, x: e.clientX, y: e.clientY, id })
}
const range = (n: number) => Array.from({ length: n }, (_, i) => i + 1)
const menuOptions = computed<DropdownOption[]>(() => {
  const node = all.value.find(n => n.id === menu.id)
  const parent = node && parentOf(node.id)
  if (!node || !parent)
    return []
  const i = parent.children!.indexOf(node)
  const opts: DropdownOption[] = []
  if (parent.type === 'Grid') {
    const cols = num(parent, 'columns', 2)
    opts.push(
      { key: 'span', label: '跨列', children: range(cols).map(v => ({ key: `colSpan:${v}`, label: `${v} 列` })) },
      { key: 'rspan', label: '跨行', children: range(Number(parent.attrs.rows) || 4).map(v => ({ key: `rowSpan:${v}`, label: `${v} 行` })) },
    )
  }
  if (sizable(node, parent))
    opts.push({ key: 'size', label: '占比', children: [{ key: 'size:', label: '自动' }, ...SIZES.map(v => ({ key: `size:${v}`, label: v })), { key: 'size-custom', label: '自定义…' }] })
  if (opts.length)
    opts.push({ type: 'divider', key: 'd1' })
  opts.push(
    { key: 'up', label: '上移', disabled: i === 0 },
    { key: 'down', label: '下移', disabled: i === parent.children!.length - 1 },
    { key: 'copy', label: '复制', disabled: !root.value || !cloneNode(node, root.value) },
    { key: 'parent', label: '选中上级', disabled: parent.type === 'Workbench' },
    { type: 'divider', key: 'd2' },
    { key: 'remove', label: '删除' },
  )
  return opts
})
function onMenu(key: string) {
  menu.show = false
  const node = all.value.find(n => n.id === menu.id)!
  const parent = parentOf(node.id)!
  const list = parent.children!
  const i = list.indexOf(node)
  const [attr, value] = key.split(':')
  if (attr === 'size')
    setSize(node, parent, value)
  else if (value !== undefined)
    node.attrs[attr] = value
  else if (key === 'size-custom')
    selected.value = node.id
  else if (key === 'up' || key === 'down')
    list.splice(key === 'up' ? i - 1 : i + 1, 0, ...list.splice(i, 1))
  else if (key === 'copy')
    list.splice(i + 1, 0, cloneNode(node, root.value!)!)
  else if (key === 'parent')
    selected.value = parent.id
  else if (key === 'remove')
    remove(node.id)
}
// 拖放：自己计算落点。光标靠近组件的上 / 下 / 左 / 右边 → 插到那一侧；光标在容器内部 → 放进该容器（高亮整个容器）
// 插到与父容器排列方向垂直的一侧时，把目标与新组件包进一个列表，两者各占一半
type Side = 'top' | 'bottom' | 'left' | 'right'
interface DropHint {
  /** fill：放进容器末尾；seq：在父容器中按顺序插入；wrap：与目标一起包进新列表 */
  mode: 'fill' | 'seq' | 'wrap'
  targetId: string
  side?: Side
  style: Record<string, string>
}
const drag = ref<{ key?: string, id?: string } | null>(null)
const hint = ref<DropHint | null>(null)
const byId = (id?: string) => all.value.find(n => n.id === id)
const EDGE = 16
/** 子节点沿横向排列的容器 */
const horizontalOf = (n: LayoutNode) => n.type === 'ButtonBar' || n.type === 'Grid' || (n.type === 'List' && n.attrs.direction === 'horizontal')
/** 只能按顺序插入、不能包一层列表的容器 */
const SEQ_ONLY = ['ButtonBar', 'Canvas']
const px = (v: number) => `${v}px`

function startDrag(e: DragEvent, from: { key?: string, id?: string }) {
  if (props.readonly)
    return e.preventDefault()
  e.dataTransfer!.effectAllowed = from.id ? 'move' : 'copy'
  e.dataTransfer!.setData('text/plain', from.id ?? from.key ?? '')
  drag.value = from
}
function endDrag() {
  drag.value = null
  hint.value = null
}

/** 光标最靠近的一边；容器只认 16px 边缘带，带外返回 null（放进容器） */
function nearestSide(r: DOMRect, x: number, y: number, edgeOnly: boolean): Side | null {
  const d: [Side, number, number][] = [['left', x - r.left, r.width], ['right', r.right - x, r.width], ['top', y - r.top, r.height], ['bottom', r.bottom - y, r.height]]
  if (edgeOnly) {
    const [side, dist] = d.reduce((a, b) => b[1] < a[1] ? b : a)
    return dist <= EDGE ? side : null
  }
  return d.reduce((a, b) => b[1] / b[2] < a[1] / a[2] ? b : a)[0]
}
function sideStyle(r: DOMRect, side: Side, half: boolean) {
  if (half) {
    const w = side === 'left' || side === 'right' ? r.width / 2 : r.width
    const h = side === 'top' || side === 'bottom' ? r.height / 2 : r.height
    return { left: px(side === 'right' ? r.right - w : r.left), top: px(side === 'bottom' ? r.bottom - h : r.top), width: px(w), height: px(h) }
  }
  return side === 'left' || side === 'right'
    ? { left: px((side === 'left' ? r.left : r.right) - 1), top: px(r.top), width: '3px', height: px(r.height) }
    : { left: px(r.left), top: px((side === 'top' ? r.top : r.bottom) - 1), width: px(r.width), height: '3px' }
}

function resolveDrop(e: DragEvent): DropHint | null {
  const d = drag.value
  const kind: Kind | undefined = d?.key ? COMPONENTS.find(c => c.key === d.key)?.kind : defOf(byId(d?.id) ?? { type: '', attrs: {} })?.kind
  if (!d || !kind)
    return null
  // 不能把节点拖进它自己或子孙里
  const banned = new Set(d.id ? walk(byId(d.id)!).map(n => n.id) : [])
  // 按钮、状态项、间隔放进按钮栏以外的容器时，松手后自动包一层按钮栏
  const accepts = (type: string) => canDrop(type, kind) || (kind === 'item' && canDrop(type, 'bar'))
  let el = (e.target as HTMLElement).closest<HTMLElement>('[data-node]')
  while (el) {
    const node = byId(el.dataset.node)!
    const parent = parentOf(node.id)
    const isBox = CONTAINERS.includes(node.type) || node.type === 'Canvas'
    const r = el.getBoundingClientRect()
    if (!banned.has(node.id)) {
      const fillable = isBox && accepts(node.type)
      if (parent && accepts(parent.type)) {
        // 容器内部可放时只在边缘带内插到旁边；普通组件与不收该组件的容器按最近的一边
        const side = nearestSide(r, e.clientX, e.clientY, fillable)
        if (side) {
          const along = (side === 'left' || side === 'right') === horizontalOf(parent)
          const wrap = !along && !SEQ_ONLY.includes(parent.type)
          return { mode: wrap ? 'wrap' : 'seq', targetId: node.id, side, style: sideStyle(r, side, wrap) }
        }
      }
      if (fillable) {
        const box = (el.querySelector(':scope > .drop') ?? el).getBoundingClientRect()
        return { mode: 'fill', targetId: node.id, style: { left: px(box.left), top: px(box.top), width: px(box.width), height: px(box.height) } }
      }
    }
    el = el.parentElement?.closest<HTMLElement>('[data-node]') ?? null
  }
  return null
}
function onDragOver(e: DragEvent) {
  hint.value = resolveDrop(e)
  if (hint.value)
    e.preventDefault()
}
function onDrop(e: DragEvent) {
  e.preventDefault()
  const h = hint.value
  const d = drag.value
  endDrag()
  const target = byId(h?.targetId)
  if (!h || !d || !target || !root.value)
    return
  // 先取出（移动）或新建要放下的节点
  let node: LayoutNode
  if (d.id) {
    node = byId(d.id)!
    const from = parentOf(d.id)!
    from.children!.splice(from.children!.indexOf(node), 1)
  }
  else {
    const def = COMPONENTS.find(c => c.key === d.key)!
    if (used(def))
      return
    node = createNode(def, root.value)
  }
  const intoBar = (dest: LayoutNode) => {
    if (defOf(node)?.kind !== 'item' || dest.type === 'ButtonBar')
      return node
    const bar = createNode(COMPONENTS.find(c => c.key === 'ButtonBar')!, root.value!)
    bar.children = [node]
    return bar
  }
  if (h.mode === 'fill') {
    target.children!.push(intoBar(target))
  }
  else {
    const parent = parentOf(target.id)!
    const i = parent.children!.indexOf(target)
    const before = h.side === 'top' || h.side === 'left'
    if (h.mode === 'seq') {
      parent.children!.splice(before ? i : i + 1, 0, intoBar(parent))
    }
    else {
      // 包一层与该侧方向一致的列表，原来的占比、跨行跨列交给外层，两者各占一半
      const { size, colSpan, rowSpan, ...rest } = target.attrs
      target.attrs = rest
      const wrapper = createNode(COMPONENTS.find(c => c.key === (h.side === 'left' || h.side === 'right' ? 'List:horizontal' : 'List:vertical'))!, root.value)
      Object.assign(wrapper.attrs, Object.fromEntries(Object.entries({ size, colSpan, rowSpan }).filter(([, v]) => v)))
      const placed = intoBar(wrapper)
      wrapper.children = before ? [placed, target] : [target, placed]
      parent.children!.splice(i, 1, wrapper)
    }
  }
  selected.value = node.id
}
provide('designer', { selected, readonly: computed(() => !!props.readonly), remove, menu: openMenu, startDrag, endDrag })

const current = computed(() => {
  const node = all.value.find(n => n.id === selected.value && n.type !== 'Workbench')
  return node ? { node, def: defOf(node), parent: parentOf(node.id)! } : null
})
const canvas = computed(() => current.value?.parent.type === 'Canvas' ? current.value.parent : undefined)
const valueAttr = (n: LayoutNode) => 'valueList' in n.attrs ? 'valueList' : 'value'
const optList = (opts?: string) => (opts ?? '').split(',').filter(Boolean)
const addField = (n: LayoutNode) => n.fields!.push({ name: `field_${n.fields!.length + 1}`, label: '新字段', type: 'text' } as FieldDef)
const addColumn = (n: LayoutNode) => n.columns!.push({ key: `col_${n.columns!.length + 1}`, title: '新列' } as ColumnDef)
const fieldTypeOptions = Object.entries(FIELD_TYPES).map(([value, label]) => ({ value, label }))
const columnTypeOptions = [{ value: 'text', label: '文本' }, { value: 'number', label: '数字' }, { value: 'date', label: '日期' }]
</script>

<template>
  <n-alert v-if="error" type="error" :show-icon="false">
    {{ error }}
  </n-alert>
  <n-flex
    v-else-if="root"
    :wrap="false"
    :size="12"
    class="min-h-0"
    :style="{ '--wb-border': themeVars.borderColor, '--wb-primary': themeVars.primaryColor, '--wb-hover': themeVars.hoverColor, '--wb-error': themeVars.errorColor }"
  >
    <n-scrollbar class="w-50 shrink-0">
      <div v-for="[group, defs] in groups" :key="group" class="mb-3">
        <n-text depth="3" class="text-xs">
          {{ group }}
        </n-text>
        <div class="mt-1 flex flex-wrap gap-1.5">
          <!-- 拖动时关闭悬停预览，避免预览浮层挡住放置区 -->
          <n-popover v-for="def in defs" :key="def.key" trigger="hover" placement="right" :delay="1000" :width="260" :disabled="!!drag">
            <template #trigger>
              <div
                class="palette-chip"
                :class="{ 'is-used': used(def) }"
                :draggable="!readonly && !used(def)"
                @dragstart="startDrag($event, { key: def.key })"
                @dragend="endDrag"
              >
                <n-icon :component="COMPONENT_ICONS[def.key]" :size="14" />
                {{ def.label }}
              </div>
            </template>
            <ComponentPreview :def="def" />
          </n-popover>
        </div>
      </div>
    </n-scrollbar>

    <n-scrollbar class="min-w-0 flex-1" content-class="h-full">
      <div class="h-full" @dragover="onDragOver" @drop="onDrop" @dragleave.self="hint = null">
        <DesignerNode :node="root" />
      </div>
    </n-scrollbar>
    <div v-if="hint" class="drop-hint" :class="{ 'is-fill': hint.mode === 'fill', 'is-half': hint.mode === 'wrap' }" :style="hint.style" />

    <n-scrollbar class="w-72 shrink-0">
      <n-form v-if="current" label-placement="left" :label-width="64" size="small" :disabled="readonly">
        <n-form-item label="组件">
          {{ nodeLabel(current.node) }}
        </n-form-item>

        <n-form-item v-if="current.node.type === 'List'" label="方向">
          <n-radio-group v-model:value="current.node.attrs.direction">
            <n-radio value="horizontal" label="横向" />
            <n-radio value="vertical" label="纵向" />
          </n-radio-group>
        </n-form-item>
        <n-form-item v-if="isHorizontalList(current.node)" label="列数">
          <n-input-number :value="Number(current.node.attrs.columns) || null" :min="1" :max="12" placeholder="不设则按占比" clearable @update:value="v => setColumns(current!.node, v)" />
        </n-form-item>
        <template v-if="current.node.type === 'Grid'">
          <n-form-item label="列数">
            <n-input-number :value="num(current.node, 'columns', 2)" :min="1" :max="6" @update:value="v => setNum(current!.node, 'columns', v)" />
          </n-form-item>
          <n-form-item label="行数">
            <n-input-number :value="num(current.node, 'rows', 0) || null" :min="1" :max="12" placeholder="自动" clearable @update:value="v => setNum(current!.node, 'rows', v)" />
          </n-form-item>
        </template>
        <template v-if="current.node.type === 'ButtonBar'">
          <n-form-item label="水平">
            <n-radio-group v-model:value="current.node.attrs.align" size="small">
              <n-radio-button value="start" label="左" />
              <n-radio-button value="center" label="中" />
              <n-radio-button value="end" label="右" />
              <n-radio-button value="between" label="分散" />
            </n-radio-group>
          </n-form-item>
          <n-form-item label="垂直">
            <n-radio-group v-model:value="current.node.attrs.valign" size="small">
              <n-radio-button value="top" label="上" />
              <n-radio-button value="center" label="中" />
              <n-radio-button value="bottom" label="下" />
            </n-radio-group>
          </n-form-item>
        </template>
        <n-form-item v-if="['List', 'Grid', 'ButtonBar'].includes(current.node.type)" label="间距">
          <n-input-number :value="num(current.node, 'gap', current.node.type === 'ButtonBar' || current.node.attrs.direction === 'horizontal' ? 8 : 12)" :min="0" :max="48" @update:value="v => setNum(current!.node, 'gap', v)" />
        </n-form-item>
        <n-form-item v-if="current.node.type === 'Panel'" label="标题">
          <n-input v-model:value="current.node.attrs.title" />
        </n-form-item>
        <template v-if="current.parent.type === 'Grid'">
          <n-form-item label="跨列">
            <n-input-number :value="num(current.node, 'colSpan', 1)" :min="1" :max="num(current.parent, 'columns', 2)" @update:value="v => setNum(current!.node, 'colSpan', v)" />
          </n-form-item>
          <n-form-item label="跨行">
            <n-input-number :value="num(current.node, 'rowSpan', 1)" :min="1" :max="num(current.parent, 'rows', 0) || 12" @update:value="v => setNum(current!.node, 'rowSpan', v)" />
          </n-form-item>
        </template>
        <n-form-item v-if="sizable(current.node, current.parent)" label="占比">
          <n-select
            :value="current.node.attrs.size || null"
            :options="SIZES.map(v => ({ label: v, value: v }))"
            placeholder="自动，可输入百分比"
            filterable
            tag
            clearable
            @update:value="(v: string | null) => setSize(current!.node, current!.parent, v)"
          />
        </n-form-item>

        <n-form-item v-if="current.node.type === 'Form' || current.node.type === 'DataTable'" label="名称">
          <n-input v-model:value="current.node.attrs.name" />
        </n-form-item>
        <template v-if="current.node.type === 'Form'">
          <n-form-item label="列数">
            <n-input-number :value="num(current.node, 'columns', 2)" :min="1" :max="4" @update:value="v => setNum(current!.node, 'columns', v)" />
          </n-form-item>
          <n-divider title-placement="left" class="my-2!">
            字段
          </n-divider>
          <n-card v-for="(f, i) in current.node.fields" :key="i" size="small" embedded class="mb-2" content-class="flex flex-col gap-2">
            <n-flex :wrap="false" :size="6">
              <n-input v-model:value="f.label" placeholder="标签" />
              <n-input v-model:value="f.name" placeholder="字段名" />
            </n-flex>
            <n-flex :wrap="false" :size="6" align="center">
              <n-select v-model:value="f.type" :options="fieldTypeOptions" class="flex-1" />
              <n-checkbox v-model:checked="f.required">
                必填
              </n-checkbox>
              <n-button text type="error" @click="current!.node.fields!.splice(i, 1)">
                <icon-park-outline-delete />
              </n-button>
            </n-flex>
            <n-input v-if="['select', 'radio', 'checkbox'].includes(f.type)" v-model:value="f.options" placeholder="选项，逗号分隔" />
          </n-card>
          <n-button dashed block @click="addField(current.node)">
            <template #icon>
              <icon-park-outline-plus />
            </template>
            添加字段
          </n-button>
        </template>
        <template v-if="current.node.type === 'DataTable'">
          <n-divider title-placement="left" class="my-2!">
            列
          </n-divider>
          <n-card v-for="(c, i) in current.node.columns" :key="i" size="small" embedded class="mb-2" content-class="flex flex-col gap-2">
            <n-flex :wrap="false" :size="6">
              <n-input v-model:value="c.title" placeholder="列名称" />
              <n-input v-model:value="c.key" placeholder="字段" />
            </n-flex>
            <n-flex :wrap="false" :size="6" align="center">
              <n-select v-model:value="c.type" :options="columnTypeOptions" placeholder="类型" clearable class="flex-1" />
              <n-input v-model:value="c.width" placeholder="宽度" class="w-20!" />
              <n-button text type="error" @click="current!.node.columns!.splice(i, 1)">
                <icon-park-outline-delete />
              </n-button>
            </n-flex>
          </n-card>
          <n-button dashed block @click="addColumn(current.node)">
            <template #icon>
              <icon-park-outline-plus />
            </template>
            添加列
          </n-button>
        </template>

        <template v-if="isLs(current.def?.kind)">
          <n-form-item v-if="current.def!.kind === 'vis'" label="文字">
            <n-input v-model:value="current.node.attrs.value" />
          </n-form-item>
          <n-form-item v-else label="name">
            <n-input v-model:value="current.node.attrs.name" />
          </n-form-item>
          <n-form-item v-if="current.def!.kind === 'obj'" label="数据">
            <n-input v-model:value="current.node.attrs[valueAttr(current.node)]" placeholder="$变量" />
          </n-form-item>
          <n-form-item v-if="current.def!.kind === 'ctl'" label="toName">
            <n-select v-model:value="current.node.attrs.toName" :options="objectNames(canvas).map(v => ({ label: v, value: v }))" />
          </n-form-item>
          <n-form-item v-if="current.node.opts !== undefined" label="选项">
            <n-dynamic-tags :value="optList(current.node.opts)" @update:value="(v: string[]) => current!.node.opts = v.join(',')" />
          </n-form-item>
        </template>
        <n-code v-if="current.node.type === 'Raw'" :code="current.node.xml" word-wrap />
      </n-form>
      <n-empty v-else size="small" description="选中组件编辑属性" class="mt-10" />
    </n-scrollbar>
    <n-dropdown
      trigger="manual"
      placement="bottom-start"
      size="small"
      :show="menu.show"
      :x="menu.x"
      :y="menu.y"
      :options="menuOptions"
      @select="onMenu"
      @clickoutside="menu.show = false"
    />
  </n-flex>
</template>

<style scoped>
.palette-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border: 1px solid var(--wb-border);
  border-radius: 3px;
  font-size: 12px;
  line-height: 20px;
  cursor: grab;
}
.palette-chip:hover {
  background: var(--wb-hover);
}
.drop-hint {
  position: fixed;
  z-index: 10;
  pointer-events: none;
  border-radius: 2px;
  background: var(--wb-primary);
}
.drop-hint.is-fill,
.drop-hint.is-half {
  background: transparent;
  border: 2px solid var(--wb-primary);
  box-shadow: inset 0 0 0 9999px color-mix(in srgb, var(--wb-primary) 12%, transparent);
}
.palette-chip.is-used {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>
