/** Enrutador mínimo con la History API: seis rutas no justifican una dependencia más. */
import {useSyncExternalStore, type AnchorHTMLAttributes, type MouseEvent, type ReactNode} from 'react';

export const ROUTES = {
  classify: '/',
  model: '/modelo',
  data: '/datos',
  legal: '/aviso-legal',
  privacy: '/privacidad',
  cookies: '/cookies',
} as const;

export type RoutePath = (typeof ROUTES)[keyof typeof ROUTES];

const NAV_EVENT = 'cpcmini:navigate';

function subscribe(onChange: () => void): () => void {
  window.addEventListener('popstate', onChange);
  window.addEventListener(NAV_EVENT, onChange);
  return () => {
    window.removeEventListener('popstate', onChange);
    window.removeEventListener(NAV_EVENT, onChange);
  };
}

function currentPath(): string {
  const path = window.location.pathname.replace(/\/+$/, '');
  return path === '' ? '/' : path;
}

export function usePath(): string {
  return useSyncExternalStore(subscribe, currentPath, () => '/');
}

export function navigate(to: string): void {
  if (to === currentPath()) return;
  window.history.pushState({}, '', to);
  window.dispatchEvent(new Event(NAV_EVENT));
  window.scrollTo({top: 0});
  document.getElementById('contenido')?.focus({preventScroll: true});
}

interface LinkProps extends AnchorHTMLAttributes<HTMLAnchorElement> {
  to: string;
  children: ReactNode;
}

/** Enlace interno: navegación sin recargar, respetando Ctrl/Cmd+clic y clic central. */
export function RouterLink({to, children, onClick, ...rest}: LinkProps) {
  const path = usePath();
  const handle = (event: MouseEvent<HTMLAnchorElement>) => {
    onClick?.(event);
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }
    event.preventDefault();
    navigate(to);
  };
  return (
    <a href={to} onClick={handle} aria-current={path === to ? 'page' : undefined} {...rest}>
      {children}
    </a>
  );
}
