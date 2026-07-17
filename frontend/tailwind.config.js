/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4ff",
          100: "#dbe6ff",
          500: "#3563e9",
          600: "#2a4ec9",
          700: "#213c9c",
        },
      },
    },
  },
  plugins: [],
};
