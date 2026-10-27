<script setup lang="ts">
// 工作台布局树的递归渲染：容器排布子节点，组件从工作台上下文取数据与命令
import type { CSSProperties } from 'vue'
import type { LayoutNode } from './layout'
// 别名导入：模板里仍按 n-xxx 用全局注册的组件
import { NDatePicker as CellDate, NInput as CellInput, NInputNumber as CellNumber, useThemeVars } from 'naive-ui'
import { WORKBENCH } from './context'
import { COMPONENT_ICONS } from './icons'
import { ALIGN, defOf, flexOf, gapOf, JUSTIFY } from './layout'

const props = defineProps<{ node: LayoutNode }>()
const ctx = inject(WORKBENCH)!
const themeVars = useThemeVars()
const n = computed(() => props.node)

const horizontal = computed(() => n.value.type === 'List' && n.value.attrs.direction === 'horizontal')
const gap = computed(() => `${gapOf(n.value)}px`)

/** 子节点在父容器里的尺寸（只控制尺寸，不覆盖子节点自身的 display）：列表按占比分配剩余空间，网格按跨行 / 跨列 */
function childStyle(c: LayoutNode): CSSProperties {
  if (n.value.type === 'Grid') {
    const rows = Number(n.value.attrs.rows ?? 0)
    return {
      gridColumn: `span ${Math.min(Number(c.attrs.colSpan ?? 1), Number(n.value.attrs.columns ?? 2))}`,
      gridRow: `span ${rows ? Math.min(Number(c.attrs.rowSpan ?? 1), rows) : Number(c.attrs.rowSpan ?? 1)}`,
      minWidth: 0,
      minHeight: 0,
    }
  }
  if (n.value.type === 'ButtonBar')
    return { flex: c.type === 'Spacer' ? '1 1 0' : 'none' }
  return { flex: flexOf(c, n.value, Number.parseInt(gap.value)), minWidth: 0, minHeight: 0 }
}
const containerStyle = computed<CSSProperties>(() => {
  if (n.value.type === 'Grid') {
    return {
      display: 'grid',
      gap: gap.value,
      gridTemplateColumns: `repeat(${Number(n.value.attrs.columns ?? 2)}, minmax(0, 1fr))`,
      ...(Number(n.value.attrs.rows) ? { gridTemplateRows: `repeat(${Number(n.value.attrs.rows)}, minmax(0, 1fr))` } : { gridAutoRows: 'minmax(min-content, 1fr)' }),
    }
  }
  if (n.value.type === 'ButtonBar')
    return { display: 'flex', flexWrap: 'wrap', gap: gap.value, justifyContent: JUSTIFY[n.value.attrs.align ?? 'start'], alignItems: ALIGN[n.value.attrs.valign ?? 'center'] }
  return { display: 'flex', gap: gap.value, flexDirection: horizontal.value ? 'row' : 'column', flexWrap: horizontal.value && Number(n.value.attrs.columns) ? 'wrap' : 'nowrap' }
})

const fields = computed(() => n.value.fields ?? [])
// 表单值由工作台按表单名预先建好，这里只读写字段
const values = computed(() => ctx.forms[n.value.attrs.name] ?? {})
const options = (s?: string) => (s ?? '').split(',').filter(Boolean).map(o => ({ label: o, value: o }))
// 表格行由工作台按表格名建好；表格可编辑时，勾选可编辑的列渲染为输入控件
const tableRows = computed(() => ctx.tables[n.value.attrs.name] ?? [])
type Row = Record<string, unknown>
function cell(key: string, type?: string) {
  return (row: Row) => {
    if (type === 'number')
      return h(CellNumber, { 'size': 'small', 'value': row[key] as number, 'showButton': false, 'onUpdate:value': (v: number | null) => row[key] = v })
    if (type === 'date')
      return h(CellDate, { 'size': 'small', 'type': 'date', 'formattedValue': row[key] as string, 'valueFormat': 'yyyy-MM-dd', 'onUpdate:formattedValue': (v: string | null) => row[key] = v })
    return h(CellInput, { 'size': 'small', 'value': row[key] as string, 'onUpdate:value': (v: string) => row[key] = v })
  }
}
const tableColumns = computed(() => (n.value.columns ?? []).map(c => ({
  key: c.key,
  title: c.title,
  width: c.width ? Number(c.width) : undefined,
  ...(n.value.attrs.editable === 'true' && c.editable ? { render: cell(c.key, c.type) } : { ellipsis: { tooltip: true } }),
})))
</script>

<template>
  <!-- 容器 -->
  <div v-if="['Workbench', 'List', 'Grid', 'ButtonBar'].includes(n.type)" class="min-h-0 min-w-0" :class="{ 'flex-1': n.type !== 'ButtonBar' }" :style="containerStyle">
    <WorkbenchNode v-for="c in n.children" :key="c.id" :node="c" :style="childStyle(c)" />
  </div>
  <n-card v-else-if="n.type === 'Panel'" size="small" :title="n.attrs.title" class="min-h-0 flex-1" content-class="flex min-h-0 flex-col gap-3 overflow-auto">
    <WorkbenchNode v-for="c in n.children" :key="c.id" :node="c" :style="childStyle(c)" />
  </n-card>

  <span v-else-if="n.type === 'Spacer'" />

  <n-dropdown
    v-else-if="n.type === 'Button' && n.v === 'export'"
    trigger="click"
    :options="[{ key: 'export-json', label: 'JSON' }, { key: 'export-yaml', label: 'YAML' }]"
    @select="(k: string) => ctx.run(k)"
  >
    <n-button size="small" quaternary>
      <template #icon>
        <n-icon :component="COMPONENT_ICONS['Button:export']" />
      </template>
      导出
    </n-button>
  </n-dropdown>
  <n-button
    v-else-if="n.type === 'Button'"
    size="small"
    :type="n.v === 'submit' ? 'primary' : 'default'"
    :quaternary="!['save', 'submit'].includes(n.v!)"
    :disabled="(n.v === 'prev' && !ctx.hasPrev.value) || (n.v === 'next' && !ctx.hasNext.value)"
    :loading="ctx.loading.value && ['save', 'submit'].includes(n.v!)"
    @click="ctx.run(n.v!)"
  >
    <template #icon>
      <n-icon :component="COMPONENT_ICONS[`Button:${n.v}`]" />
    </template>
    {{ n.v === 'submit' && ctx.hasNext.value ? '提交并下一份' : defOf(n)?.label }}{{ n.v === 'log' && ctx.logs.value.length ? ` ${ctx.logs.value.length}` : '' }}
  </n-button>

  <div
    v-else-if="n.type === 'Canvas'"
    class="min-h-80 flex-1 overflow-hidden rounded"
    :style="{ border: `1px solid ${themeVars.borderColor}` }"
  >
    <AnnotationCanvas
      v-if="ctx.canvas.config.value"
      :ref="ctx.setCanvas"
      :config="ctx.canvas.config.value"
      :data="ctx.canvas.data.value"
      :result="ctx.canvas.result.value"
    />
  </div>

  <n-form v-else-if="n.type === 'Form'" :model="values" label-placement="top" size="small">
    <n-grid :cols="Number(n.attrs.columns ?? 2)" :x-gap="18">
      <n-form-item-gi
        v-for="f in fields"
        :key="f.name"
        :label="f.label"
        :path="f.name"
        :show-require-mark="!!f.required"
        :span="f.type === 'textarea' ? Number(n.attrs.columns ?? 2) : 1"
      >
        <n-input v-if="f.type === 'text'" v-model:value="values[f.name] as string" />
        <n-input v-else-if="f.type === 'textarea'" v-model:value="values[f.name] as string" type="textarea" :rows="2" />
        <n-input-number v-else-if="f.type === 'number'" v-model:value="values[f.name] as number" class="w-full" />
        <n-select v-else-if="f.type === 'select'" v-model:value="values[f.name] as string" :options="options(f.options)" clearable />
        <n-radio-group v-else-if="f.type === 'radio'" v-model:value="values[f.name] as string">
          <n-radio v-for="o in options(f.options)" :key="o.value" :value="o.value" :label="o.label" />
        </n-radio-group>
        <n-checkbox-group v-else-if="f.type === 'checkbox'" v-model:value="values[f.name] as string[]">
          <n-checkbox v-for="o in options(f.options)" :key="o.value" :value="o.value" :label="o.label" />
        </n-checkbox-group>
        <n-date-picker v-else-if="f.type === 'date'" v-model:formatted-value="values[f.name] as string" type="date" value-format="yyyy-MM-dd" class="w-full" />
        <n-switch v-else-if="f.type === 'switch'" v-model:value="values[f.name] as boolean" />
      </n-form-item-gi>
    </n-grid>
  </n-form>

  <n-data-table
    v-else-if="n.type === 'DataTable'"
    size="small"
    :columns="tableColumns"
    :data="tableRows"
    :bordered="false"
    flex-height
    class="min-h-50"
  />
</template>
