import {useRef, useState, type FormEvent} from 'react';
import {Banner} from '@astryxdesign/core/Banner';
import {Button} from '@astryxdesign/core/Button';
import {Skeleton} from '@astryxdesign/core/Skeleton';
import {TextArea} from '@astryxdesign/core/TextArea';
import {ApiError, predict, type Prediction} from '../api';
import {CodeRuler} from '../components/CodeRuler';
import {ConfidenceMeter} from '../components/ConfidenceMeter';
import {EXAMPLES} from '../content/site';
import {formatPercent, usePageMeta} from '../meta';
import {ROUTES, RouterLink} from '../router';
import {useModelInfo} from '../useModelInfo';

const MAX_CHARS = 500;
const MIN_CHARS = 3;

type ResultState =
  | {status: 'empty'}
  | {status: 'loading'}
  | {status: 'error'; message: string}
  | {status: 'done'; prediction: Prediction};

export function Classify() {
  usePageMeta(
    'Sugiere el código CPC de una compra pública',
    'Escribe la descripción de un ítem de compra pública de Ecuador y recibe los tres códigos CPC más probables, con su confianza calibrada, o «no sé».',
  );
  const [text, setText] = useState('');
  const [result, setResult] = useState<ResultState>({status: 'empty'});
  const [touched, setTouched] = useState(false);
  const pending = useRef<AbortController | null>(null);
  const tooShort = text.trim().length < MIN_CHARS;

  async function run(description: string) {
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    setResult({status: 'loading'});
    try {
      const prediction = await predict(description, controller.signal);
      if (!controller.signal.aborted) setResult({status: 'done', prediction});
    } catch (error: unknown) {
      if (controller.signal.aborted) return;
      const message = error instanceof ApiError ? error.message : 'Algo falló al consultar el modelo.';
      setResult({status: 'error', message});
    }
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTouched(true);
    if (tooShort) return;
    void run(text.trim());
  }

  function tryExample(example: string) {
    setText(example);
    setTouched(false);
    void run(example);
  }

  return (
    <div className="classify">
      <section className="classify__work" aria-labelledby="titulo">
        <h1 id="titulo">Del texto de compra al código CPC</h1>
        <p className="lead">Describe el ítem como en el pliego. El modelo propone tres códigos y dice «no sé» cuando duda.</p>
        <form className="classify__form" onSubmit={onSubmit} noValidate>
          <TextArea
            label="Descripción del ítem"
            description="Producto o servicio con su medida, material o presentación."
            value={text}
            onChange={(value) => setText(value.slice(0, MAX_CHARS))}
            maxLength={MAX_CHARS}
            placeholder="Por ejemplo: guantes de nitrilo talla M, caja x 100"
            isRequired
            status={touched && tooShort ? {type: 'error', message: `Escribe al menos ${MIN_CHARS} caracteres.`} : undefined}
          />
          <div className="classify__actions">
            <Button type="submit" variant="primary" label="Sugerir códigos" isLoading={result.status === 'loading'} />
          </div>
        </form>
        <div className="examples">
          <p className="examples__label" id="ejemplos">
            O prueba con una compra real
          </p>
          <ul className="examples__list" aria-labelledby="ejemplos">
            {EXAMPLES.map((example) => (
              <li key={example}>
                <button type="button" className="chip" onClick={() => tryExample(example)}>
                  {example}
                </button>
              </li>
            ))}
          </ul>
        </div>
        <div className="results" aria-live="polite" aria-busy={result.status === 'loading'}>
          <Results state={result} onRetry={() => void run(text.trim() || EXAMPLES[0])} />
        </div>
      </section>
      <ModelAside />
    </div>
  );
}

/** El título del aviso ya dice «No sé»; la descripción no lo repite. */
export function withoutAbstainPrefix(message: string): string {
  const rest = message.replace(/^No sé:\s*/u, '');
  return rest.charAt(0).toUpperCase() + rest.slice(1);
}

function Results({state, onRetry}: {state: ResultState; onRetry: () => void}) {
  if (state.status === 'empty') {
    return (
      <div className="results__empty">
        <h2>Aquí aparecen las sugerencias</h2>
        <p>Verás el código de 9 dígitos, su subclase de 5 dígitos y la confianza de cada opción.</p>
      </div>
    );
  }
  if (state.status === 'loading') {
    return (
      <div className="results__loading" aria-label="Consultando el modelo">
        <Skeleton height={56} radius={2} />
        <Skeleton height={120} radius={2} index={1} />
        <Skeleton height={44} radius={2} index={2} />
      </div>
    );
  }
  if (state.status === 'error') {
    return (
      <Banner
        status="error"
        title="Error: no hubo respuesta del modelo"
        description={state.message}
        endContent={<Button label="Reintentar" variant="secondary" size="sm" onClick={onRetry} />}
      />
    );
  }
  const {prediction} = state;
  const [first, ...rest] = prediction.candidates;
  if (!first) {
    return (
      <Banner
        status="warning"
        title="No sé: falta información para sugerir un código"
        description={withoutAbstainPrefix(prediction.message)}
      />
    );
  }
  return (
    <div className="results__done">
      {prediction.abstained ? (
        <Banner status="warning" title="No sé: la confianza es baja" description={withoutAbstainPrefix(prediction.message)} />
      ) : null}
      <article className={`entry${prediction.abstained ? ' entry--doubtful' : ''}`} aria-labelledby="mas-probable">
        <header className="entry__head">
          <h2 id="mas-probable" className="entry__kind">
            {prediction.abstained ? 'Candidato más cercano' : 'Más probable'}
          </h2>
          <p className="entry__figure num">{formatPercent(first.confidence)}</p>
        </header>
        <div className="entry__body notebook">
          <CodeRuler code={first.code9} />
          <p className="entry__label">{first.label || 'Sin etiqueta en el catálogo'}</p>
          <ConfidenceMeter
            value={first.confidence}
            threshold={prediction.threshold}
            label={`Confianza del código ${first.code9}`}
          />
          <p className="entry__note">
            {prediction.threshold <= 1
              ? `La raya marca el umbral de respuesta (${formatPercent(prediction.threshold)}), calibrado para acertar 9 de cada 10 veces en validación.`
              : 'En validación ninguna confianza alcanzó 9 aciertos de cada 10, así que este modelo siempre responde «no sé» y muestra candidatos como referencia.'}
          </p>
          <CopyButton code={first.code9} />
        </div>
      </article>
      {rest.length > 0 ? (
        <section className="alternatives" aria-labelledby="otras">
          <h2 id="otras" className="alternatives__title">
            Otras opciones
          </h2>
          <ol className="ruled">
            {rest.map((candidate) => (
              <li key={candidate.code9} className="alternatives__row">
                <span className="alternatives__code num">{candidate.code9}</span>
                <span className="alternatives__label">{candidate.label || 'Sin etiqueta en el catálogo'}</span>
                <span className="alternatives__figure num">{formatPercent(candidate.confidence)}</span>
              </li>
            ))}
          </ol>
        </section>
      ) : null}
    </div>
  );
}

function CopyButton({code}: {code: string}) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }
  return (
    <div className="copy">
      <Button label={copied ? 'Código copiado' : 'Copiar código'} variant="secondary" size="sm" onClick={() => void copy()} />
    </div>
  );
}

function ModelAside() {
  const state = useModelInfo();
  return (
    <aside className="aside" aria-labelledby="como-leer">
      <h2 id="como-leer">Cómo leer el resultado</h2>
      <p>
        El modelo aprendió de casi 196 mil descripciones únicas de compras del SERCOP entre 2015 y 2023, y su
        confianza se calibró con las compras de 2024.
      </p>
      {state.status === 'loading' ? <Skeleton height={140} radius={2} /> : null}
      {state.status === 'error' ? <p className="aside__error">{state.message}</p> : null}
      {state.status === 'ready' ? (
        <dl className="figures">
          <div className="figures__row">
            <dt>Código exacto en la primera opción</dt>
            <dd className="num">{formatPercent(state.info.metrics.level_9_top1 ?? 0)}</dd>
          </div>
          <div className="figures__row">
            <dt>Código exacto entre las tres</dt>
            <dd className="num">{formatPercent(state.info.metrics.level_9_top3 ?? 0)}</dd>
          </div>
          <div className="figures__row">
            <dt>Subclase de 5 dígitos entre las tres</dt>
            <dd className="num">{formatPercent(state.info.metrics.level_5_top3 ?? 0)}</dd>
          </div>
        </dl>
      ) : null}
      <p className="aside__more">
        Medido con compras de 2025 y 2026 que el modelo nunca vio. <RouterLink to={ROUTES.model}>Ficha completa</RouterLink>
      </p>
    </aside>
  );
}
