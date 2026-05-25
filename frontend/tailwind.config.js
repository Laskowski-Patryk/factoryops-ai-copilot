/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#111827",
        panel: "#172033",
        steel: "#243043",
        signal: "#42d392",
        warning: "#f6c453",
        danger: "#fb7185"
      }
    }
  },
  plugins: []
};
