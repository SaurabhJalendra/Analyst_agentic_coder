import { lazy, Suspense, useEffect, useState } from 'react';
import axios from 'axios';
import type Plotly from 'plotly.js-basic-dist-min';

// Lazy-load Chart so Plotly stays in its own bundle chunk (not the main index-*.js).
const Chart = lazy(() => import('../renderers/Chart'));

const BASE = import.meta.env.VITE_API_URL || '';

interface ChartPayload {
  artifact_id: string;
  kind: 'chart';
  title: string;
  payload: {
    data: Plotly.Data[];
    layout: Partial<Plotly.Layout>;
  };
}

interface Props {
  artifactId: string;
}

export function ChartArtifactBody({ artifactId }: Props) {
  const [state, setState] = useState<
    | { status: 'loading' }
    | { status: 'error' }
    | { status: 'ready'; chart: ChartPayload }
  >({ status: 'loading' });

  useEffect(() => {
    let cancelled = false;

    axios
      .get<ChartPayload>(`${BASE}/api/artifacts/${artifactId}/payload`)
      .then((res) => {
        if (!cancelled) {
          setState({ status: 'ready', chart: res.data });
        }
      })
      .catch(() => {
        if (!cancelled) {
          setState({ status: 'error' });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [artifactId]);

  if (state.status === 'loading') {
    return (
      <p className="text-[10px] text-slate-400 italic">Loading chart…</p>
    );
  }

  if (state.status === 'error') {
    return (
      <p className="text-[10px] text-slate-400 italic">Chart unavailable.</p>
    );
  }

  const { chart } = state;

  return (
    <Suspense
      fallback={
        <p className="text-[10px] text-slate-400 italic">Rendering chart…</p>
      }
    >
      <Chart
        data={chart.payload.data}
        layout={chart.payload.layout}
        title={chart.title}
      />
    </Suspense>
  );
}
