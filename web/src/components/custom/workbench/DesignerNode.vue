<script setup lang="ts">
// 设计器里的一个容器（或画布）：递归渲染子节点；尺寸规则与工作台一致，子节点默认撑满所在位置
// 拖放落点由 LayoutDesigner 统一计算，这里只标记节点（data-node）并发起拖动
import type { CSSProperties, Ref } from 'vue'
import type { LayoutNode } from './layout'
import { COMPONENT_ICONS } from './icons'
import { ALIGN, CONTAINERS, defOf, flexOf, gapOf, JUSTIFY, nodeLabel, objectNames } from './layout'

const props = defineProps<{ node: LayoutNode }>()
const ctx = inject<{
  selected: Ref<string>
  readonly: Ref<boolean>
  remove: (id: string) => void
  menu: (e: MouseEvent, id: string) => void
  startDrag: (e: DragEvent, from: { id: string }) => void
  endDrag: () => void
}>('designer')!
const n = computed(() => props.node)
const isRoot = computed(() => n.value.type === 'Workbench')
const nested = (c: LayoutNode) => CONTAINERS.includes(c.type) || c.type === 'Canvas'
const flow = computed(() => {
  if (n.value.type === 'Grid')
    return 'is-grid'
  if (n.value.type === 'ButtonBar')
    return 'is-bar'
  if (n.value.type === 'List' && n.value.attrs.direction === 'horizontal')
    return Number(n.value.attrs.columns) ? 'is-row is-wrap' : 'is-row'
  return 'is-col'
})
const ALIGN_LABEL: Record<string, string> = { start: '左对齐', center: '居中', end: '右对齐', between: '分散' }
const title = computed(() => {
  const base = n.value.type === 'Canvas' ? '画布 · Label Studio' : nodeLabel(n.value)
  if (n.value.type === 'Grid')
    return `${base} · ${n.value.attrs.columns ?? 2} 列${Number(n.value.attrs.rows) ? ` × ${n.value.attrs.rows} 行` : ''}`
  if (n.value.type === 'ButtonBar')
    return `${base} · ${ALIGN_LABEL[n.value.attrs.align ?? 'start']}`
  if (n.value.type === 'List' && Number(n.value.attrs.columns))
    return `${base} · ${n.value.attrs.columns} 列`
  return n.value.type === 'Panel' && n.value.attrs.title ? `${base} · ${n.value.attrs.title}` : base
})
/** 与工作台一致：容器自己的间距，按钮栏自己的对齐方式 */
const dropStyle = computed<CSSProperties | undefined>(() => {
  const gap = `${gapOf(n.value)}px`
  if (n.value.type === 'ButtonBar')
    return { gap, justifyContent: JUSTIFY[n.value.attrs.align ?? 'start'], alignItems: ALIGN[n.value.attrs.valign ?? 'center'] }
  if (n.value.type !== 'Grid')
    return n.value.type === 'Canvas' ? undefined : { gap }
  const rows = Number(n.value.attrs.rows)
  return {
    gap,
    gridTemplateColumns: `repeat(${n.value.attrs.columns ?? 2}, minmax(0, 1fr))`,
    ...(rows ? { gridTemplateRows: `repeat(${rows}, minmax(40px, 1fr))` } : { gridAutoRows: 'minmax(40px, 1fr)' }),
  }
})
/** 与工作台相同：列表里会伸展的子节点按占比撑满，网格子节点按跨行跨列撑满单元格；画布内是 Label Studio 标签，不参与 */
function cellStyle(c: LayoutNode): CSSProperties | undefined {
  if (n.value.type === 'Grid')
    return { gridColumn: `span ${Math.min(Number(c.attrs.colSpan ?? 1), Number(n.value.attrs.columns ?? 2))}`, gridRow: `span ${c.attrs.rowSpan ?? 1}` }
  // 画布里的对象标签（图像、文本、音视频）撑满画布，控件按内容高度
  if (n.value.type === 'Canvas')
    return defOf(c)?.kind === 'obj' ? { flex: '1 1 0' } : undefined
  if (n.value.type === 'ButtonBar')
    return undefined
  return { flex: flexOf(c, n.value, gapOf(n.value)) }
}
const brokenToName = (c: LayoutNode) => defOf(c)?.kind === 'ctl' && !objectNames(n.value).includes(c.attrs.toName)
const select = (id: string) => ctx.selected.value = id
</script>

<template>
  <div
    class="box"
    :class="{ 'is-root': isRoot, 'is-on': ctx.selected.value === n.id }"
    :data-node="n.id"
    :draggable="!isRoot && !ctx.readonly.value"
    @dragstart.stop="ctx.startDrag($event, { id: n.id })"
    @dragend.stop="ctx.endDrag()"
    @click.stop="select(n.id)"
    @contextmenu.prevent.stop="!isRoot && ctx.menu($event, n.id)"
  >
    <n-flex v-if="!isRoot" align="center" :size="4" class="mb-1.5">
      <n-text depth="3" class="text-xs">
        {{ title }}
      </n-text>
      <n-button v-if="!ctx.readonly.value" text size="tiny" class="ml-auto" @click.stop="ctx.remove(n.id)">
        <icon-park-outline-close-small />
      </n-button>
    </n-flex>
    <div class="drop" :class="flow" :style="dropStyle">
      <template v-for="c in n.children" :key="c.id">
        <DesignerNode v-if="nested(c)" :node="c" :style="cellStyle(c)" />
        <div
          v-else
          class="chip"
          :class="{ 'is-on': ctx.selected.value === c.id, 'is-spacer': c.type === 'Spacer', 'is-block': n.type === 'Canvas' ? defOf(c)?.kind === 'obj' : n.type !== 'ButtonBar' && defOf(c)?.kind !== 'item' }"
          :style="cellStyle(c)"
          :data-node="c.id"
          :draggable="!ctx.readonly.value"
          @dragstart.stop="ctx.startDrag($event, { id: c.id })"
          @dragend.stop="ctx.endDrag()"
          @click.stop="select(c.id)"
          @contextmenu.prevent.stop="ctx.menu($event, c.id)"
        >
          <div class="chip-head">
            <span v-if="c.type === 'Spacer'">⟷</span>
            <template v-else>
              <n-icon v-if="COMPONENT_ICONS[defOf(c)?.key ?? '']" :component="COMPONENT_ICONS[defOf(c)?.key ?? '']" :size="13" />
              {{ nodeLabel(c) }}
            </template>
            <n-text v-if="c.attrs.name" depth="3" class="text-xs">
              {{ c.attrs.name }}
            </n-text>
            <n-tag v-if="n.type === 'Canvas' && brokenToName(c)" size="tiny" type="error">
              toName
            </n-tag>
            <n-button v-if="!ctx.readonly.value" text size="tiny" class="ml-auto" @click.stop="ctx.remove(c.id)">
              <icon-park-outline-close-small />
            </n-button>
          </div>
          <!-- 表单、表格在画板上显示字段 / 列，所见即所得 -->
          <div v-if="c.type === 'Form'" class="chip-body grid gap-x-3 gap-y-1" :style="{ gridTemplateColumns: `repeat(${c.attrs.columns ?? 2}, minmax(0, 1fr))` }">
            <n-text v-for="f in c.fields" :key="f.name" depth="3" class="truncate text-xs" :style="{ gridColumn: f.type === 'textarea' ? '1 / -1' : undefined }">
              <span v-if="f.required" class="mr-0.5" :style="{ color: 'var(--wb-error)' }">*</span>{{ f.label }}
            </n-text>
          </div>
          <div v-else-if="c.type === 'DataTable'" class="chip-body flex gap-3">
            <n-text v-for="col in c.columns" :key="col.key" depth="3" class="truncate text-xs" :style="{ flex: col.width ? `0 0 ${col.width}px` : '1' }">
              {{ col.title }}
            </n-text>
          </div>
        </div>
      </template>
    </div>
    <n-text v-if="isRoot && !n.children?.length" depth="3" class="pointer-events-none absolute inset-0 flex-center">
      从左侧拖入布局与组件
    </n-text>
  </div>
</template>

<style scoped>
.box {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  padding: 8px;
  border: 1px dashed var(--wb-border);
  border-radius: 4px;
  cursor: grab;
}
.box.is-root {
  position: relative;
  height: 100%;
  border-style: solid;
  cursor: default;
}
.box.is-on {
  border-color: var(--wb-primary);
}
.drop {
  flex: 1;
  gap: 6px;
  min-height: 40px;
}
.drop.is-col {
  display: flex;
  flex-direction: column;
}
.drop.is-row {
  display: flex;
}
.drop.is-wrap {
  flex-wrap: wrap;
}
.drop.is-row > * {
  min-width: 0;
}
.drop.is-grid {
  display: grid;
}
.drop.is-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}
.chip {
  display: inline-flex;
  align-items: center;
  min-width: 0;
  padding: 2px 8px;
  border: 1px solid var(--wb-border);
  border-radius: 3px;
  font-size: 12px;
  line-height: 20px;
  white-space: nowrap;
  cursor: grab;
}
/* 撑满的组件：标签放在左上角 */
.chip-head {
  display: flex;
  align-items: center;
  gap: 4px;
  width: 100%;
  min-width: 0;
}
.chip-body {
  width: 100%;
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px dashed var(--wb-border);
}
.chip.is-block {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  min-height: 40px;
  padding: 8px;
}
.chip.is-spacer {
  flex: 1;
  min-width: 48px;
}
/* 列表里的间隔是一段空白，画板上按实际长度显示 */
.chip.is-spacer.is-block {
  min-width: 0;
  min-height: 16px;
  padding: 0 8px;
  justify-content: center;
}
.chip:hover {
  background: var(--wb-hover);
}
.chip.is-on {
  border-color: var(--wb-primary);
  color: var(--wb-primary);
}
</style>
