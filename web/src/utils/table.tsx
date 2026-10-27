import { NButton, NPopover, NSpace } from 'naive-ui'
import { isVNode } from 'vue'
import type { VNode } from 'vue'

/**
 * 按字段可能的最长内容估算列宽，保证单元格单行展示：
 * 半角字符（数字、字母）约 8px、全角字符约 14px，另加单元格左右内边距 32px 和图标等附加宽度 extra
 */
export function colWidth(halfChars: number, fullChars = 0, extra = 0) {
  return Math.ceil(halfChars * 8 + fullChars * 14 + 32 + extra)
}

/** 常用列宽预设，新列优先选用 */
export const COL_WIDTH = {
  /** 2026-10-27 12:20:24 */
  datetime: colWidth(19),
  /** sub、租户 ID 等 18 位 ID（u_ / t_ + 16 位十六进制）+ 复制图标 */
  id: colWidth(18, 0, 20),
  /** 两字状态标签（启用 / 停用 / 未开通） */
  status: colWidth(0, 3, 16),
  /** 两个文字按钮（编辑 角色）或「更多」 */
  actions: colWidth(0, 4, 24),
}

export function renderTableActions(actions: Array<VNode | false | null | undefined>) {
  const visibleActions = actions.filter((action): action is VNode => isVNode(action))
  if (!visibleActions.length)
    return null
  if (visibleActions.length <= 2)
    return <NSpace justify="center">{visibleActions}</NSpace>

  return (
    <NPopover trigger="click" placement="bottom-end">
      {{
        trigger: () => <NButton size="small" text>更多</NButton>,
        default: () => <NSpace vertical size="small">{visibleActions}</NSpace>,
      }}
    </NPopover>
  )
}
