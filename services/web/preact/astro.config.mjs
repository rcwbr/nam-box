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
        // React Flow (@xyflow/react) compiles to JSX that imports from
        // react/jsx-runtime; the bare 'react' alias above does NOT cover
        // subpath imports, so alias the JSX runtime explicitly to Preact.
        'react/jsx-runtime': 'preact/jsx-runtime',
        'react/jsx-dev-runtime': 'preact/jsx-runtime',
      },
      tsconfigPaths: true,
    },
    // Proxy /api/effects and /api/model to the backend via Traefik (dev mode).
    // In production, Traefik handles this routing. In dev, the Astro dev server
    // runs standalone without Traefik, so we proxy here to the real backend.
    server: {
      proxy: {
        '/api/effects': {
          target: 'https://localhost',
          changeOrigin: true,
          secure: false,
        },
        '/api/model': {
          target: 'https://localhost',
          changeOrigin: true,
          secure: false,
        },
      },
    },
  },
});
