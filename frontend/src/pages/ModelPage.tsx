import {Banner} from '@astryxdesign/core/Banner';
import {Skeleton} from '@astryxdesign/core/Skeleton';
import type {ModelInfo} from '../api';
import {formatDecimal, formatInteger, formatPercent, usePageMeta} from '../meta';
import {ROUTES, RouterLink} from '../router';
import {useModelInfo} from '../useModelInfo';

const METRIC_ROWS = [
  {key: 'level_9_top1', label: 'Código de 9 dígitos, primera opción'},
  {key: 'level_9_top3', label: 'Código de 9 dígitos, entre las tres'},
  {key: 'level_5_top1', label: 'Subclase de 5 dígitos, primera opción'},
  {key: 'level_5_top3', label: 'Subclase de 5 dígitos, entre las tres'},
  {key: 'level_9_macro_f1', label: 'F1 macro a 9 dígitos (castiga ignorar códigos raros)'},
] as const;

const SUBSET_LABELS: Record<string, string> = {
  proceso_unico: 'Procesos de un solo ítem',
  proceso_multi_varios_codigos: 'Procesos con varios ítems y varios códigos',
  proceso_multi_un_codigo: 'Rubros que heredan el código de la obra',
  anio_2025: 'Compras de 2025',
  anio_2026: 'Compras de 2026',
  texto_libre: 'Descripciones distintas al nombre del catálogo',
};

export function ModelPage() {
  usePageMeta(
    'Ficha del modelo',
    'Métricas con intervalos, límites, sesgos conocidos y usos no previstos del clasificador CPC-mini.',
  );
  const state = useModelInfo();
  return (
    <article className="doc">
      <h1>Ficha del modelo</h1>
      <p className="lead">Lo que mide, dónde falla y para qué no sirve. Todas las cifras vienen del modelo en servicio.</p>
      {state.status === 'loading' ? <Skeleton height={320} radius={2} /> : null}
      {state.status === 'error' ? <Banner status="error" title="Error al cargar la ficha" description={state.message} /> : null}
      {state.status === 'ready' ? <ModelSheet info={state.info} /> : null}
    </article>
  );
}

function ModelSheet({info}: {info: ModelInfo}) {
  const subsets = Object.entries(info.subsets).filter(([name]) => name in SUBSET_LABELS);
  return (
    <>
      <section className="doc__section" aria-labelledby="exactitud">
        <h2 id="exactitud">Exactitud en compras nunca vistas</h2>
        <p>
          Prueba con compras de 2025 y 2026. Ninguna descripción de prueba aparece, ni casi idéntica, en
          entrenamiento (2015 a 2023) ni en validación (2024). Intervalos del 95 % por bootstrap.
        </p>
        <div className="table-scroll">
        <table className="sheet-table">
          <caption className="visually-hidden">Exactitud del modelo {info.name}</caption>
          <thead>
            <tr>
              <th scope="col">Medida</th>
              <th scope="col" className="num">
                Valor
              </th>
              <th scope="col" className="num">
                Intervalo 95 %
              </th>
            </tr>
          </thead>
          <tbody>
            {METRIC_ROWS.map((row) => {
              const value = info.metrics[row.key];
              const interval = info.intervals[row.key];
              return (
                <tr key={row.key}>
                  <th scope="row">{row.label}</th>
                  <td className="num">{value === undefined ? 'sin dato' : formatPercent(value)}</td>
                  <td className="num">
                    {interval ? `${formatPercent(interval[0])} a ${formatPercent(interval[1])}` : 'sin dato'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        </div>
      </section>

      <section className="doc__section" aria-labelledby="donde-falla">
        <h2 id="donde-falla">Dónde falla y por qué</h2>
        <p>
          En obras con muchos rubros, el SERCOP registra cada línea con el código de la obra completa: «breaker de
          16 A» aparece como servicio de construcción. Esa etiqueta no se puede deducir del texto del rubro, y el
          modelo lo refleja.
        </p>
        {subsets.length > 0 ? (
          <div className="table-scroll">
          <table className="sheet-table">
            <caption className="visually-hidden">Exactitud por tipo de compra</caption>
            <thead>
              <tr>
                <th scope="col">Tipo de compra</th>
                <th scope="col" className="num">
                  Descripciones
                </th>
                <th scope="col" className="num">
                  Primera opción
                </th>
                <th scope="col" className="num">
                  Entre las tres
                </th>
              </tr>
            </thead>
            <tbody>
              {subsets.map(([name, subset]) => (
                <tr key={name}>
                  <th scope="row">{SUBSET_LABELS[name]}</th>
                  <td className="num">{formatInteger(subset.n)}</td>
                  <td className="num">{formatPercent(subset.top1)}</td>
                  <td className="num">{formatPercent(subset.top3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        ) : null}
      </section>

      <section className="doc__section doc__columns" aria-labelledby="uso">
        <div>
          <h2 id="uso">Uso previsto</h2>
          <p>{info.intended_use}</p>
        </div>
        <div>
          <h2>Usos no previstos</h2>
          <p>{info.not_intended_use}</p>
        </div>
      </section>

      <section className="doc__section" aria-labelledby="ficha-tecnica">
        <h2 id="ficha-tecnica">Ficha técnica</h2>
        <dl className="figures">
          <div className="figures__row">
            <dt>Modelo en servicio</dt>
            <dd>{info.family}</dd>
          </div>
          <div className="figures__row">
            <dt>Umbral de respuesta</dt>
            <dd className="num">{info.threshold > 1 ? 'siempre se abstiene' : formatPercent(info.threshold)}</dd>
          </div>
          <div className="figures__row">
            <dt>Exactitud exigida a lo respondido</dt>
            <dd className="num">{formatPercent(info.target_precision)}</dd>
          </div>
          {info.latency_ms_p50 !== null ? (
            <div className="figures__row">
              <dt>Latencia típica en CPU</dt>
              <dd className="num">{formatDecimal(info.latency_ms_p50)} ms</dd>
            </div>
          ) : null}
          {info.size_mb !== null ? (
            <div className="figures__row">
              <dt>Tamaño en disco</dt>
              <dd className="num">{formatInteger(Math.round(info.size_mb))} MB</dd>
            </div>
          ) : null}
          <div className="figures__row">
            <dt>Versión del dataset</dt>
            <dd className="num">{info.dataset_hash.slice(0, 12)}</dd>
          </div>
          <div className="figures__row">
            <dt>Corte de los datos</dt>
            <dd>Registro del 10 de noviembre de 2026</dd>
          </div>
        </dl>
        <p>
          Los escalones con mmBERT-small y Qwen3-0.6B están implementados pero aún no se entrenan: necesitan GPU.
          Sus resultados se publicarán cuando existan, aunque no superen a esta línea base. Fuente de los datos en{' '}
          <RouterLink to={ROUTES.data}>Datos y licencias</RouterLink>.
        </p>
      </section>
    </>
  );
}
