/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Identidad visual Yakuni: paleta agua / petróleo
        agua: {
          50: '#ecfeff', 100: '#cffafe', 200: '#a5f3fc', 400: '#22d3ee',
          500: '#06b6d4', 600: '#0891b2', 700: '#0e7490', 800: '#155e75', 900: '#164e63',
        },
        // Colores semafóricos accesibles (contraste AA)
        verde: '#15803d',
        amarillo: '#b45309',
        rojo: '#b91c1c',
      },
      fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'] },
    },
  },
  plugins: [],
}
