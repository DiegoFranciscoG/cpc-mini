import type {ReactNode} from 'react';
import {Link} from '@astryxdesign/core/Link';
import {ATTRIBUTION, DATA_SOURCE, OWNER, OWNER_GITHUB, REPOSITORY} from '../content/site';
import {ROUTES, RouterLink} from '../router';
import {Logo} from './Logo';
import {NoCookiesNotice} from './NoCookiesNotice';

const NAV = [
  {to: ROUTES.classify, label: 'Clasificar'},
  {to: ROUTES.model, label: 'El modelo'},
  {to: ROUTES.data, label: 'Datos y licencias'},
];

const LEGAL = [
  {to: ROUTES.legal, label: 'Aviso legal'},
  {to: ROUTES.privacy, label: 'Privacidad'},
  {to: ROUTES.cookies, label: 'Cookies'},
  {to: ROUTES.data, label: 'Datos y licencias'},
];

export function Shell({children}: {children: ReactNode}) {
  return (
    <>
      <a className="skip-link" href="#contenido">
        Saltar al contenido
      </a>
      <header className="topbar">
        <div className="container topbar__inner">
          <RouterLink to={ROUTES.classify} className="topbar__brand" aria-label="CPC-mini, inicio">
            <Logo />
          </RouterLink>
          <nav aria-label="Principal">
            <ul className="topbar__nav">
              {NAV.map((item) => (
                <li key={item.to}>
                  <RouterLink to={item.to} className="topbar__link">
                    {item.label}
                  </RouterLink>
                </li>
              ))}
            </ul>
          </nav>
        </div>
      </header>
      <main id="contenido" tabIndex={-1} className="container main">
        {children}
      </main>
      <footer className="footer">
        <div className="container footer__inner">
          <div className="footer__about">
            <Logo size={28} />
            <p className="footer__attribution">
              {ATTRIBUTION}{' '}
              <Link href={DATA_SOURCE.licenseUrl} isExternalLink newTabLabel="(se abre en otra pestaña)" type="inherit">
                Ver licencia
              </Link>
            </p>
            <p className="footer__disclaimer">
              Proyecto independiente de {OWNER}. No es un servicio oficial ni está afiliado al SERCOP; las sugerencias
              requieren revisión humana.
            </p>
          </div>
          <nav aria-label="Legal" className="footer__nav">
            <ul>
              {LEGAL.map((item) => (
                <li key={item.label}>
                  <RouterLink to={item.to}>{item.label}</RouterLink>
                </li>
              ))}
              <li>
                <Link href={REPOSITORY} isExternalLink newTabLabel="(se abre en otra pestaña)" type="inherit">
                  Código fuente
                </Link>
              </li>
              <li>
                <Link href={OWNER_GITHUB} isExternalLink newTabLabel="(se abre en otra pestaña)" type="inherit">
                  Autor en GitHub
                </Link>
              </li>
            </ul>
          </nav>
        </div>
      </footer>
      <NoCookiesNotice />
    </>
  );
}
