import { useMemo } from 'react';
// We use the basic dist to keep bundle smaller (line/scatter/bar; no 3D, no maps).
import Plotly from 'plotly.js-basic-dist-min';
import createPlotlyComponent from 'react-plotly.js/factory';

const Plot = createPlotlyComponent(Plotly);

export interface ChartProps {
  data: Plotly.Data[];
  layout?: Partial<Plotly.Layout>;
  title?: string;
  height?: number;
}

export function Chart({ data, layout, title, height = 240 }: ChartProps) {
  const fullLayout = useMemo<Partial<Plotly.Layout>>(() => ({
    title: title ? { text: title, font: { size: 12 } } : undefined,
    margin: { l: 36, r: 12, t: title ? 28 : 12, b: 28 },
    height,
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { family: 'Inter, system-ui, sans-serif', size: 10, color: '#475569' },
    showlegend: false,
    xaxis: { gridcolor: '#e2e8f0', zeroline: false, ...layout?.xaxis },
    yaxis: { gridcolor: '#e2e8f0', zeroline: false, ...layout?.yaxis },
    ...layout,
  }), [layout, title, height]);

  return (
    <Plot
      data={data}
      layout={fullLayout}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: '100%', height: `${height}px` }}
      useResizeHandler
    />
  );
}

// Default export so React.lazy() can consume Chart.tsx when an artifact card
// (Phase 3) wires up real chart payloads.
export default Chart;
