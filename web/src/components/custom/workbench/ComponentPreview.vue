<script setup lang="ts">
// 组件库悬停预览：用样例数据画出组件外观
import type { ColumnDef, ComponentDef } from './layout'
import { useThemeVars } from 'naive-ui'
import { mockRows } from './layout'

const props = defineProps<{ def: ComponentDef }>()
const themeVars = useThemeVars()
const k = computed(() => props.def.key)
const opts = computed(() => (props.def.opts ?? '').split(',').filter(Boolean))
const box = computed(() => ({ border: `1px dashed ${themeVars.value.borderColor}`, borderRadius: '3px', minHeight: '28px' }))
const columns: ColumnDef[] = [{ key: 'seq', title: '序号', type: 'number', width: '60' }, { key: 'title', title: '文件题名' }]
const tableColumns = columns.map(c => ({ key: c.key, title: c.title }))
const DOC_TYPES = ['Canvas', 'Image', 'Rectangle', 'RectangleLabels', 'PolygonLabels', 'KeyPointLabels', 'BrushLabels']
</script>

<template>
  <n-flex vertical :size="8">
    <n-text depth="3" class="text-xs">
      {{ def.label }} · {{ def.key }}
    </n-text>
    <div v-if="k === 'Grid'" class="grid grid-cols-2 gap-1.5">
      <div v-for="i in 4" :key="i" :style="box" />
    </div>
    <div v-else-if="k.startsWith('List:')" class="flex gap-1.5" :class="k === 'List:vertical' ? 'flex-col' : ''">
      <div v-for="i in 3" :key="i" class="flex-1" :style="box" />
    </div>
    <n-card v-else-if="k === 'Panel'" size="small" title="面板">
      <div :style="box" />
    </n-card>
    <n-flex v-else-if="k === 'ButtonBar'" justify="space-between" align="center" class="rounded p-1.5" :style="box">
      <n-button size="tiny" quaternary>
        撤销
      </n-button>
      <n-button size="tiny" quaternary>
        查看数据
      </n-button>
      <n-button size="tiny" type="primary">
        提交
      </n-button>
    </n-flex>
    <div v-else-if="k === 'Spacer'" class="flex flex-col gap-1.5">
      <n-card size="small" title="面板" />
      <div class="h-6 border-y border-dashed" :style="{ borderColor: themeVars.textColor3 }" />
      <n-card size="small" title="面板" />
    </div>
    <n-form v-else-if="k === 'Form'" label-placement="top" size="small" :show-feedback="false" class="flex flex-col gap-2">
      <n-form-item label="题名" show-require-mark>
        <n-input value="关于开展档案数字化质量检查的通知" />
      </n-form-item>
      <n-form-item label="密级">
        <n-select value="公开" :options="[{ label: '公开', value: '公开' }]" />
      </n-form-item>
    </n-form>
    <n-data-table v-else-if="k === 'DataTable'" size="small" :columns="tableColumns" :data="mockRows(columns, 3)" />
    <n-button v-else-if="k.startsWith('Button:')" size="small" :type="k === 'Button:submit' ? 'primary' : 'default'" class="self-start">
      {{ def.label }}
    </n-button>
    <svg v-else-if="DOC_TYPES.includes(k)" viewBox="0 0 120 160" width="120" class="self-center">
      <rect width="120" height="160" fill="#fbfaf6" :stroke="themeVars.borderColor" />
      <rect x="20" y="16" width="80" height="6" fill="#b3312a" />
      <rect v-for="i in 6" :key="i" x="16" :y="30 + i * 12" :width="i % 3 ? 88 : 56" height="4" fill="#d6d3ca" />
      <circle cx="88" cy="128" r="16" fill="none" stroke="#c8413a" stroke-width="1.5" />
      <rect v-if="k === 'Rectangle' || k === 'RectangleLabels'" x="68" y="108" width="40" height="40" :fill="themeVars.primaryColor" fill-opacity="0.15" :stroke="themeVars.primaryColor" stroke-width="1.5" />
      <polygon v-if="k === 'PolygonLabels'" points="14,36 104,32 108,100 18,104" :fill="themeVars.primaryColor" fill-opacity="0.15" :stroke="themeVars.primaryColor" stroke-width="1.5" />
      <circle v-for="[x, y] in k === 'KeyPointLabels' ? [[16, 12], [104, 12], [104, 148], [16, 148]] : []" :key="x + y" :cx="x" :cy="y" r="3" :fill="themeVars.errorColor" />
      <path v-if="k === 'BrushLabels'" d="M20 120 C 40 80, 70 140, 100 90" :stroke="themeVars.warningColor" stroke-opacity="0.6" stroke-width="10" fill="none" stroke-linecap="round" />
    </svg>
    <n-p v-else-if="k === 'Text'" class="m-0">
      2026 年 8 月，四川星辰信息技术有限公司向成华区市场监管局提交设立登记申请。
    </n-p>
    <n-p v-else-if="k === 'Labels'" class="m-0">
      <n-tag size="small" type="primary">
        张明
      </n-tag> 向 <n-tag size="small" type="success">
        成华区市场监管局
      </n-tag> 提交申请。
    </n-p>
    <div v-else-if="k === 'HyperText'" class="rounded p-2" :style="{ border: `1px solid ${themeVars.borderColor}` }">
      <b>通知</b>：请于 <u>11 月 1 日</u>前完成整理。
    </div>
    <svg v-else-if="k === 'Audio'" viewBox="0 0 200 32" width="200">
      <rect v-for="(h, i) in [8, 20, 12, 26, 10, 18, 24, 6, 16, 22, 9, 19, 14, 25, 7, 17]" :key="i" :x="i * 12 + 4" :y="16 - h / 2" width="6" :height="h" rx="2" :fill="themeVars.primaryColor" />
    </svg>
    <div v-else-if="k === 'Video'" class="aspect-video flex-center rounded bg-black text-white">
      ▶
    </div>
    <n-radio-group v-else-if="k === 'Choices'" :value="opts[0]">
      <n-radio v-for="o in opts" :key="o" :value="o" :label="o" />
    </n-radio-group>
    <n-tree v-else-if="k === 'Taxonomy'" :data="opts.map(o => ({ key: o, label: o, children: [{ key: `${o}-1`, label: `${o} · 子类` }] }))" default-expand-all checkable />
    <n-input v-else-if="k === 'TextArea'" type="textarea" :rows="2" value="关于开展档案数字化质量检查的通知" />
    <n-input-number v-else-if="k === 'Number'" :value="30" />
    <n-date-picker v-else-if="k === 'DateTime'" :value="1786406400000" type="date" />
    <n-rate v-else-if="k === 'Rating'" :value="4" />
    <n-h4 v-else-if="k === 'Header'" class="m-0">
      标题
    </n-h4>
    <n-flex v-if="k.endsWith('Labels')" :size="4">
      <n-tag v-for="o in opts" :key="o" size="small" type="primary">
        {{ o }}
      </n-tag>
    </n-flex>
  </n-flex>
</template>
