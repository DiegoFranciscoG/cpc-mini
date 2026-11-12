/** Cliente de la API (mismo origen: el proxy de nginx o de Vite reenvía /api). */

export interface Candidate {
  code9: string;
  code5: string;
  label: string;
  confidence: number;
}

export interface Prediction {
  description: string;
  abstained: boolean;
  message: string;
  threshold: number;
  candidates: Candidate[];
  model: string;
  latency_ms: number;
}

export interface SubsetMetric {
  n: number;
  top1: number;
  top3: number;
}

export interface ModelInfo {
  name: string;
  family: string;
  dataset_hash: string;
  trained_at: string;
  threshold: number;
  target_precision: number;
  metrics: Record<string, number>;
  intervals: Record<string, [number, number]>;
  subsets: Record<string, SubsetMetric>;
  latency_ms_p50: number | null;
  size_mb: number | null;
  data_attribution: string;
  data_license: string;
  data_license_url: string;
  intended_use: string;
  not_intended_use: string;
}

export type ApiErrorKind = 'validation' | 'rate-limit' | 'server' | 'network';

export class ApiError extends Error {
  constructor(
    public readonly kind: ApiErrorKind,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

const TIMEOUT_MS = 15_000;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      signal: init?.signal ?? controller.signal,
      headers: {'Content-Type': 'application/json', Accept: 'application/json', ...init?.headers},
    });
  } catch {
    throw new ApiError('network', 'No hay conexión con el servicio. Revisa tu red e inténtalo de nuevo.');
  } finally {
    clearTimeout(timer);
  }
  if (response.ok) return (await response.json()) as T;
  if (response.status === 422) {
    throw new ApiError('validation', 'Revisa la descripción: debe tener entre 3 y 500 caracteres.');
  }
  if (response.status === 429) {
    throw new ApiError('rate-limit', 'Hiciste muchas consultas seguidas. Espera un minuto y vuelve a intentarlo.');
  }
  throw new ApiError('server', 'El servicio no pudo responder. Inténtalo de nuevo en unos segundos.');
}

export function predict(description: string, signal?: AbortSignal): Promise<Prediction> {
  return request<Prediction>('/api/v1/predictions', {
    method: 'POST',
    body: JSON.stringify({description}),
    signal,
  });
}

export function fetchModelInfo(signal?: AbortSignal): Promise<ModelInfo> {
  return request<ModelInfo>('/api/v1/model', {signal});
}
