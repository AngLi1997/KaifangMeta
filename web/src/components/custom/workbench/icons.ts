// 组件库与按钮使用的图标（icon-park-outline），键同 ComponentDef.key
import type { Component } from 'vue'
import IconCalendar from '~icons/icon-park-outline/calendar'
import IconCheck from '~icons/icon-park-outline/check'
import IconCode from '~icons/icon-park-outline/code'
import IconColumn from '~icons/icon-park-outline/column'
import IconPoint from '~icons/icon-park-outline/connection-point'
import IconDistribute from '~icons/icon-park-outline/distribute-horizontal-spacing'
import IconDownload from '~icons/icon-park-outline/download'
import IconBrush from '~icons/icon-park-outline/format-brush'
import IconForm from '~icons/icon-park-outline/form-one'
import IconGrid from '~icons/icon-park-outline/grid-four'
import IconHeader from '~icons/icon-park-outline/h'
import IconLabel from '~icons/icon-park-outline/label'
import IconPanel from '~icons/icon-park-outline/layout-five'
import IconLeft from '~icons/icon-park-outline/left'
import IconChoices from '~icons/icon-park-outline/list-checkbox'
import IconNumber from '~icons/icon-park-outline/list-numbers'
import IconList from '~icons/icon-park-outline/list-two'
import IconLogs from '~icons/icon-park-outline/log'
import IconBar from '~icons/icon-park-outline/more-three'
import IconAudio from '~icons/icon-park-outline/music'
import IconCanvas from '~icons/icon-park-outline/painted-screen'
import IconPolygon from '~icons/icon-park-outline/pentagon-one'
import IconImage from '~icons/icon-park-outline/pic'
import IconPreview from '~icons/icon-park-outline/preview-open'
import IconRectangle from '~icons/icon-park-outline/rectangle-one'
import IconRedo from '~icons/icon-park-outline/redo'
import IconRight from '~icons/icon-park-outline/right'
import IconSave from '~icons/icon-park-outline/save'
import IconStar from '~icons/icon-park-outline/star'
import IconTable from '~icons/icon-park-outline/table'
import IconText from '~icons/icon-park-outline/text'
import IconTextArea from '~icons/icon-park-outline/text-message'
import IconTree from '~icons/icon-park-outline/tree-diagram'
import IconUndo from '~icons/icon-park-outline/undo'
import IconVideo from '~icons/icon-park-outline/video'

export const COMPONENT_ICONS: Record<string, Component> = {
  'Grid': IconGrid,
  'List:horizontal': IconColumn,
  'List:vertical': IconList,
  'Panel': IconPanel,
  'Form': IconForm,
  'DataTable': IconTable,
  'ButtonBar': IconBar,
  'Spacer': IconDistribute,
  'Button:undo': IconUndo,
  'Button:redo': IconRedo,
  'Button:prev': IconLeft,
  'Button:next': IconRight,
  'Button:view-data': IconPreview,
  'Button:export': IconDownload,
  'Button:log': IconLogs,
  'Button:save': IconSave,
  'Button:submit': IconCheck,
  'Canvas': IconCanvas,
  'Image': IconImage,
  'Text': IconText,
  'HyperText': IconCode,
  'Audio': IconAudio,
  'Video': IconVideo,
  'Rectangle': IconRectangle,
  'RectangleLabels': IconRectangle,
  'PolygonLabels': IconPolygon,
  'KeyPointLabels': IconPoint,
  'BrushLabels': IconBrush,
  'Labels': IconLabel,
  'Choices': IconChoices,
  'Taxonomy': IconTree,
  'TextArea': IconTextArea,
  'Number': IconNumber,
  'DateTime': IconCalendar,
  'Rating': IconStar,
  'Header': IconHeader,
}
