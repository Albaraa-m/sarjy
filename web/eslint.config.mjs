import sarj from "@sarj/eslint-plugin";
import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const SARJ_RULES = [
  "no-raw-env",
  "no-server-env-in-client-component",
  "prefer-schema-for-api-payload",
  "no-unnecessary-use-client",
  "no-enum",
  "require-assert-never",
  "no-insecure-random-id",
  "no-credential-in-browser-storage",
  "no-silent-promise-catch",
  "no-log-only-catch",
  "no-client-side-data-fetching",
  "require-button-accessible-name",
  "prefer-module-level-constant",
  "prefer-immutable-module-constant",
  "sole-export-matches-filename",
  "no-restated-comment",
  "no-comment-cruft",
  "excessive-commentary",
  "no-trailing-value-narration",
];

export default defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    files: ["app/**/*.{ts,tsx}", "components/**/*.{ts,tsx}", "lib/**/*.ts"],
    plugins: { sarj },
    languageOptions: {
      parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname },
    },
    rules: Object.fromEntries(SARJ_RULES.map((rule) => [`sarj/${rule}`, "error"])),
  },
  // Vendored LiveKit Agents UI components (installed with `shadcn add`), kept as upstream wrote them.
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    "components/agents-ui/**",
    "hooks/agents-ui/**",
  ]),
]);
