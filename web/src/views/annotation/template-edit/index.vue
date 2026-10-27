<script setup lang="ts">
import type { FormInst, FormRules } from 'naive-ui'
import { useThemeVars } from 'naive-ui'
import { checkTemplateXml } from '@/components/custom/label-studio-schema'
import { checkLayout, parseLayout } from '@/components/custom/workbench/layout'
import LayoutDesigner from '@/components/custom/workbench/LayoutDesigner.vue'
import Workbench from '@/components/custom/workbench/Workbench.vue'
import XmlEditor from '@/components/custom/XmlEditor.vue'
import { usePermission } from '@/hooks'
import { fetchAnnotationTemplate, fetchCreateAnnotationTemplate, fetchUpdateAnnotationTemplate } from '@/service'
import { useAuthStore, useTabStore } from '@/store'
import { message } from '@/utils'
import { refDebounced, useElementSize } from '@vueuse/core'
import { MODALITY, toOptions } from '../constants'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const tabStore = useTabStore()
const { hasPermission } = usePermission()
const loading = ref(false)
const formRef = ref<FormInst | null>(null)
const form = ref<Partial<Entity.AnnotationTemplate>>({
  name: '',
  code: '',
  modality: 'image',
  // 编辑已有模板时留空，避免加载前先渲染默认模板
  config: route.query.id ? '' : '<Workbench/>',
})
const readonly = ref(false)
// XML 与布局两种方式编辑同一份 config；布局模式下设计器占满页面
const mode = ref<'xml' | 'layout' | 'preview'>(route.query.id ? 'xml' : 'layout')
const MODES = [['xml', 'XML'], ['layout', '布局'], ['preview', '预览']] as const
const rules: FormRules = {
  name: { required: true, message: '请输入模板名称', trigger: 'blur' },
  code: { required: true, pattern: /^[a-z][a-z0-9._-]*$/, message: '小写字母开头，可含数字 . _ -', trigger: 'blur' },
  modality: { required: true, message: '请选择模态', trigger: 'change' },
}

// 预览铺满预览区；预览区窄于工作台最小宽度时整体等比缩小，保证编辑器仍按工作台布局排版，超出部分在编辑器内滚动
const WORKBENCH_MIN_WIDTH = 1280
const themeVars = useThemeVars()
const previewBox = ref<HTMLDivElement>()
const { width: boxWidth, height: boxHeight } = useElementSize(previewBox)
const scale = computed(() => Math.min(1, boxWidth.value / WORKBENCH_MIN_WIDTH) || 1)
const stage = computed(() => ({ width: boxWidth.value / scale.value, height: boxHeight.value / scale.value }))

// 预览样例：按模板中的 value="$变量" 及其标签类型生成
const SAMPLE_IMAGE = `data:image/svg+xml;utf8,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="595" height="842"><rect width="595" height="842" fill="#fbfaf6"/><text x="297" y="110" font-size="30" fill="#b3312a" text-anchor="middle" font-family="serif" letter-spacing="8">××省档案局文件</text><text x="297" y="150" font-size="14" text-anchor="middle">×档发〔2024〕12号</text><rect x="60" y="165" width="475" height="3" fill="#b3312a"/><text x="297" y="215" font-size="18" text-anchor="middle" font-weight="bold">关于开展档案数字化质量检查的通知</text>${Array.from({ length: 9 }, (_, i) => `<rect x="60" y="${250 + i * 32}" width="${i % 4 === 3 ? 300 : 475}" height="10" fill="#d6d3ca"/>`).join('')}<circle cx="430" cy="680" r="62" fill="none" stroke="#c8413a" stroke-width="3"/><text x="440" y="700" font-size="14" text-anchor="middle">2024年3月18日</text></svg>`)}`
const SAMPLE_TEXT = '2024年3月18日，××省档案局在杭州印发《关于开展档案数字化质量检查的通知》，由张明负责组织实施。'

const previewConfig = refDebounced(computed(() => form.value.config ?? ''), 600)
const xmlError = computed(() => previewConfig.value && checkTemplateXml(previewConfig.value))
const sampleData = computed(() => Object.fromEntries(
  [...previewConfig.value.matchAll(/<(\w+)\s[^>]*?value="\$(\w+)"/g)].map(([, tag, key]) =>
    [key, tag === 'Image' ? SAMPLE_IMAGE : ['Text', 'HyperText', 'Header'].includes(tag) ? SAMPLE_TEXT : '']),
))

// 回到列表并关闭本编辑页标签
async function back() {
  const fullPath = route.fullPath
  await router.push('/annotation/template')
  tabStore.closeTab(fullPath)
}

async function load() {
  const id = Number(route.query.id)
  if (!id)
    return
  const res = await fetchAnnotationTemplate(id)
  if (!res.isSuccess)
    return
  form.value = res.data
  readonly.value = res.data.tenant_id !== authStore.userInfo?.tenant_id || !hasPermission('post/api/v1/annotation/template/update')
}

async function submit() {
  await formRef.value?.validate()
  if (!form.value.config?.trim())
    return message.warning('请输入模板 XML')
  let layoutError = ''
  try {
    layoutError = checkLayout(parseLayout(form.value.config))
  }
  catch (e) {
    layoutError = (e as Error).message
  }
  if (layoutError)
    return message.warning(`模板布局有误：${layoutError}`)
  loading.value = true
  const { id, name, code, modality, config } = form.value
  const res = id
    ? await fetchUpdateAnnotationTemplate({ id, name, modality, config })
    : await fetchCreateAnnotationTemplate({ name, code, modality, config })
  loading.value = false
  if (res.isSuccess) {
    message.success('已保存')
    back()
  }
}

onMounted(load)
</script>

<template>
  <n-flex :wrap="false" class="h-full min-h-0" :size="16">
    <n-card
      :class="mode === 'xml' ? 'w-2/5 min-w-100 max-w-150 shrink-0' : 'min-w-0 flex-1'"
      content-class="flex min-h-0 flex-col gap-3"
    >
      <template #header>
        <n-space align="center" :size="16">
          <span>{{ form.id ? `${form.code}@${form.version}` : '新建模板' }}</span>
          <n-button-group>
            <n-button v-for="[k, label] in MODES" :key="k" :type="mode === k ? 'primary' : 'default'" @click="mode = k">
              {{ label }}
            </n-button>
          </n-button-group>
        </n-space>
      </template>
      <template #header-extra>
        <n-space>
          <n-button @click="back">
            返回
          </n-button>
          <n-button v-if="!readonly" type="primary" :loading="loading" @click="submit">
            保存
          </n-button>
        </n-space>
      </template>
      <n-form ref="formRef" :model="form" :rules="rules" :disabled="readonly" label-placement="left" :label-width="64">
        <n-grid :cols="2" :x-gap="18">
          <n-form-item-gi label="名称" path="name">
            <n-input v-model:value="form.name" />
          </n-form-item-gi>
          <n-form-item-gi label="模态" path="modality">
            <n-select v-model:value="form.modality" :options="toOptions(MODALITY)" />
          </n-form-item-gi>
          <n-form-item-gi :span="2" label="编码" path="code">
            <n-input v-model:value="form.code" :disabled="!!form.id" placeholder="如 image.seal" />
          </n-form-item-gi>
        </n-grid>
      </n-form>
      <XmlEditor v-if="mode === 'xml'" v-model="form.config" :readonly="readonly" class="min-h-0 flex-1" />
      <LayoutDesigner v-else-if="mode === 'layout' && form.config" v-model="form.config" :readonly="readonly" class="flex-1" />
      <div v-else-if="mode === 'preview'" class="min-h-0 flex-1 overflow-hidden border border-solid rounded" :style="{ borderColor: themeVars.borderColor }">
        <Workbench v-if="form.config" :config="form.config" :data="sampleData" :item="{ name: '样例', index: 1, total: 1 }" preview />
      </div>
    </n-card>

    <n-card v-show="mode === 'xml'" title="预览" class="min-w-0 flex-1" content-class="flex min-h-0 flex-col">
      <n-alert v-if="xmlError" type="error" :show-icon="false" class="mb-3">
        {{ xmlError }}
      </n-alert>
      <div
        ref="previewBox"
        class="relative min-h-0 flex-1 overflow-hidden border border-solid rounded"
        :style="{ borderColor: themeVars.borderColor }"
      >
        <div
          class="absolute left-0 top-0 origin-top-left"
          :style="{ width: `${stage.width}px`, height: `${stage.height}px`, transform: `scale(${scale})` }"
        >
          <Workbench v-if="previewConfig && !xmlError" :config="previewConfig" :data="sampleData" :item="{ name: '样例', index: 1, total: 1 }" preview />
        </div>
      </div>
    </n-card>
  </n-flex>
</template>
