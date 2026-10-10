/** @type {import('tailwindcss').Config} */
module.exports = {
  // Use the standard 'class' value so you control dark mode by toggling the `.dark` class.
  darkMode: 'class',
  content: [
    './pages/**/*.{js,jsx,ts,tsx}',
    './components/**/*.{js,jsx,ts,tsx}',
    './app/**/*.{js,jsx,ts,tsx}',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    container: {
      center: true,
      padding: '2rem',
      screens: { '2xl': '1400px' },
    },
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      keyframes: {
        'accordion-down': { from: { height: 0 }, to: { height: 'var(--radix-accordion-content-height)' } },
        'accordion-up': { from: { height: 'var(--radix-accordion-content-height)' }, to: { height: 0 } },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
      },

      // Typography plugin themed with your CSS variables
      typography: ({ theme }) => ({
        DEFAULT: {
          css: {
            color: theme('colors.foreground'),
            a: {
              color: theme('colors.primary.DEFAULT'),
              textDecoration: 'none',
              fontWeight: '600',
              '&:hover': { textDecoration: 'underline' },
            },
            h1: { color: theme('colors.foreground'), fontWeight: '800' },
            h2: { color: theme('colors.foreground'), fontWeight: '800' },
            h3: { color: theme('colors.foreground'), fontWeight: '700' },
            strong: { color: theme('colors.foreground') },
            blockquote: {
              color: theme('colors.foreground'),
              borderLeftColor: theme('colors.border'),
            },
            hr: { borderColor: theme('colors.border') },
            code: {
              color: theme('colors.foreground'),
              backgroundColor: theme('colors.muted.DEFAULT'),
              padding: '0.15rem 0.35rem',
              borderRadius: '0.35rem',
            },
            'code::before': { content: 'none' },
            'code::after': { content: 'none' },
            pre: {
              backgroundColor: theme('colors.card.DEFAULT'),
              color: theme('colors.card.foreground'),
              borderRadius: theme('borderRadius.lg'),
              borderColor: theme('colors.border'),
              borderWidth: '1px',
            },
            img: { borderRadius: theme('borderRadius.lg') },
          },
        },
        invert: {
          css: {
            color: theme('colors.foreground'),
            a: { color: theme('colors.primary.DEFAULT') },
            blockquote: { borderLeftColor: theme('colors.border') },
            hr: { borderColor: theme('colors.border') },
            code: { backgroundColor: theme('colors.muted.DEFAULT') },
            pre: {
              backgroundColor: theme('colors.card.DEFAULT'),
              color: theme('colors.card.foreground'),
              borderColor: theme('colors.border'),
            },
          },
        },
      }),
    },
  },
  safelist: [
    // ensure these classes are not purged when used in JSX strings
    'prose',
    'prose-lg',
    'dark:prose-invert',
  ],
  plugins: [
    require('@tailwindcss/typography'),
    require('tailwindcss-animate'),
  ],
};
