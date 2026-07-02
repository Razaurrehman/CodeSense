export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      keyframes: {
        'slide-in-right': {
          from: { transform: 'translateX(100%)' },
          to:   { transform: 'translateX(0)' },
        },
      },
      animation: {
        'slide-in-right': 'slide-in-right 0.22s ease-out',
      },
    },
  },
  plugins: [],
}
