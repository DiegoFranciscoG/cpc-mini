import {useEffect, useState} from 'react';
import {ApiError, fetchModelInfo, type ModelInfo} from './api';

export type ModelInfoState =
  | {status: 'loading'}
  | {status: 'error'; message: string}
  | {status: 'ready'; info: ModelInfo};

/** Ficha del modelo servida por la API: las cifras de la web nunca se escriben a mano. */
export function useModelInfo(): ModelInfoState {
  const [state, setState] = useState<ModelInfoState>({status: 'loading'});
  useEffect(() => {
    const controller = new AbortController();
    fetchModelInfo(controller.signal)
      .then((info) => setState({status: 'ready', info}))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        const message = error instanceof ApiError ? error.message : 'No se pudo cargar la ficha del modelo.';
        setState({status: 'error', message});
      });
    return () => controller.abort();
  }, []);
  return state;
}
