import js from '@eslint/js'
import { includeIgnoreFile,defineConfig } from 'eslint/config'
import svelte from 'eslint-plugin-svelte'
import globals from 'globals'
import { fileURLToPath } from 'node:url'
import ts from 'typescript-eslint'
import oxlint from 'eslint-plugin-oxlint'
import svelteConfig from './svelte.config.js'

const gitignorePath = fileURLToPath(new URL('./.gitignore', import.meta.url))

export default defineConfig(
	includeIgnoreFile(gitignorePath),
	js.configs.recommended,
	...ts.configs.recommended,
	...svelte.configs.recommended,
	{ ignores: ['**/*.ts', '**/*.js'] },
	{
		languageOptions: {
			globals: { ...globals.browser, ...globals.node }
		},
		rules: {
			'no-undef': 'off',
			// does not detect assignment correctly
			'no-useless-assignment': 'off',
			'@typescript-eslint/no-unused-vars': ['error', { varsIgnorePattern: '^_' }]
		}
	},
	{
		files: ['**/*.svelte'],
		languageOptions: {
			parserOptions: {
				projectService: true,
				extraFileExtensions: ['.svelte'],
				parser: ts.parser,
				svelteConfig
			}
		}
	},
	// turn off rules already handled by oxlint
	oxlint.configs['flat/recommended']
)
