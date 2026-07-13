import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1f2933",
        paper: "#f7f8f6",
        line: "#d9ded7",
        sea: "#0f766e",
        amber: "#92400e",
        danger: "#b91c1c"
      },
      boxShadow: {
        panel: "0 1px 2px rgba(31,41,51,0.08)"
      }
    }
  },
  plugins: []
};

export default config;
