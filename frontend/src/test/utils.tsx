import type {ReactElement} from 'react';
import {render} from '@testing-library/react';
import {InternationalizationProvider} from '@astryxdesign/core/i18n';
import spanish from '@astryxdesign/core/locales/es-ES.generated.js';
import {Theme} from '@astryxdesign/core/theme';
import {vi} from 'vitest';
import {themes, defaultThemeSlug} from '../astryx-themes';
import type {ModelInfo, Prediction} from '../api';

export function renderApp(ui: ReactElement) {
  return render(
    <InternationalizationProvider locale="es-EC" messages={{'es-EC': spanish}}>
      <Theme theme={themes[defaultThemeSlug]} mode="light">
        {ui}
      </Theme>
    </InternationalizationProvider>,
  );
}

export const MODEL_INFO: ModelInfo = {
  name: 'tfidf_logreg',
  family: '1. Base: TF-IDF + regresión logística jerárquica',
  dataset_hash: 'f064fad0abaeb22a6222d6a6e8cc454e',
  trained_at: '2026-11-12T20:00:00+00:00',
  threshold: 0.42,
  target_precision: 0.9,
  metrics: {level_9_top1: 0.2, level_9_top3: 0.35, level_5_top1: 0.3, level_5_top3: 0.5, level_9_macro_f1: 0.1},
  intervals: {level_9_top1: [0.19, 0.21]},
  subsets: {proceso_unico: {n: 3326, top1: 0.3, top3: 0.45}, otro: {n: 1, top1: 0, top3: 0}},
  latency_ms_p50: 4.2,
  size_mb: 61,
  data_attribution: 'Datos: SERCOP vía OCP, CC BY 3.0 EC.',
  data_license: 'CC BY 3.0 EC',
  data_license_url: 'https://creativecommons.org/licenses/by/3.0/ec/',
  intended_use: 'Sugerir códigos con revisión humana.',
  not_intended_use: 'Decisiones automáticas.',
};

export function prediction(overrides: Partial<Prediction> = {}): Prediction {
  return {
    description: 'Paracetamol 500 mg',
    abstained: false,
    message: 'Sugerencias ordenadas por confianza.',
    threshold: 0.42,
    candidates: [
      {code9: '352603076', code5: '35260', label: 'Paracetamol, sólido oral, 500 mg', confidence: 0.61},
      {code9: '352603022', code5: '35260', label: 'PARACETAMOL', confidence: 0.2},
      {code9: '625730011', code5: '62573', label: '', confidence: 0.05},
    ],
    model: 'tfidf_logreg',
    latency_ms: 5,
    ...overrides,
  };
}

/** fetch simulado: responde según la ruta. */
export function mockFetch(routes: Record<string, () => Response | Promise<Response>>) {
  const fn = vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.pathname : input.url;
    const handler = routes[url];
    if (!handler) return new Response('{}', {status: 404});
    return handler();
  });
  vi.stubGlobal('fetch', fn);
  return fn;
}

export function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {status, headers: {'Content-Type': 'application/json'}});
}
