<script setup lang="ts">
// Label Studio 编辑器的唯一接入点（docs/platform/annotation/labelstudio.md）：
// 编辑器在同源 iframe 中运行，其 React 与全局样式不影响控制台；换编辑器版本只改这里
// shortcut: 暂用 npm @heartexlabs/label-studio@1.4.0（1.8.0 的 npm 包缺少构建产物），汉化为运行时补译；改为 1.23.2 源码构建后替换 editorJs / editorCss
import editorCss from '@heartexlabs/label-studio/build/static/css/main.css?url'
import editorJs from '@heartexlabs/label-studio/build/static/js/main.js?url'
import { useAppStore } from '@/store'
import { checkTemplateXml } from './label-studio-schema'

const props = defineProps<{
  config: string
  data: Record<string, unknown>
  /** 已有标注结果（serializeAnnotation 的数组） */
  result?: Record<string, unknown>[] | null
}>()

const appStore = useAppStore()
const frame = ref<HTMLIFrameElement>()
// 1.4.0 在同一页面 destroy 后重建会残留上一份配置的布局（侧栏、画布），每次重渲染都换新 iframe
const frameKey = ref(0)
const error = ref('')
let editor: any = null
// 编辑器根 store（onLabelStudioLoad 传入），结果从这里取
let store: any = null

// 编辑器文案补译：只替换完全匹配的界面文字，模板里的标签名不受影响
const ZH: Record<string, string> = {
  'Regions': '区域',
  'Labels': '标签',
  'History': '历史',
  'Submit': '提交',
  'Update': '更新',
  'Skip': '跳过',
  'Undo': '撤销',
  'Redo': '重做',
  'Reset': '重置',
  'Settings': '设置',
  'Delete': '删除',
  'Info': '信息',
  'Hotkeys': '快捷键',
  'General': '通用',
  'Layout': '布局',
  'Relations': '关系',
  'Results': '结果',
  'No Regions created yet': '尚未创建区域',
  'Regions not added': '尚未添加区域',
  'Selected': '已选中',
  'Created': '创建于',
  'No Region selected': '未选中区域',
  'No Relations added yet': '尚未添加关系',
  'Sorted by Date': '按时间排序',
  'Sorted by Score': '按分数排序',
  'Group by Labels': '按标签分组',
}
const ZH_PATTERNS: [RegExp, string][] = [[/^Relations \((\d+)\)$/, '关系（$1）'], [/^Relations \($/, '关系 (']]

const srcdoc = `<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="${new URL(editorCss, location.href)}">
<style>html,body{margin:0;height:100%;background:#fff}#ls{height:100%;overflow:auto}</style>
</head><body><div id="ls"></div><script src="${new URL(editorJs, location.href)}"><\/script></body></html>`

function translate(root: Node) {
  if (appStore.lang !== 'zhCN')
    return
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const text = node.nodeValue?.trim()
    if (!text)
      continue
    const zh = ZH[text] ?? ZH_PATTERNS.reduce((t, [re, to]) => t.replace(re, to), text)
    if (zh !== text)
      node.nodeValue = node.nodeValue!.replace(text, zh)
  }
}

function render() {
  const win = frame.value?.contentWindow as (typeof window & { LabelStudio?: any }) | null
  if (!win?.LabelStudio)
    return
  // 编辑中的半截 XML 不交给编辑器（它会抛出未捕获的解析错误），只提示
  error.value = checkTemplateXml(props.config)
  if (error.value)
    return
  try {
    // 编辑器的 mobx-state-tree 只认本 realm 的普通对象，参数经 iframe 的 JSON.parse 重建
    const options = win.JSON.parse(JSON.stringify({
      config: props.config,
      interfaces: ['panel', 'side-column', 'annotations:current'],
      // 只用于编辑器内显示，身份以平台 Token 为准
      user: { id: 1, pk: 1, firstName: '', lastName: '' },
      task: {
        id: 1,
        data: props.data,
        annotations: props.result?.length ? [{ id: 'km', result: props.result }] : [],
        predictions: [],
      },
    }))
    editor = new win.LabelStudio(win.document.getElementById('ls'), {
      ...options,
      onLabelStudioLoad(ls: any) {
        store = ls
        const annotations = ls.annotationStore
        const current = annotations.annotations[0] ?? annotations.addAnnotation({ userGenerate: true })
        annotations.selectAnnotation(current.id)
      },
    })
  }
  catch (e) {
    error.value = String(e)
  }
}

function onLoad() {
  const win = frame.value!.contentWindow as typeof window
  new win.MutationObserver(records => records.forEach(r => r.type === 'characterData' ? translate(r.target) : r.addedNodes.forEach(translate)))
    .observe(win.document.body, { childList: true, subtree: true, characterData: true })
  render()
}

/** 当前标注结果；编辑器未就绪时返回 null */
function getResult(): Record<string, unknown>[] | null {
  return store?.annotationStore?.selected?.serializeAnnotation() ?? null
}

/** 撤销 / 重做：交给编辑器自身的标注历史 */
const undo = () => store?.annotationStore?.selected?.history?.undo()
const redo = () => store?.annotationStore?.selected?.history?.redo()

watch(() => [props.config, props.data, props.result], () => {
  editor = null
  store = null
  error.value = ''
  frameKey.value++
})
onBeforeUnmount(() => editor?.destroy?.())
defineExpose({ getResult, undo, redo })
</script>

<template>
  <div class="relative wh-full">
    <iframe :key="frameKey" ref="frame" :srcdoc="srcdoc" class="block wh-full border-0" @load="onLoad" />
    <n-alert v-if="error" type="error" class="absolute left-4 right-4 top-4" :title="error" />
  </div>
</template>
