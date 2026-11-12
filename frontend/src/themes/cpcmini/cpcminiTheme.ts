/**
 * Tema Astryx de CPC-mini: extiende el tema neutral con la paleta Furrow
 * (papel manila, tinta casi negra, una señal mandarina con tinta encima).
 * Fuente de autoría para `astryx theme build`; la app importa el tema compilado.
 */
import {defineTheme} from '@astryxdesign/core/theme';
import {neutralTheme} from '@astryxdesign/theme-neutral/built';

const ink = '#14110f';
const accent = '#fc6b33';
const paper = '#f5f1ea';
const sheet = '#fffdfa';

export const cpcminiTheme = defineTheme({
  name: 'cpcmini',
  extends: neutralTheme,
  color: {accent: [accent, accent], neutralStyle: 'warm', contrast: 'standard'},
  typography: {
    scale: {base: 16, ratio: 1.2},
    body: {family: 'Red Hat Text', fallbacks: 'ui-sans-serif, system-ui, sans-serif'},
    heading: {family: 'Red Hat Display', fallbacks: 'Red Hat Text, ui-sans-serif, sans-serif'},
    code: {family: 'Red Hat Mono', fallbacks: 'ui-monospace, monospace'},
  },
  radius: {base: 6, multiplier: 1},
  tokens: {
    '--color-accent': [accent, accent],
    '--color-on-accent': [ink, ink],
    '--color-text-accent': [ink, ink],
    '--color-text-primary': [ink, ink],
    '--color-text-secondary': ['#58514c', '#58514c'],
    '--color-background-body': [paper, paper],
    '--color-background-surface': [sheet, sheet],
    '--color-background-card': [sheet, sheet],
    '--color-border': ['#cfc9bd', '#cfc9bd'],
  },
});
