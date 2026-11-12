// Capturas del README y la imagen social. Requiere `npm run preview` y la API en marcha.
// Uso: node scripts/screenshots.mjs [http://127.0.0.1:4173]
import {mkdirSync, readFileSync} from 'node:fs';
import {chromium, devices} from '@playwright/test';

const BASE = process.argv[2] ?? 'http://127.0.0.1:4173';
const DOCS = new URL('../../docs/img/', import.meta.url);
const PUBLIC = new URL('../public/', import.meta.url);
mkdirSync(DOCS, {recursive: true});

async function classify(page, text) {
  await page.goto(BASE);
  await page.getByRole('button', {name: 'Entendido'}).click();
  await page.getByRole('textbox', {name: /Descripción del ítem/}).fill(text);
  await page.getByRole('button', {name: 'Sugerir códigos'}).click();
  await page.getByRole('article').waitFor();
}

const browser = await chromium.launch();
try {
  const desktop = await browser.newPage({viewport: {width: 1280, height: 900}, locale: 'es-EC'});
  await classify(desktop, 'Resma de papel bond A4 de 75 g');
  await desktop.screenshot({path: new URL('clasificar.png', DOCS).pathname.replace(/^\/([A-Z]:)/, '$1'), fullPage: false});
  await desktop.goto(`${BASE}/modelo`);
  await desktop.getByRole('table').first().waitFor();
  await desktop.screenshot({path: new URL('ficha-modelo.png', DOCS).pathname.replace(/^\/([A-Z]:)/, '$1'), fullPage: true});

  const social = await browser.newPage({viewport: {width: 1200, height: 630}, locale: 'es-EC'});
  await classify(social, 'Paracetamol 500 mg tabletas, caja x 100');
  await social.screenshot({path: new URL('og.png', PUBLIC).pathname.replace(/^\/([A-Z]:)/, '$1')});

  const phone = await browser.newPage({...devices['Pixel 7'], locale: 'es-EC'});
  await classify(phone, 'Servicio de limpieza de oficinas');
  await phone.getByRole('article').scrollIntoViewIfNeeded();
  await phone.screenshot({path: new URL('movil.png', DOCS).pathname.replace(/^\/([A-Z]:)/, '$1')});

  const icon = await browser.newPage({viewport: {width: 180, height: 180}});
  const svg = readFileSync(new URL('favicon.svg', PUBLIC), 'utf8');
  await icon.setContent(`<body style="margin:0">${svg.replace('<svg ', '<svg width="180" height="180" ')}</body>`);
  await icon.screenshot({path: new URL('apple-touch-icon.png', PUBLIC).pathname.replace(/^\/([A-Z]:)/, '$1'), omitBackground: true});
} finally {
  await browser.close();
}
console.log('capturas listas');
