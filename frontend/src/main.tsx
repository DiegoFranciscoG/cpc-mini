import '@fontsource/red-hat-display/latin-600.css';
import '@fontsource/red-hat-text/latin-400.css';
import '@fontsource/red-hat-text/latin-500.css';
import '@fontsource/red-hat-mono/latin-400.css';
import '@fontsource/red-hat-mono/latin-500.css';
import '@astryxdesign/core/reset.css';
import '@astryxdesign/core/astryx.css';
import './styles/app.css';
import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import {InternationalizationProvider} from '@astryxdesign/core/i18n';
import spanish from '@astryxdesign/core/locales/es-ES.generated.js';
import {Theme} from '@astryxdesign/core/theme';
import {themes, defaultThemeSlug} from './astryx-themes';
import {App} from './App';

const root = document.getElementById('root');
if (root) {
  createRoot(root).render(
    <StrictMode>
      <InternationalizationProvider locale="es-EC" messages={{'es-EC': spanish}}>
        <Theme theme={themes[defaultThemeSlug]} mode="light">
          <App />
        </Theme>
      </InternationalizationProvider>
    </StrictMode>,
  );
}
