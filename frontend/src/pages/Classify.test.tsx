import {screen, waitFor, within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {describe, expect, it} from 'vitest';
import {Classify, withoutAbstainPrefix} from './Classify';
import {json, MODEL_INFO, mockFetch, prediction, renderApp} from '../test/utils';

describe('Clasificador', () => {
  it('muestra el estado vacío y las cifras reales del modelo', async () => {
    mockFetch({'/api/v1/model': () => json(MODEL_INFO)});
    renderApp(<Classify />);
    expect(screen.getByRole('heading', {level: 1, name: 'Del texto de compra al código CPC'})).toBeInTheDocument();
    expect(screen.getByText('Aquí aparecen las sugerencias')).toBeInTheDocument();
    expect(await screen.findByText('20%')).toBeInTheDocument();
    expect(screen.getByText('35%')).toBeInTheDocument();
    expect(document.title).toContain('CPC-mini');
  });

  it('valida la longitud mínima antes de consultar', async () => {
    const fetchMock = mockFetch({'/api/v1/model': () => json(MODEL_INFO)});
    renderApp(<Classify />);
    await userEvent.click(screen.getByRole('button', {name: 'Sugerir códigos'}));
    expect((await screen.findAllByText('Escribe al menos 3 caracteres.')).length).toBeGreaterThan(0);
    expect(fetchMock).not.toHaveBeenCalledWith('/api/v1/predictions', expect.anything());
  });

  it('consulta y muestra la ficha con el código desglosado', async () => {
    mockFetch({
      '/api/v1/model': () => json(MODEL_INFO),
      '/api/v1/predictions': () => json(prediction()),
    });
    renderApp(<Classify />);
    await userEvent.type(screen.getByRole('textbox', {name: /Descripción del ítem/}), 'Paracetamol 500 mg');
    await userEvent.click(screen.getByRole('button', {name: 'Sugerir códigos'}));
    const card = await screen.findByRole('article', {name: 'Más probable'});
    expect(within(card).getByText('61%')).toBeInTheDocument();
    expect(within(card).getByText('Paracetamol, sólido oral, 500 mg')).toBeInTheDocument();
    expect(within(card).getByText('35260')).toBeInTheDocument();
    expect(within(card).getByRole('meter', {name: /Confianza del código 352603076/})).toHaveAttribute('aria-valuenow', '61');
    const others = screen.getByRole('region', {name: 'Otras opciones'});
    expect(within(others).getByText('352603022')).toBeInTheDocument();
    expect(within(others).getByText('Sin etiqueta en el catálogo')).toBeInTheDocument();
  });

  it('usa un ejemplo y avisa cuando se abstiene', async () => {
    mockFetch({
      '/api/v1/model': () => json(MODEL_INFO),
      '/api/v1/predictions': () =>
        json(prediction({abstained: true, message: 'No sé: la confianza está por debajo del umbral.'})),
    });
    renderApp(<Classify />);
    await userEvent.click(screen.getByRole('button', {name: 'Resma de papel bond A4 de 75 g'}));
    expect(await screen.findByText('No sé: la confianza es baja')).toBeInTheDocument();
    expect(screen.getByText('La confianza está por debajo del umbral.')).toBeInTheDocument();
    expect(screen.getByRole('article', {name: 'Candidato más cercano'})).toBeInTheDocument();
  });

  it('dice «no sé» si no hay candidatos', async () => {
    mockFetch({
      '/api/v1/model': () => json(MODEL_INFO),
      '/api/v1/predictions': () => json(prediction({abstained: true, candidates: [], message: 'No sé: falta información.'})),
    });
    renderApp(<Classify />);
    await userEvent.click(screen.getByRole('button', {name: 'Servicio de limpieza de oficinas'}));
    expect(await screen.findByText('No sé: falta información para sugerir un código')).toBeInTheDocument();
  });

  it('muestra el error con reintento cuando el servicio falla', async () => {
    let calls = 0;
    mockFetch({
      '/api/v1/model': () => json({}, 500),
      '/api/v1/predictions': () => {
        calls += 1;
        return calls === 1 ? json({}, 429) : json(prediction());
      },
    });
    renderApp(<Classify />);
    expect(await screen.findByText('El servicio no pudo responder. Inténtalo de nuevo en unos segundos.')).toBeInTheDocument();
    await userEvent.type(screen.getByRole('textbox', {name: /Descripción del ítem/}), 'Guantes de nitrilo');
    await userEvent.click(screen.getByRole('button', {name: 'Sugerir códigos'}));
    expect(await screen.findByText(/Hiciste muchas consultas seguidas/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', {name: 'Reintentar'}));
    await waitFor(() => expect(screen.getByRole('article', {name: 'Más probable'})).toBeInTheDocument());
  });

  it('copia el código al portapapeles', async () => {
    mockFetch({'/api/v1/model': () => json(MODEL_INFO), '/api/v1/predictions': () => json(prediction())});
    const user = userEvent.setup();
    renderApp(<Classify />);
    await user.click(screen.getByRole('button', {name: 'Paracetamol 500 mg tabletas, caja x 100'}));
    await user.click(await screen.findByRole('button', {name: 'Copiar código'}));
    expect(await screen.findByRole('button', {name: 'Código copiado'})).toBeInTheDocument();
    await expect(navigator.clipboard.readText()).resolves.toBe('352603076');
  });

  it('quita el prefijo repetido del mensaje', () => {
    expect(withoutAbstainPrefix('No sé: la confianza es baja')).toBe('La confianza es baja');
    expect(withoutAbstainPrefix('texto')).toBe('Texto');
  });
});
