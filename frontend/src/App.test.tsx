import {act, screen} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {describe, expect, it, vi} from 'vitest';
import {App} from './App';
import {ApiError, fetchModelInfo, predict} from './api';
import {CodeRuler} from './components/CodeRuler';
import {NoCookiesNotice} from './components/NoCookiesNotice';
import {NOTICE_STORAGE_KEY} from './content/site';
import {navigate} from './router';
import {json, MODEL_INFO, mockFetch, renderApp} from './test/utils';

function go(path: string) {
  act(() => navigate(path));
}

describe('Rutas y páginas', () => {
  it('navega entre páginas sin recargar y marca la actual', async () => {
    mockFetch({'/api/v1/model': () => json(MODEL_INFO)});
    renderApp(<App />);
    const nav = screen.getByRole('navigation', {name: 'Principal'});
    expect(nav.querySelector('[aria-current="page"]')).toHaveTextContent('Clasificar');
    await userEvent.click(screen.getAllByRole('link', {name: 'El modelo'})[0]!);
    expect(await screen.findByRole('heading', {level: 1, name: 'Ficha del modelo'})).toBeInTheDocument();
    expect(window.location.pathname).toBe('/modelo');
    expect(nav.querySelector('[aria-current="page"]')).toHaveTextContent('El modelo');
  });

  it('T-09: la atribución y la licencia aparecen en todas las páginas y en Datos y licencias', async () => {
    mockFetch({'/api/v1/model': () => json(MODEL_INFO)});
    renderApp(<App />);
    expect(screen.getByRole('contentinfo')).toHaveTextContent('SERCOP');
    expect(screen.getByRole('contentinfo')).toHaveTextContent('Open Contracting Partnership');
    expect(screen.getByRole('contentinfo')).toHaveTextContent('CC BY 3.0 Ecuador');
    go('/datos');
    expect(await screen.findByRole('heading', {level: 1, name: 'Datos y licencias'})).toBeInTheDocument();
    expect(screen.getByRole('link', {name: /Texto legal de la licencia/})).toHaveAttribute(
      'href',
      'https://creativecommons.org/licenses/by/3.0/ec/',
    );
    expect(document.title).toBe('Datos y licencias | CPC-mini');
  });

  it('muestra aviso legal, privacidad, cookies y 404', async () => {
    mockFetch({'/api/v1/model': () => json(MODEL_INFO)});
    renderApp(<App />);
    go('/aviso-legal');
    expect(await screen.findByText(/no está respaldado por ellas/)).toBeInTheDocument();
    go('/privacidad');
    expect(await screen.findByText(/Ley Orgánica de Protección de Datos Personales/)).toBeInTheDocument();
    expect(screen.getByText(/Superintendencia de Protección de Datos Personales/)).toBeInTheDocument();
    go('/cookies');
    expect(await screen.findByText('cpcmini.aviso-sin-cookies')).toBeInTheDocument();
    go('/no-existe');
    expect(await screen.findByRole('heading', {name: 'Esta página no existe'})).toBeInTheDocument();
  });

  it('la ficha del modelo muestra métricas, intervalos y subgrupos de la API', async () => {
    mockFetch({'/api/v1/model': () => json(MODEL_INFO)});
    window.history.replaceState({}, '', '/modelo');
    renderApp(<App />);
    expect(await screen.findByText('19% a 21%')).toBeInTheDocument();
    expect(screen.getByText('Procesos de un solo ítem')).toBeInTheDocument();
    expect(screen.queryByText('otro')).not.toBeInTheDocument();
    expect(screen.getByText('4.2 ms')).toBeInTheDocument();
    expect(screen.getAllByText('sin dato').length).toBeGreaterThan(0);
  });

  it('la ficha del modelo informa si la API falla', async () => {
    mockFetch({'/api/v1/model': () => json({}, 500)});
    window.history.replaceState({}, '', '/modelo');
    renderApp(<App />);
    expect(await screen.findByText('Error al cargar la ficha')).toBeInTheDocument();
  });
});

describe('Componentes', () => {
  it('desglosa el código en sus tres niveles', () => {
    renderApp(<CodeRuler code="013492912" />);
    expect(screen.getByRole('figure', {name: 'Código 013492912 desglosado por niveles'})).toBeInTheDocument();
    expect(screen.getByText('013')).toBeInTheDocument();
    expect(screen.getByText('01349')).toBeInTheDocument();
    expect(screen.getByText('013492912')).toBeInTheDocument();
  });

  it('el aviso sin cookies se cierra y lo recuerda', async () => {
    const {unmount} = renderApp(<NoCookiesNotice />);
    await userEvent.click(screen.getByRole('button', {name: 'Entendido'}));
    expect(screen.queryByRole('complementary', {name: 'Aviso sobre cookies'})).not.toBeInTheDocument();
    expect(window.localStorage.getItem(NOTICE_STORAGE_KEY)).toBe('1');
    unmount();
    renderApp(<NoCookiesNotice />);
    expect(screen.queryByRole('complementary', {name: 'Aviso sobre cookies'})).not.toBeInTheDocument();
  });

  it('el aviso funciona aunque el almacenamiento esté bloqueado', async () => {
    const proto = Object.getPrototypeOf(window.localStorage) as Storage;
    const getItem = vi.spyOn(proto, 'getItem').mockImplementation(() => {
      throw new Error('bloqueado');
    });
    vi.spyOn(proto, 'setItem').mockImplementation(() => {
      throw new Error('bloqueado');
    });
    renderApp(<NoCookiesNotice />);
    await userEvent.click(screen.getByRole('button', {name: 'Entendido'}));
    expect(screen.queryByRole('complementary', {name: 'Aviso sobre cookies'})).not.toBeInTheDocument();
    expect(getItem).toHaveBeenCalled();
  });
});

describe('Cliente de la API', () => {
  it('traduce los errores HTTP y de red a mensajes claros', async () => {
    mockFetch({'/api/v1/predictions': () => json({}, 422)});
    await expect(predict('x')).rejects.toMatchObject({kind: 'validation'});
    mockFetch({'/api/v1/predictions': () => json({}, 503)});
    await expect(predict('x')).rejects.toMatchObject({kind: 'server'});
    vi.stubGlobal('fetch', vi.fn(async () => Promise.reject(new TypeError('offline'))));
    const error = await fetchModelInfo().catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).kind).toBe('network');
  });
});
