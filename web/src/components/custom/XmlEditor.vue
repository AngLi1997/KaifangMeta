<script setup lang="ts">
// Label Studio 模板 XML 编辑器：语法高亮 + 按标签 / 属性补全（输入 < 或空格后提示，Ctrl+Space 手动触发）
import type { AttrSpec } from '@codemirror/lang-xml'
import { startCompletion } from '@codemirror/autocomplete'
import { xml } from '@codemirror/lang-xml'
import { EditorState } from '@codemirror/state'
import { EditorView } from '@codemirror/view'
import { basicSetup } from 'codemirror'
import { useThemeVars } from 'naive-ui'
import { LABEL_STUDIO_ELEMENTS } from './label-studio-schema'

const props = defineProps<{ readonly?: boolean }>()
const model = defineModel<string>({ default: '' })
const el = ref<HTMLDivElement>()
const themeVars = useThemeVars()
let view: EditorView | null = null

// 选中属性时补全为 name=""，光标放进引号并接着提示可选值
function withQuotes(attr: string | AttrSpec): AttrSpec {
  const spec = typeof attr === 'string' ? { name: attr } : attr
  return {
    ...spec,
    completion: {
      apply(editor, _completion, from, to) {
        editor.dispatch({ changes: { from, to, insert: `${spec.name}=""` }, selection: { anchor: from + spec.name.length + 2 } })
        if (spec.values)
          startCompletion(editor)
      },
    },
  }
}
const elements = LABEL_STUDIO_ELEMENTS.map(e => ({ ...e, attributes: e.attributes?.map(withQuotes) }))

const theme = EditorView.theme({
  '&': { height: '100%', fontSize: '13px' },
  '&.cm-focused': { outline: 'none' },
  '.cm-scroller': { fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' },
  '.cm-gutters': { backgroundColor: 'transparent', border: 'none' },
})

onMounted(() => {
  view = new EditorView({
    parent: el.value!,
    state: EditorState.create({
      doc: model.value,
      extensions: [
        basicSetup,
        xml({ elements }),
        theme,
        EditorState.readOnly.of(!!props.readonly),
        EditorView.updateListener.of((u) => {
          if (u.docChanged)
            model.value = u.state.doc.toString()
        }),
      ],
    }),
  })
})

// 外部替换内容（如加载模板后）时同步到编辑器
watch(model, (value) => {
  if (view && value !== view.state.doc.toString())
    view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: value } })
})

onBeforeUnmount(() => view?.destroy())
</script>

<template>
  <div
    ref="el"
    class="h-full overflow-hidden border border-solid rounded"
    :style="{ borderColor: themeVars.borderColor }"
  />
</template>
