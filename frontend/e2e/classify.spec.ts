import {expect, test} from '@playwright/test';

test.describe('flujo crítico', () => {
  test('clasifica una descripción real y muestra tres candidatos', async ({page}) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    await page.goto('/');
    await expect(page).toHaveTitle(/CPC-mini/);
    await page.getByRole('button', {name: 'Entendido'}).click();
    await page.getByRole('textbox', {name: /Descripción del ítem/}).fill('Resma de papel bond A4 de 75 g');
    await page.getByRole('button', {name: 'Sugerir códigos'}).click();
    const card = page.getByRole('article', {name: /Más probable|Candidato más cercano/});
    await expect(card).toBeVisible();
    await expect(card.getByRole('meter')).toHaveAttribute('aria-valuenow', /\d+/);
    await expect(card.getByRole('figure')).toContainText('Subclase CPC');
    await expect(page.getByRole('region', {name: 'Otras opciones'}).getByRole('listitem')).toHaveCount(2);
    expect(errors).toEqual([]);
  });

  test('responde «no sé» ante una descripción sin información', async ({page}) => {
    await page.goto('/');
    await page.getByRole('textbox', {name: /Descripción del ítem/}).fill('ver pliegos');
    await page.getByRole('button', {name: 'Sugerir códigos'}).click();
    await expect(page.getByText('No sé: falta información para sugerir un código')).toBeVisible();
  });

  test('las páginas legales y de datos están enlazadas desde el pie', async ({page}) => {
    await page.goto('/');
    const footer = page.getByRole('contentinfo');
    await expect(footer).toContainText('CC BY 3.0 Ecuador');
    for (const [link, heading] of [
      ['Aviso legal', 'Aviso legal'],
      ['Privacidad', 'Política de privacidad'],
      ['Cookies', 'Política de cookies'],
    ] as const) {
      await footer.getByRole('link', {name: link, exact: true}).click();
      await expect(page.getByRole('heading', {level: 1, name: heading})).toBeVisible();
    }
    await page.goto('/modelo');
    await expect(page.getByRole('heading', {level: 1, name: 'Ficha del modelo'})).toBeVisible();
    await expect(page.getByText('Código de 9 dígitos, primera opción')).toBeVisible();
  });

  test('no hay desplazamiento horizontal y el foco es visible', async ({page}) => {
    await page.goto('/');
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);
    await page.keyboard.press('Tab');
    await expect(page.getByRole('link', {name: 'Saltar al contenido'})).toBeFocused();
  });
});
