/**
 * Marca de CPC-mini: un tronco con tres ramas que se alargan (3, 5 y 9 dígitos), como la jerarquía
 * del CPC; el último tramo, en mandarina, es el código elegido.
 */
interface LogoProps {
  withWordmark?: boolean;
  size?: number;
}

export function LogoMark({size = 32}: {size?: number}) {
  return (
    <svg className="logo-mark" width={size} height={size} viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <rect className="logo-mark__plate" width="32" height="32" rx="7" />
      <path className="logo-mark__stem" d="M8 7.5v16" />
      <path className="logo-mark__branch" d="M8 9h6M8 16h10M8 23h10" />
      <path className="logo-mark__leaf" d="M18 23h7" />
    </svg>
  );
}

export function Logo({withWordmark = true, size = 32}: LogoProps) {
  return (
    <span className="logo">
      <LogoMark size={size} />
      {withWordmark ? <span className="logo__word">CPC-mini</span> : null}
    </span>
  );
}
