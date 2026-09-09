/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        accent: "#615c50",
        "accent-hover": "#756f62",
        "accent-soft": "#b8b0a0",
        "accent-focus": "#9d9586",
      },
    },
  },
  plugins: [],
}

