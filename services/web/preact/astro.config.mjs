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
      },
      tsconfigPaths: true,
    },
  },
});
