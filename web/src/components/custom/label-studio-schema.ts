import type { ElementSpec } from '@codemirror/lang-xml'

// Label Studio 模板标签，供 XML 编辑器补全；只收常用标签与属性，未收录的仍可手写
const BOOL = ['true', 'false']
const OBJECTS = ['Image', 'Text', 'HyperText', 'Audio', 'Video', 'Header', 'Paragraphs', 'Table', 'TimeSeries']
const CONTROLS = [
  'Labels',
  'RectangleLabels',
  'PolygonLabels',
  'KeyPointLabels',
  'EllipseLabels',
  'BrushLabels',
  'Rectangle',
  'Polygon',
  'KeyPoint',
  'Ellipse',
  'Choices',
  'TextArea',
  'Rating',
  'Number',
  'DateTime',
  'Taxonomy',
  'Relations',
  'Ranker',
]
const VISUAL = ['View', 'Header', 'Style', 'Filter', 'Collapse']
const BLOCK = [...VISUAL, ...OBJECTS, ...CONTROLS]

const control = ['name', 'toName', { name: 'required', values: BOOL }, { name: 'perRegion', values: BOOL }, 'whenTagName', 'whenLabelValue', 'whenChoiceValue']
const labelControl = [...control, { name: 'choice', values: ['single', 'multiple'] }, { name: 'showInline', values: BOOL }, 'strokeWidth', 'opacity', 'fillColor']
const label = ['value', 'alias', 'background', 'hotkey', 'selected', 'hint']

export const LABEL_STUDIO_ELEMENTS: ElementSpec[] = [
  { name: 'View', top: true, children: BLOCK, attributes: ['style', 'className', { name: 'visibleWhen', values: ['region-selected', 'choice-selected', 'no-region-selected'] }] },
  { name: 'Header', attributes: ['value', 'size', 'style', { name: 'underline', values: BOOL }] },
  { name: 'Style' },
  { name: 'Filter', attributes: ['name', 'toName', 'placeholder', 'hotkey'] },
  { name: 'Collapse', children: ['Panel'], attributes: [{ name: 'accordion', values: BOOL }] },
  { name: 'Panel', children: BLOCK, attributes: ['value'] },

  { name: 'Image', attributes: ['name', 'value', 'valueList', { name: 'zoom', values: BOOL }, { name: 'zoomControl', values: BOOL }, { name: 'rotateControl', values: BOOL }, 'width', 'maxWidth', { name: 'crosshair', values: BOOL }] },
  { name: 'Text', attributes: ['name', 'value', { name: 'granularity', values: ['symbol', 'word', 'sentence', 'paragraph'] }, { name: 'highlightColor' }, { name: 'showLabels', values: BOOL }] },
  { name: 'HyperText', attributes: ['name', 'value', { name: 'inline', values: BOOL }, { name: 'saveTextResult', values: BOOL }] },
  { name: 'Audio', attributes: ['name', 'value', 'hotkey', 'speed', 'volume'] },
  { name: 'Video', attributes: ['name', 'value', 'frameRate', 'height'] },
  { name: 'Paragraphs', attributes: ['name', 'value', 'nameKey', 'textKey', { name: 'layout', values: ['none', 'dialogue'] }] },
  { name: 'Table', attributes: ['name', 'value'] },
  { name: 'TimeSeries', children: ['Channel'], attributes: ['name', 'value', 'valueType', 'timeColumn'] },
  { name: 'Channel', attributes: ['column', 'legend', 'strokeColor'] },

  ...['Labels', 'RectangleLabels', 'PolygonLabels', 'KeyPointLabels', 'EllipseLabels', 'BrushLabels'].map(name => ({
    name,
    children: ['Label'],
    attributes: labelControl,
  })),
  { name: 'Label', attributes: label },
  ...['Rectangle', 'Polygon', 'KeyPoint', 'Ellipse'].map(name => ({ name, attributes: [...control, 'strokeWidth', 'opacity', 'fillColor'] })),
  {
    name: 'Choices',
    children: ['Choice'],
    attributes: [...control, { name: 'choice', values: ['single', 'single-radio', 'multiple'] }, { name: 'showInline', values: BOOL }, { name: 'layout', values: ['select', 'inline', 'vertical'] }],
  },
  { name: 'Choice', attributes: ['value', 'alias', 'hotkey', 'background', 'selected', 'hint'] },
  {
    name: 'TextArea',
    attributes: [...control, 'placeholder', 'value', 'maxSubmissions', 'rows', { name: 'editable', values: BOOL }, { name: 'showSubmitButton', values: BOOL }, { name: 'transcription', values: BOOL }],
  },
  { name: 'Rating', attributes: [...control, 'maxRating', 'defaultValue', { name: 'icon', values: ['star', 'heart', 'fire', 'smile'] }, { name: 'size', values: ['small', 'medium', 'large'] }] },
  { name: 'Number', attributes: [...control, 'min', 'max', 'step', 'defaultValue'] },
  { name: 'DateTime', attributes: [...control, { name: 'only', values: ['date', 'time', 'month', 'year'] }, 'format', 'min', 'max'] },
  { name: 'Taxonomy', children: ['Choice'], attributes: [...control, { name: 'leafsOnly', values: BOOL }, { name: 'showFullPath', values: BOOL }, 'maxUsages'] },
  { name: 'Relations', children: ['Relation'], attributes: [{ name: 'choice', values: ['single', 'multiple'] }] },
  { name: 'Relation', attributes: ['value', 'background'] },
  { name: 'Ranker', attributes: ['name', 'toName'] },
]

/** 校验模板 XML，返回错误说明；合法时返回空串 */
export function checkTemplateXml(config: string) {
  const error = new DOMParser().parseFromString(config, 'application/xml').querySelector('parsererror')
  if (!error)
    return ''
  const detail = error.textContent?.match(/error on line .*?(?=Below is|$)/s)?.[0].trim()
  return `模板 XML 有误：${detail ?? error.textContent ?? ''}`
}
