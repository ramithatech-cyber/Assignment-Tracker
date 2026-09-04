/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter var', 'Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      colors: {
        // Dark red brand ramp. `brand` is kept as the token name so every
        // existing class keeps working -- only the hues moved.
        brand: {
          50: '#fef2f2',
          100: '#fee2e2',
          200: '#fecaca',
          300: '#fca5a5',
          400: '#f87171',
          500: '#dc2626',
          600: '#b91c1c',
          700: '#991b1b',
          800: '#7f1d1d',
          900: '#651414',
          950: '#450a0a',
        },
        ink: '#450a0a',
        muted: '#78716c',
      },
      boxShadow: {
        soft: '0 1px 2px rgba(69,10,10,.04), 0 8px 24px -12px rgba(153,27,27,.16)',
        lift: '0 10px 28px -12px rgba(153,27,27,.45)',
        glow: '0 0 0 1px rgba(185,28,28,.14), 0 8px 30px -8px rgba(127,29,29,.3)',
      },
      backgroundImage: {
        'brand-gradient': 'linear-gradient(135deg,#7f1d1d 0%,#991b1b 45%,#dc2626 100%)',
        'brand-deep': 'linear-gradient(135deg,#450a0a 0%,#7f1d1d 55%,#b91c1c 100%)',
      },
      keyframes: {
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'none' },
        },
        'scale-in': {
          '0%': { opacity: '0', transform: 'scale(.96)' },
          '100%': { opacity: '1', transform: 'none' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-500px 0' },
          '100%': { backgroundPosition: '500px 0' },
        },
        float: {
          '0%,100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-6px)' },
        },
      },
      animation: {
        'fade-up': 'fade-up .45s cubic-bezier(.21,1.02,.73,1) both',
        'scale-in': 'scale-in .35s cubic-bezier(.21,1.02,.73,1) both',
        shimmer: 'shimmer 2s linear infinite',
        float: 'float 4s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
