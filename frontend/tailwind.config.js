/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'system-ui', 'sans-serif'],
      },
      colors: {
        coral: {
          DEFAULT: '#e8917a',
          light: '#f0a898',
          dark: '#d4785f',
          muted: 'rgba(232,145,122,0.15)',
        },
        surface: {
          DEFAULT: 'rgba(255,255,255,0.03)',
          raised: 'rgba(255,255,255,0.06)',
        },
        'slate-deep': '#0b1121',
      },
    },
  },
  plugins: [],
}
