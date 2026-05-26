/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{astro,html,js,jsx,tsx,ts}'],
  theme: {
    extend: {
      colors: {
        lcd: {
          50: '#fefce8',
          100: '#fef9c3',
          200: '#fef08a',
          300: '#fde047',
          400: '#facc15',
          500: '#eab308',
          600: '#ca8a04',
          700: '#a16207',
          800: '#854d0e',
          900: '#5c2104',
          950: '#211300',
        },
        led: {
          500: '#44e674',
          600: '#32d76a',
        },
      },
      fontFamily: {
        'mono': ['"Orbitron"', 'sans-serif'],
      },
    },
  },
  plugins: [],
}