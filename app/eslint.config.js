import eslintPluginSvelte from 'eslint-plugin-svelte'
import { defineConfig } from "eslint/config"
import js from "@eslint/js"
import globals from "globals"


export default defineConfig([
  {
    ignores: ["dist/"],
  },
  ...eslintPluginSvelte.configs['flat/recommended'],
  { files: ["**/*.{js,mjs,cjs}"], plugins: { js }, extends: ["js/recommended"] },
  { files: ["**/*.{js,mjs,cjs}"], languageOptions: { globals: globals.browser } },
  {
    rules: {
      'no-self-assign': 'off',
      'semi': ['error', 'never'],
      'indent': ['error', 2],
      'svelte/require-each-key': 'off',
      'svelte/no-dom-manipulating': 'off',
      'no-unused-vars': ['error', {
        'args': 'none',
        'caughtErrors': 'none'
      }],
    },
  }
])