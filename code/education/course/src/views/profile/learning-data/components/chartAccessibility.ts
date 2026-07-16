import type {
  PortraitDimension,
  PortraitTrendSeries,
  ResourcePreference,
} from '../learningPortraitViewModel';

export type ChartTableCell = string | number;

export interface ChartAccessibilityContent {
  label: string;
  summary: string;
  headers: string[];
  rows: ChartTableCell[][];
}

const finiteNumber = (value: unknown) => {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

export function formatChartValue(value: unknown, suffix = '') {
  const number = finiteNumber(value);
  if (number === null) return '暂无数据';
  const rounded = Math.round(number * 10) / 10;
  return `${Number.isInteger(rounded) ? rounded.toFixed(0) : rounded.toFixed(1)}${suffix}`;
}

export function buildGrowthChartAccessibility(
  labels: string[],
  series: PortraitTrendSeries[]
): ChartAccessibilityContent {
  const periodSummary = labels.length
    ? `${labels[0]}至${labels[labels.length - 1]}，共 ${labels.length} 个周期。`
    : '暂无周期数据。';
  const seriesSummary = series
    .map((item) => {
      const measured = item.values.filter(
        (value): value is number => finiteNumber(value) !== null
      );
      if (!measured.length) return `${item.label}暂无有效数据`;
      return `${item.label}从 ${formatChartValue(measured[0], '分')} 变化至 ${formatChartValue(
        measured[measured.length - 1],
        '分'
      )}`;
    })
    .join('；');

  return {
    label: '能力成长趋势图',
    summary: `${periodSummary}${seriesSummary || '暂无有效能力数据。'}`,
    headers: ['周期', ...series.map((item) => item.label)],
    rows: labels.map((label, index) => [
      label,
      ...series.map((item) => formatChartValue(item.values[index], '分')),
    ]),
  };
}

export function buildCapabilityChartAccessibility(
  dimensions: PortraitDimension[]
): ChartAccessibilityContent {
  const available = dimensions.filter((item) => finiteNumber(item.value) !== null);
  const strongest = [...available].sort((a, b) => b.value - a.value)[0];
  const priority = [...available].sort((a, b) => a.value - b.value)[0];
  const comparisonAvailable =
    available.length > 0 && available.every((item) => item.previous !== null);
  const partialComparisonAvailable =
    !comparisonAvailable && available.some((item) => item.previous !== null);
  const summaryParts = [
    strongest ? `当前表现较好的是${strongest.label}，${formatChartValue(strongest.value, '分')}` : '',
    priority ? `建议优先关注${priority.label}，${formatChartValue(priority.value, '分')}` : '',
    comparisonAvailable
      ? '雷达图同时展示 30 天前的数据用于比较'
      : partialComparisonAvailable
        ? '部分维度已积累 30 天前的数据，详见数据表；数据完整后再绘制对比轮廓'
        : '暂未积累 30 天前的对比数据',
  ].filter(Boolean);

  return {
    label: '核心能力画像雷达图',
    summary: `${summaryParts.join('；')}。`,
    headers: ['能力维度', '当前', '30 天前'],
    rows: dimensions.map((item) => [
      item.label,
      formatChartValue(item.value, '分'),
      formatChartValue(item.previous, '分'),
    ]),
  };
}

export function buildRhythmChartAccessibility(
  weekLabels: string[],
  dayLabels: string[],
  activity: number[][],
  hourLabels: string[],
  focusHours: number[]
): ChartAccessibilityContent {
  const activityRows: ChartTableCell[][] = activity.flatMap((row, weekIndex) =>
    row.map((value, dayIndex) => [
      '学习活跃度',
      `${weekLabels[weekIndex] || `第 ${weekIndex + 1} 周`}·周${
        dayLabels[dayIndex] || `第 ${dayIndex + 1} 天`
      }`,
      formatChartValue(value),
    ])
  );
  const focusRows: ChartTableCell[][] = focusHours.map((value, index) => [
    '单次专注时长',
    hourLabels[index] || `时段 ${index + 1}`,
    formatChartValue(value, ' 小时'),
  ]);

  const activePoints = activityRows
    .map((row) => ({ label: String(row[1]), value: finiteNumber(String(row[2])) ?? 0 }))
    .sort((a, b) => b.value - a.value);
  const focusPoints = focusHours
    .map((value, index) => ({ label: hourLabels[index] || `时段 ${index + 1}`, value }))
    .filter((item) => finiteNumber(item.value) !== null)
    .sort((a, b) => b.value - a.value);
  const activityPeak = activePoints[0];
  const focusPeak = focusPoints[0];

  return {
    label: '学习节律组合图',
    summary: [
      activityPeak
        ? `学习活跃度较高的时段是${activityPeak.label}，活跃度 ${formatChartValue(
            activityPeak.value
          )}`
        : '',
      focusPeak
        ? `单次专注时长峰值出现在${focusPeak.label}，为 ${formatChartValue(
            focusPeak.value,
            ' 小时'
          )}`
        : '',
    ]
      .filter(Boolean)
      .join('；') || '暂无可分析的学习节律数据。',
    headers: ['数据类型', '时段', '数值'],
    rows: [...activityRows, ...focusRows],
  };
}

export function buildResourceChartAccessibility(
  preferences: ResourcePreference[]
): ChartAccessibilityContent {
  const available = preferences.filter((item) => item.value !== null);
  const leading = [...available].sort((a, b) => (b.value || 0) - (a.value || 0))[0];

  return {
    label: '学习资源类型分布图',
    summary: leading
      ? `已生成和上传的资源中，数量占比较高的是${leading.label}，${formatChartValue(leading.value, '%')}。各资源类型的具体占比见数据表。`
      : '当前仅识别出推荐资源类型，尚未形成可比较的真实资源数量占比。',
    headers: ['资源类型', '占比'],
    rows: preferences.map((item) => [item.label, formatChartValue(item.value, '%')]),
  };
}
