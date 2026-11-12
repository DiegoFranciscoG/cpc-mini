import {useState} from 'react';
import {Button} from '@astryxdesign/core/Button';
import {NOTICE_STORAGE_KEY} from '../content/site';
import {ROUTES, RouterLink} from '../router';

function readDismissed(): boolean {
  try {
    return window.localStorage.getItem(NOTICE_STORAGE_KEY) === '1';
  } catch {
    return false;
  }
}

function writeDismissed(): void {
  try {
    window.localStorage.setItem(NOTICE_STORAGE_KEY, '1');
  } catch {
    // Almacenamiento bloqueado (modo privado): el aviso simplemente vuelve a mostrarse.
  }
}

/**
 * Aviso informativo: el sitio no usa cookies ni rastreadores, así que no pide consentimiento;
 * sólo informa y recuerda en tu navegador que lo cerraste.
 */
export function NoCookiesNotice() {
  const [dismissed, setDismissed] = useState(readDismissed);
  if (dismissed) return null;
  return (
    <aside className="notice" aria-label="Aviso sobre cookies">
      <p className="notice__text">
        Este sitio no usa cookies ni herramientas de seguimiento. Lo que escribes se procesa para responderte y no
        se guarda. <RouterLink to={ROUTES.cookies}>Detalles</RouterLink>
      </p>
      <Button
        label="Entendido"
        variant="secondary"
        size="sm"
        onClick={() => {
          writeDismissed();
          setDismissed(true);
        }}
      />
    </aside>
  );
}
