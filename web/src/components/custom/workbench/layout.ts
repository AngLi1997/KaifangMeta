// 标注工作台布局（docs/platform/annotation/components/）：模板 XML ↔ 布局树，拖拽设计器与工作台共用
// 根为 <Workbench>，内部是可嵌套的容器（网格、列表、面板）与组件；根为 <View> 的旧模板按默认布局渲染

export type FieldType = 'text' | 'textarea' | 'number' | 'select' | 'radio' | 'checkbox' | 'date' | 'switch'
export interface FieldDef {
  name: string
  label: string
  type: FieldType
  required?: boolean
  /** select / radio / checkbox 的选项，逗号分隔 */
  options?: string
}
export interface ColumnDef {
  key: string
  title: string
  type?: 'text' | 'number' | 'date'
  width?: string
  /** 表格 editable 时该列可编辑 */
  editable?: boolean
}

export interface LayoutNode {
  id: string
  /** 标签名；无法识别的画布内标签为 Raw */
  type: string
  /** Button 的 action */
  v?: string
  attrs: Record<string, string>
  /** 容器与画布的子节点 */
  children?: LayoutNode[]
  /** Label Studio 标签的 Label / Choice 选项，逗号分隔 */
  opts?: string
  /** Raw：原文 */
  xml?: string
  fields?: FieldDef[]
  columns?: ColumnDef[]
}

/**
 * kind：container 布局容器 / bar 按钮栏（只收 item 与 spacer）/ item 按钮（只能放进按钮栏）/ spacer 间隔（任意容器）/ leaf 组件
 * obj、ctl、vis 为 Label Studio 对象、控件、视觉标签（只能放进画布）
 */
export type Kind = 'container' | 'bar' | 'item' | 'spacer' | 'leaf' | 'obj' | 'ctl' | 'vis'
export interface ComponentDef {
  /** 组件库中的键 */
  key: string
  type: string
  v?: string
  label: string
  group: string
  kind: Kind
  /** 同一模板只能放一个 */
  unique?: boolean
  attrs?: Record<string, string>
  opts?: string
}

const button = (v: string, label: string): ComponentDef => ({ key: `Button:${v}`, type: 'Button', v, label, group: '按钮', kind: 'item', unique: true })
function ls(type: string, label: string, kind: 'obj' | 'ctl' | 'vis', attrs: Record<string, string> = {}, opts?: string): ComponentDef {
  return { key: type, type, label, kind, attrs, opts, group: { obj: 'Label Studio 对象', ctl: 'Label Studio 控件', vis: 'Label Studio 视觉' }[kind] }
}

/** 内置组件库：只收已实现的组件，按期开放 */
export const COMPONENTS: ComponentDef[] = [
  { key: 'Grid', type: 'Grid', label: '网格', group: '布局', kind: 'container', attrs: { columns: '2' } },
  { key: 'List:horizontal', type: 'List', label: '横向列表', group: '布局', kind: 'container', attrs: { direction: 'horizontal' } },
  { key: 'List:vertical', type: 'List', label: '纵向列表', group: '布局', kind: 'container', attrs: { direction: 'vertical' } },
  { key: 'Panel', type: 'Panel', label: '面板', group: '布局', kind: 'container', attrs: { title: '面板' } },
  { key: 'Spacer', type: 'Spacer', label: '间隔', group: '布局', kind: 'spacer' },
  { key: 'Form', type: 'Form', label: '表单', group: '组件', kind: 'leaf', attrs: { columns: '2' } },
  { key: 'DataTable', type: 'DataTable', label: '数据表格', group: '组件', kind: 'leaf' },
  { key: 'ButtonBar', type: 'ButtonBar', label: '按钮栏', group: '按钮', kind: 'bar', attrs: { align: 'start', valign: 'center' } },
  button('undo', '撤销'),
  button('redo', '重做'),
  button('prev', '上一份'),
  button('next', '下一份'),
  button('view-data', '查看数据'),
  button('export', '导出'),
  button('log', '日志'),
  button('save', '保存'),
  button('submit', '提交'),
  { key: 'Canvas', type: 'Canvas', label: '画布', group: 'Label Studio', kind: 'leaf', unique: true },
  ls('Image', '图像', 'obj', { value: '$image' }),
  ls('Text', '文本', 'obj', { value: '$text' }),
  ls('HyperText', 'HTML', 'obj', { value: '$html' }),
  ls('Audio', '音频', 'obj', { value: '$audio' }),
  ls('Video', '视频', 'obj', { value: '$video' }),
  ls('Rectangle', '矩形框', 'ctl'),
  ls('RectangleLabels', '矩形标签', 'ctl', {}, '印章,签名'),
  ls('PolygonLabels', '多边形标签', 'ctl', {}, '印章'),
  ls('KeyPointLabels', '关键点', 'ctl', {}, '角点'),
  ls('BrushLabels', '画笔标签', 'ctl', {}, '涂改'),
  ls('Labels', '实体标签', 'ctl', {}, '人名,机构'),
  ls('Choices', '单 / 多选', 'ctl', { choice: 'single' }, '公开,内部'),
  ls('Taxonomy', '分类树', 'ctl', {}, '文书,科技'),
  ls('TextArea', '文本输入', 'ctl'),
  ls('Number', '数字', 'ctl'),
  ls('DateTime', '日期时间', 'ctl', { only: 'date' }),
  ls('Rating', '评分', 'ctl'),
  ls('Header', '标题文字', 'vis', { value: '标题' }),
]
const BY_KEY = Object.fromEntries(COMPONENTS.map(c => [c.key, c])) as Record<string, ComponentDef>
export const FIELD_TYPES: Record<FieldType, string> = { text: '文本', textarea: '多行文本', number: '数字', select: '下拉', radio: '单选', checkbox: '多选', date: '日期', switch: '开关' }
export const CONTAINERS = ['Workbench', 'List', 'Grid', 'Panel', 'ButtonBar']
const VATTR: Record<string, string> = { Button: 'action' }
const OPT_TAG = (type: string) => type === 'Choices' || type === 'Taxonomy' ? 'Choice' : 'Label'

/** 节点对应的组件定义 */
export function defOf(n: Pick<LayoutNode, 'type' | 'v' | 'attrs'>): ComponentDef | undefined {
  if (n.type === 'List')
    return BY_KEY[`List:${n.attrs.direction === 'horizontal' ? 'horizontal' : 'vertical'}`]
  return BY_KEY[n.v !== undefined ? `${n.type}:${n.v}` : n.type]
}
export const isLs = (kind?: Kind) => kind === 'obj' || kind === 'ctl' || kind === 'vis'
/** 拖放规则：画布只收 Label Studio 标签，按钮栏只收按钮与间隔，其他容器收容器、组件与间隔 */
export function canDrop(parentType: string, kind?: Kind) {
  if (parentType === 'Canvas')
    return isLs(kind)
  if (parentType === 'ButtonBar')
    return kind === 'item' || kind === 'spacer'
  return CONTAINERS.includes(parentType) && (kind === 'container' || kind === 'bar' || kind === 'leaf' || kind === 'spacer')
}
export const nodeLabel = (n: LayoutNode) => n.type === 'Raw' ? `<${n.v}>` : defOf(n)?.label ?? n.type
export const walk = (n: LayoutNode): LayoutNode[] => [n, ...(n.children ?? []).flatMap(walk)]
export const findCanvas = (root: LayoutNode) => walk(root).find(n => n.type === 'Canvas')
export const objectNames = (canvas?: LayoutNode) => (canvas?.children ?? []).filter(n => defOf(n)?.kind === 'obj').map(n => n.attrs.name)

let seq = 0
export const newId = () => `n${++seq}`
const node = (type: string, attrs: Record<string, string> = {}, rest: Partial<LayoutNode> = {}): LayoutNode => ({ id: newId(), type, attrs, ...rest })

/** 新建组件节点（从组件库拖出时）；同类组件按已有名称自动编号 */
export function createNode(def: ComponentDef, root: LayoutNode): LayoutNode {
  const names = walk(root).map(n => n.attrs.name)
  const unique = (base: string) => {
    let i = 1
    while (names.includes(i > 1 ? `${base}_${i}` : base)) i++
    return i > 1 ? `${base}_${i}` : base
  }
  const attrs = { ...def.attrs }
  if (def.kind === 'container' || def.kind === 'bar' || def.type === 'Canvas')
    return node(def.type, attrs, { children: [] })
  if (def.type === 'Form') {
    return node('Form', { name: unique('form'), ...attrs }, { fields: [
      { name: 'title', label: '题名', type: 'text', required: true },
      { name: 'secret', label: '密级', type: 'select', options: '公开,内部,秘密' },
    ] })
  }
  if (def.type === 'DataTable') {
    return node('DataTable', { name: unique('table'), ...attrs }, { columns: [
      { key: 'seq', title: '序号', type: 'number', width: '80' },
      { key: 'title', title: '文件题名' },
      { key: 'date', title: '成文日期', type: 'date', width: '140' },
    ] })
  }
  if (!isLs(def.kind))
    return node(def.type, attrs, { v: def.v })
  const ls: Record<string, string> = def.kind === 'vis' ? {} : { name: unique(def.type.toLowerCase()) }
  if (def.kind === 'ctl')
    ls.toName = objectNames(findCanvas(root))[0] ?? ''
  return node(def.type, { ...ls, ...attrs }, { opts: def.opts })
}

const childrenOf = (el: Element) => Array.from(el.children)
const attrsOf = (el: Element) => Object.fromEntries(Array.from(el.attributes).map(a => [a.name, a.value]))
const rawXml = (el: Element) => new XMLSerializer().serializeToString(el).replace(/ xmlns="[^"]*"/g, '')

function parseDoc(xml: string) {
  const doc = new DOMParser().parseFromString(xml, 'application/xml')
  if (doc.querySelector('parsererror'))
    throw new Error('XML 无法解析')
  return doc.documentElement
}

function parseCanvasChildren(view: Element | null): LayoutNode[] {
  return (view ? childrenOf(view) : []).map((el) => {
    const def = BY_KEY[el.tagName]
    const opts = childrenOf(el)
    if (!def || !isLs(def.kind) || opts.some(o => o.tagName !== OPT_TAG(el.tagName)))
      return node('Raw', {}, { v: el.tagName, xml: rawXml(el) })
    return node(el.tagName, attrsOf(el), { opts: opts.length || def.opts ? opts.map(o => o.getAttribute('value')).join(',') : undefined })
  })
}

function parseNode(el: Element): LayoutNode {
  const attrs = attrsOf(el)
  const n = node(el.tagName, attrs)
  if (VATTR[el.tagName]) {
    n.v = attrs[VATTR[el.tagName]] ?? ''
    n.attrs = {}
  }
  const def = defOf(n)
  if (!def || isLs(def.kind))
    throw new Error(`未知组件 <${el.tagName}${n.v ? ` ${VATTR[el.tagName]}="${n.v}"` : ''}>`)
  if (el.tagName === 'Canvas') {
    n.children = parseCanvasChildren(el.querySelector('View'))
  }
  else if (def.kind === 'container' || def.kind === 'bar') {
    n.children = childrenOf(el).map(parseNode)
  }
  else if (el.tagName === 'Form') {
    n.fields = childrenOf(el).map((f) => {
      const a = attrsOf(f)
      return { name: a.name ?? '', label: a.label ?? '', type: (a.type ?? 'text') as FieldType, required: a.required === 'true', options: a.options }
    })
  }
  else if (el.tagName === 'DataTable') {
    n.columns = childrenOf(el).map((c) => {
      const a = attrsOf(c)
      return { key: a.key ?? '', title: a.title ?? '', type: a.type as ColumnDef['type'], width: a.width, editable: a.editable === 'true' }
    })
  }
  return n
}

/** 旧模板（根为 <View>）的默认外壳：工具栏（撤销重做在左，保存提交在右）+ 画布 */
function legacyLayout(view: Element): LayoutNode {
  const bar = node('ButtonBar', { align: 'start', valign: 'center' }, {
    children: 'undo,redo,view-data,log,|,prev,next,save,submit'.split(',').map(v => v === '|' ? node('Spacer') : node('Button', {}, { v })),
  })
  return node('Workbench', {}, { children: [bar, node('Canvas', {}, { children: parseCanvasChildren(view) })] })
}

/** 模板 XML → 布局树；结构错误时抛出带说明的错误，规则校验见 checkLayout */
export function parseLayout(xml: string): LayoutNode {
  const root = parseDoc(xml)
  if (root.tagName === 'View')
    return legacyLayout(root)
  if (root.tagName !== 'Workbench')
    throw new Error('根标签须为 <Workbench> 或 <View>')
  return node('Workbench', {}, { children: childrenOf(root).map(parseNode) })
}

/** 规则校验，合规时返回空串 */
export function checkLayout(root: LayoutNode) {
  const all = walk(root)
  if (all.length === 1)
    return '工作台为空，请从左侧拖入组件'
  for (const parent of all) {
    const bad = parent.children?.find(c => c.type !== 'Raw' && !canDrop(parent.type, defOf(c)?.kind))
    if (bad)
      return `${nodeLabel(bad)} 不能放在${nodeLabel(parent) === 'Workbench' ? '工作台根' : nodeLabel(parent)}内${defOf(bad)?.kind === 'item' ? '，请放进按钮栏' : ''}`
  }
  const uniq = all.filter(n => defOf(n)?.unique).map(n => defOf(n)!.label)
  const dup = uniq.find((k, i) => uniq.indexOf(k) !== i)
  if (dup)
    return `${dup} 重复放置`
  const names = all.filter(n => n.type === 'Form' || n.type === 'DataTable').map(n => n.attrs.name)
  const dupName = names.find((n, i) => !n || names.indexOf(n) !== i)
  if (dupName !== undefined)
    return dupName ? `组件名 ${dupName} 重复` : '表单 / 表格缺少名称'
  for (const f of all.filter(n => n.type === 'Form')) {
    const keys = f.fields!.map(x => x.name)
    if (keys.some((k, i) => !k || keys.indexOf(k) !== i))
      return `表单 ${f.attrs.name} 的字段名为空或重复`
  }
  const canvas = findCanvas(root)
  // 原始 XML 块里可能有对象标签，无法逐个核对时放行，由编辑器渲染时报错
  if (!canvas || canvas.children!.some(n => n.type === 'Raw'))
    return ''
  const objs = objectNames(canvas)
  if (!objs.length)
    return '画布内至少需要一个对象标签（图像、文本等）'
  const lsNames = canvas.children!.map(n => n.attrs.name).filter(Boolean)
  const dupLs = lsNames.find((n, i) => lsNames.indexOf(n) !== i)
  if (dupLs)
    return `name="${dupLs}" 重复`
  const bad = canvas.children!.find(n => defOf(n)?.kind === 'ctl' && !objs.includes(n.attrs.toName))
  return bad ? `<${bad.type} name="${bad.attrs.name}"> 的 toName 未指向画布中的对象` : ''
}

const esc = (v: string) => v.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;')
const attrText = (attrs: Record<string, unknown>) => Object.entries(attrs).filter(([, v]) => v !== '' && v != null && v !== false).map(([k, v]) => ` ${k}="${esc(String(v))}"`).join('')

function canvasTag(n: LayoutNode, ind: string) {
  if (n.type === 'Raw')
    return n.xml!.split('\n').map(l => ind + l.trim()).join('\n')
  if (n.opts === undefined)
    return `${ind}<${n.type}${attrText(n.attrs)}/>`
  const opts = n.opts.split(',').map(o => o.trim()).filter(Boolean).map(o => `${ind}  <${OPT_TAG(n.type)} value="${esc(o)}"/>`)
  return `${ind}<${n.type}${attrText(n.attrs)}>\n${opts.join('\n')}\n${ind}</${n.type}>`
}

/** 画布交给 Label Studio 的 <View> */
export const canvasXml = (canvas: LayoutNode) => `<View>\n${canvas.children!.map(n => canvasTag(n, '  ')).join('\n')}\n</View>`

function tag(n: LayoutNode, ind: string): string {
  const open = (body: string[]) => body.length ? `${ind}<${n.type}${attrText(n.attrs)}>\n${body.join('\n')}\n${ind}</${n.type}>` : `${ind}<${n.type}${attrText(n.attrs)}/>`
  if (n.type === 'Canvas')
    return `${ind}<Canvas${attrText(n.attrs)}>\n${canvasXml(n).split('\n').map(l => `${ind}  ${l}`).join('\n')}\n${ind}</Canvas>`
  if (n.v !== undefined)
    return `${ind}<${n.type} ${VATTR[n.type]}="${esc(n.v)}"/>`
  if (n.fields)
    return open(n.fields.map(f => `${ind}  <Field${attrText({ name: f.name, label: f.label, type: f.type, required: f.required, options: f.options })}/>`))
  if (n.columns)
    return open(n.columns.map(c => `${ind}  <Column${attrText({ key: c.key, title: c.title, type: c.type, width: c.width, editable: c.editable })}/>`))
  return open((n.children ?? []).map(c => tag(c, `${ind}  `)))
}

/** 布局树 → 模板 XML（规范格式） */
export const serializeLayout = (root: LayoutNode) => tag(root, '')

/** 模板 XML 中交给 Label Studio 的部分：旧模板原样返回，<Workbench> 取 <Canvas> 内的 <View> 原文；没有画布时为空串 */
export function extractCanvas(xml: string) {
  const root = parseDoc(xml)
  if (root.tagName === 'View')
    return xml
  const view = root.querySelector('Canvas > View')
  return view ? rawXml(view) : ''
}

/** 列表里会占满剩余空间的节点：按钮栏（及只含按钮栏的列表）按内容高度排列，其余撑满 */
export function grows(n: LayoutNode): boolean {
  if (n.type === 'ButtonBar' || defOf(n)?.kind === 'item')
    return false
  if (n.type === 'List')
    return !!n.children?.some(grows)
  return true
}

/** 占比可选值：子节点在列表里所占的百分比，不设为平分剩余空间；也可手动输入 1%–100% */
/** 间隔在列表里的默认长度（px） */
export const SPACER = 16
export const SIZES = ['5%', '10%', '15%', '25%', '30%', '33%', '50%', '67%', '75%', '100%']
/** 手动输入的占比规范为「n%」，不合法时返回空串 */
export function normalizeSize(v: string) {
  const n = Number(String(v).trim().replace(/%$/, ''))
  return Number.isFinite(n) && n > 0 && n <= 100 ? `${n}%` : ''
}
/** 按钮栏对齐：属性值 → CSS */
export const JUSTIFY: Record<string, string> = { start: 'flex-start', center: 'center', end: 'flex-end', between: 'space-between' }
export const ALIGN: Record<string, string> = { top: 'flex-start', center: 'center', bottom: 'flex-end' }
/** 容器间距（px）：横向列表与按钮栏默认 8，其余 12 */
export const gapOf = (n: LayoutNode) => Number(n.attrs.gap ?? ((n.type === 'List' && n.attrs.direction === 'horizontal') || n.type === 'ButtonBar' ? 8 : 12))
export const isHorizontalList = (n: LayoutNode) => n.type === 'List' && n.attrs.direction === 'horizontal'
/** 子节点在该父容器里是否伸展：横向列表里都按宽度分配；纵向排列里按钮栏按内容高度 */
export const growsIn = (c: LayoutNode, parent: LayoutNode) => isHorizontalList(parent) ? defOf(c)?.kind !== 'item' : grows(c)
/** 子节点在列表中的 flex：横向列表设了列数时按列等分（忽略占比）；否则设了占比按百分比，未设平分剩余空间 */
export function flexOf(c: LayoutNode, parent: LayoutNode, gap: number) {
  if (!growsIn(c, parent))
    return 'none'
  // 间隔在列表里默认是一段固定空白（按钮栏里由按钮栏让它占满剩余宽度）
  if (c.type === 'Spacer')
    return c.attrs.size ? `0 1 ${c.attrs.size}` : `0 0 ${SPACER}px`
  const cols = isHorizontalList(parent) ? Number(parent.attrs.columns) : 0
  if (cols)
    return `0 0 calc((100% - ${(cols - 1) * gap}px) / ${cols})`
  return c.attrs.size ? `0 1 ${c.attrs.size}` : '1 1 0'
}
/** 横向列表同时设了列数与子节点占比 */
export const sizeConflict = (list: LayoutNode) => isHorizontalList(list) && !!Number(list.attrs.columns) && !!list.children?.some(c => c.attrs.size)

/** 复制节点（含子树），新 id；表单、表格、Label Studio 标签的 name 重新编号，唯一组件不复制 */
export function cloneNode(n: LayoutNode, root: LayoutNode): LayoutNode | null {
  if (walk(n).some(x => defOf(x)?.unique))
    return null
  const names = walk(root).map(x => x.attrs.name)
  const copy = (x: LayoutNode): LayoutNode => {
    const c: LayoutNode = { ...JSON.parse(JSON.stringify({ ...x, children: undefined })), id: newId(), children: x.children?.map(copy) }
    if (c.attrs.name) {
      let i = 2
      const base = c.attrs.name.replace(/_\d+$/, '')
      while (names.includes(`${base}_${i}`)) i++
      c.attrs.name = `${base}_${i}`
      names.push(c.attrs.name)
    }
    return c
  }
  return copy(n)
}

/** 数据表格的静态样例行（数据源接入前） */
export function mockRows(columns: ColumnDef[], count = 5) {
  return Array.from({ length: count }, (_, i) => Object.fromEntries(columns.map(c => [
    c.key,
    c.type === 'number' ? i + 1 : c.type === 'date' ? `2026-08-${String(11 + i).padStart(2, '0')}` : `${c.title} ${i + 1}`,
  ])))
}

/** 快照导出为 YAML（只用于查看与导出，不做反向解析） */
export function toYaml(value: unknown, ind = ''): string {
  const scalar = (x: unknown) => typeof x === 'string' ? (/^[\p{L}_][\p{L}\p{N}_ .（）-]*$/u.test(x) ? x : JSON.stringify(x)) : String(x)
  const empty = (x: unknown) => !!x && typeof x === 'object' && !Object.keys(x).length
  const nested = (x: unknown) => !!x && typeof x === 'object' && !empty(x)
  if (Array.isArray(value))
    return value.map(x => `${ind}- ${nested(x) ? toYaml(x, `${ind}  `).trimStart() : empty(x) ? JSON.stringify(x) : scalar(x)}`).join('\n')
  return Object.entries(value as object).map(([k, x]) => nested(x)
    ? `${ind}${k}:\n${toYaml(x, `${ind}  `)}`
    : `${ind}${k}: ${empty(x) ? JSON.stringify(x) : scalar(x)}`).join('\n')
}
