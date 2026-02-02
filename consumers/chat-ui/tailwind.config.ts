import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        canvas: 'var(--bg-canvas)',
        surface: 'var(--bg-default)',
        subtle: 'var(--bg-subtle)',
        border: 'var(--border-default)',
        'text-primary': 'var(--text-primary)',
        'text-secondary': 'var(--text-secondary)',
        accent: 'var(--accent-emphasis)',
        'accent-fg': 'var(--accent-fg)',
        success: 'var(--success-fg)',
        danger: 'var(--danger-fg)',
      },
    },
  },
  plugins: [],
};

export default config;
