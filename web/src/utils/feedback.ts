import type { DialogOptions, MessageOptions } from 'naive-ui'
import { $t } from './i18n'

type ConfirmType = 'default' | 'warning' | 'error'

// 确认框：default 跟随主题主色（Naive 的 info 类型用的是固定信息色，不随主题切换）
export function confirmDialog(options: Omit<DialogOptions, 'type'> & { type?: ConfirmType }) {
  return window.$dialog.create({
    positiveText: $t('common.confirm'),
    negativeText: $t('common.cancel'),
    ...options,
    type: options.type ?? 'default',
  })
}

// 消息：页面统一从这里调用，便于集中调整时长等行为
export const message = {
  success: (content: string, options?: MessageOptions) => window.$message.success(content, options),
  warning: (content: string, options?: MessageOptions) => window.$message.warning(content, options),
  error: (content: string, options?: MessageOptions) => window.$message.error(content, options),
  info: (content: string, options?: MessageOptions) => window.$message.info(content, options),
}
