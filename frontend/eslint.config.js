import js from "@eslint/js";
import tsPlugin from "@typescript-eslint/eslint-plugin";
import tsParser from "@typescript-eslint/parser";
import reactHooksPlugin from "eslint-plugin-react-hooks";
import reactRefreshPlugin from "eslint-plugin-react-refresh";
import globals from "globals";

export default [
  // Ignore built artefacts and dependencies
  { ignores: ["dist/**", "node_modules/**", "coverage/**"] },

  // Base JS rules
  js.configs.recommended,

  // TypeScript + React sources
  {
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: "latest",
        sourceType: "module",
      },
      globals: {
        ...globals.browser,
        ...globals.es2020,
      },
    },
    plugins: {
      "@typescript-eslint": tsPlugin,
      "react-hooks": reactHooksPlugin,
      "react-refresh": reactRefreshPlugin,
    },
    rules: {
      // TypeScript
      ...tsPlugin.configs.recommended.rules,
      "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
      "@typescript-eslint/no-explicit-any": "warn",

      // React hooks
      ...reactHooksPlugin.configs.recommended.rules,

      // React Refresh (HMR safety) — warnings only so lint doesn't fail on test helpers
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
    },
  },

  // Test files: relax some rules that trip on vi/describe/expect globals
  {
    files: ["src/**/*.test.{ts,tsx}", "src/test/**/*.{ts,tsx}"],
    languageOptions: {
      globals: {
        ...globals.browser,
        describe: "readonly",
        it: "readonly",
        expect: "readonly",
        beforeEach: "readonly",
        afterEach: "readonly",
        vi: "readonly",
      },
    },
    rules: {
      // Test files often import vi from vitest and use type assertions liberally
      "@typescript-eslint/no-explicit-any": "off",
    },
  },
];
