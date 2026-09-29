import { defineConfig, presetIcons, presetUno, transformerDirectives } from 'unocss'

export default defineConfig({
  presets: [
    presetUno(),
    presetIcons({
      scale: 1.2,
      warn: true,
    }),
  ],
  transformers: [transformerDirectives()],
  theme: {
    colors: {
      primary: {
        DEFAULT: '#0f766e',
        50: '#f0fdfa',
        100: '#ccfbf1',
        200: '#99f6e4',
        300: '#5eead4',
        400: '#2dd4bf',
        500: '#14b8a6',
        600: '#0d9488',
        700: '#0f766e',
        800: '#115e59',
        900: '#134e4a',
      },
    },
    fontFamily: {
      sans: 'system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans Arabic", sans-serif',
    },
  },
  shortcuts: {
    'btn': 'inline-flex items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer',
    'btn-primary': 'btn bg-primary-700 text-white hover:bg-primary-800',
    'btn-secondary': 'btn bg-gray-100 text-gray-700 hover:bg-gray-200',
    'btn-danger': 'btn bg-red-600 text-white hover:bg-red-700',
    'input': 'w-full rounded-md border border-gray-300 bg-white px-2.5 py-1.5 text-sm outline-none focus:border-primary-600 focus:ring-1 focus:ring-primary-600',
    'label': 'block text-xs font-medium text-gray-600 mb-1',
    'card': 'rounded-lg border border-gray-200 bg-white shadow-sm',
    'badge': 'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
    'th': 'px-3 py-2 text-start text-xs font-semibold text-gray-500 uppercase tracking-wide',
    'td': 'px-3 py-2 text-sm text-gray-700',
  },
})
