import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    rules: {
      // Setting loading flags + clearing stale data inside data-fetch effects is
      // standard React practice. The rule is overly aggressive for our patterns
      // (it flags unconditional `setLoading(true)` at the top of an effect).
      // Re-enable later if we adopt useSyncExternalStore / a data-fetch lib.
      'react-hooks/set-state-in-effect': 'off',
      // TanStack Table's `useReactTable` returns objects whose internals the
      // compiler can't memoize — that's by library design, not a real concern.
      'react-hooks/incompatible-library': 'off',
    },
  },
])
