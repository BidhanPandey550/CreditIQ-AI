import type { Config } from "tailwindcss";

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#1e6b52",
          light: "#2f9c78",
          dark: "#144d3a",
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
