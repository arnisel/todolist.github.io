module.exports = {
  content: [
    './templates/**/*.html',
    './**/*.py'
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: '#D4AF37',
        // Core palette used across templates (aliases provided for legacy class names)
        'background-light': '#FFFFFF',
        'background-dark': '#1A1A1A',
        'text-light': '#1A1A1A',
        'text-dark': '#FFFFFF',
        'card-light': '#F5F5F5',
        'card-dark': '#2C2C2C',
        'border-light': '#E0E0E0',
        'border-dark': '#424242',
        'text-muted-light': '#6B7280',
        'text-muted-dark': '#9CA3AF',
        // Common aliases used in templates (keeps older classnames working)
        'subtle-light': '#F5F5F5',
        'subtle-dark': '#2C2C2C',
        'text-text-muted-light': '#6B7280',
        'text-text-muted-dark': '#9CA3AF',
        'text-text-subtle-light': '#6B7280',
        'text-text-subtle-dark': '#9CA3AF',
        'text-text-light': '#1A1A1A',
        'text-text-dark': '#FFFFFF'
      },
      fontFamily: { display: ['Inter', 'sans-serif'] }
    }
  },
  plugins: []
};
