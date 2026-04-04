import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    include: ['**/*.{test,spec}.?(c|m)[jt]s?(x)'],
  },
});
