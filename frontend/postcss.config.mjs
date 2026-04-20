// frontend/postcss.config.mjs
const config = {
  plugins: {
    '@tailwindcss/postcss': {}, // <--- The new v4 package name
    autoprefixer: {},
  },
};
export default config;