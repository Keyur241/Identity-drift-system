export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: { extend: {
    colors: { void: '#07070b', midnight: '#0b0c16', panel: '#101126', ice: '#e5e8f4', violet: '#6366f1', periwinkle: '#7075ff', cyber: '#22c55e', amber: '#eab308' },
    fontFamily: { sans: ['Inter', 'SF Pro Display', '-apple-system', 'Segoe UI', 'sans-serif'], mono: ['"DM Mono"', 'SFMono-Regular', 'Consolas', 'monospace'] },
    transitionTimingFunction: { cs: 'cubic-bezier(.22,1,.36,1)' }
  } },
  plugins: []
};
