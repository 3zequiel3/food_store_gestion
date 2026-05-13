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
      /**
       * D8: Prohibir namespace imports de lucide-react.
       * `import * as Icons from 'lucide-react'` bloatea el bundle (~1500 íconos).
       * Usar named imports: `import { Home, ShoppingCart } from 'lucide-react'`.
       */
      'no-restricted-imports': [
        'error',
        {
          paths: [
            {
              name: 'lucide-react',
              importNames: ['*'],
              message:
                'Prohibido namespace import de lucide-react. Usá named imports: import { Home } from "lucide-react".',
            },
          ],
          patterns: [
            {
              group: ['lucide-react'],
              importNamePattern: '^\\*$',
              message:
                'Prohibido namespace import de lucide-react. Usá named imports: import { Home } from "lucide-react".',
            },
          ],
        },
      ],
    },
  },
])
