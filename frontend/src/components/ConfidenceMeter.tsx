import {formatPercent} from '../meta';

interface MeterProps {
  value: number;
  threshold: number;
  label: string;
}

/** Confianza calibrada con la marca del umbral de respuesta (rol "meter", no barra de progreso). */
export function ConfidenceMeter({value, threshold, label}: MeterProps) {
  const clamped = Math.min(1, Math.max(0, value));
  const mark = Math.min(1, Math.max(0, threshold));
  return (
    <div
      className="meter"
      role="meter"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(clamped * 100)}
      aria-valuetext={formatPercent(clamped)}
    >
      <span className="meter__track">
        <span className="meter__fill" style={{transform: `scaleX(${clamped})`}} />
        {threshold <= 1 ? (
          <span className="meter__threshold" style={{insetInlineStart: `${mark * 100}%`}} title="Umbral de respuesta" />
        ) : null}
      </span>
    </div>
  );
}
