// Dev-only Astro config: proxies /api to the mock-api.js server (plain HTTP).
// Use with: ASTRO_CONFIG_FILE=astro.config.dev.mjs npx astro dev
import { defineConfig } from 'astro/config';
import tailwindcss from "@tailwindcss/vite";
import preact from '@astrojs/preact';

export default defineConfig({
  build: {
    assets: '_astro',
  },

  integrations: [preact({ compat: true })],
  output: 'static',

  vite: {
    plugins: [
      tailwindcss()
    ],
    resolve: {
      alias: {
        'react': 'preact-compat',
        'react-dom': 'preact-compat',
        'react/jsx-runtime': 'preact/jsx-runtime',
        'react/jsx-dev-runtime': 'preact/jsx-runtime',
      },
      tsconfigPaths: true,
    },
    server: {
      proxy: {
        '/api/effects': {
          target: 'http://127.0.0.1:8001',
          changeOrigin: true,
        },
        '/api/model': {
          target: 'http://127.0.0.1:8001',
          changeOrigin: true,
        },
      },
    },
  },
});
