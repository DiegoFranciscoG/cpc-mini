import {defineConfig, loadEnv, type Plugin} from 'vite';
import react from '@vitejs/plugin-react';

const API_TARGET = process.env.CPCMINI_API_URL ?? 'http://127.0.0.1:8000';
const ROUTES = ['/', '/modelo', '/datos', '/aviso-legal', '/privacidad', '/cookies'];

/** sitemap.xml y URL canónica sólo si se define VITE_SITE_URL (no se inventa un dominio). */
function sitemap(siteUrl: string): Plugin {
  return {
    name: 'cpcmini-sitemap',
    generateBundle() {
      if (!siteUrl) return;
      const base = siteUrl.replace(/\/$/, '');
      const urls = ROUTES.map((r) => `  <url><loc>${base}${r}</loc></url>`).join('\n');
      this.emitFile({
        type: 'asset',
        fileName: 'sitemap.xml',
        source: `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`,
      });
    },
    transformIndexHtml(html) {
      if (!siteUrl) return html;
      const base = siteUrl.replace(/\/$/, '');
      return html.replace(
        '</head>',
        `  <link rel="canonical" href="${base}/" />\n    <meta property="og:url" content="${base}/" />\n  </head>`,
      );
    },
  };
}

export default defineConfig(({mode}) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_');
  const proxy = {'/api': {target: API_TARGET, changeOrigin: false}};
  return {
    plugins: [react(), sitemap(env.VITE_SITE_URL ?? '')],
    server: {port: 5173, strictPort: true, proxy},
    preview: {host: '127.0.0.1', port: 4173, strictPort: true, proxy},
    build: {target: 'es2022', sourcemap: false, cssCodeSplit: true},
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: ['./src/test/setup.ts'],
      include: ['src/**/*.test.{ts,tsx}'],
      css: true,
      coverage: {
        provider: 'v8',
        include: ['src/**/*.{ts,tsx}'],
        exclude: ['src/**/*.test.{ts,tsx}', 'src/test/**', 'src/main.tsx', 'src/themes/**', 'src/astryx-themes.*'],
        thresholds: {lines: 70, functions: 70, statements: 70, branches: 60},
      },
    },
  };
});
