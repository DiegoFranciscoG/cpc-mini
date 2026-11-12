/**
 * Firma de la pantalla: el código de 9 dígitos desglosado en su jerarquía. Cada regla bajo los
 * dígitos marca un nivel (grupo, subclase CPC de registro de proveedores y código SERCOP).
 */
const LEVELS = [
  {digits: 3, name: 'Grupo'},
  {digits: 5, name: 'Subclase CPC'},
  {digits: 9, name: 'Código SERCOP'},
] as const;

export function CodeRuler({code}: {code: string}) {
  const digits = code.split('');
  return (
    <figure className="ruler" aria-label={`Código ${code} desglosado por niveles`}>
      <ol className="ruler__digits" aria-hidden="true">
        {digits.map((digit, index) => (
          <li key={index} className="ruler__digit">
            {digit}
          </li>
        ))}
      </ol>
      <ul className="ruler__levels">
        {LEVELS.map((level) => (
          <li key={level.digits} className="ruler__level" data-digits={level.digits}>
            <span className="ruler__name">{level.name}</span>{' '}
            <span className="ruler__code num">{code.slice(0, level.digits)}</span>
          </li>
        ))}
      </ul>
    </figure>
  );
}
