import path from 'path'
import adapter from '@sveltejs/adapter-static'
import { enhancedImages } from '@sveltejs/enhanced-img'
import { sveltekit } from '@sveltejs/kit/vite'
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte'
import tailwindcss from '@tailwindcss/vite'
import { SvelteKitPWA } from '@vite-pwa/sveltekit'
import { config as dotEnvConfig } from 'dotenv'
import Icons from 'unplugin-icons/vite'
import { defineConfig } from 'vite'

// have to configure dotenv to load correct .env file
dotEnvConfig({ path: `.env.${process.env.NODE_ENV}` })

// only proxy API in development; in production it is proxied by Caddy
const proxyAPI = !!process.env.VITE_PROXY_API

// only serve PMTiles through vite in local development; they are served
// by Caddy in production.
// NOTE: we dynamically import the plugin to ensure it is not available in production
const servePMTiles = !!process.env.VITE_TILE_DIR
let pmtilesServer = () => undefined
if (servePMTiles) {
	pmtilesServer = (
		await import(path.resolve(import.meta.dirname, './src/plugins/pmtilesServer.ts'))
	).default
}

export default defineConfig({
	build: {
		rolldownOptions: {
			output: {
				codeSplitting: {
					groups: [
						{ test: (id) => id.includes('mapbox-gl') || id.includes('deck.gl'), name: 'map-vendor' }
					]
				}
			}
		}
	},
	resolve: {
		alias: {
			$constants: path.resolve(import.meta.dirname, '../constants')
		}
	},
	server: {
		fs: {
			allow: servePMTiles ? [path.resolve(process.env.VITE_TILE_DIR as string)] : undefined
		},
		proxy: proxyAPI
			? {
					// proxy API endpoint to FastAPI
					'/api': {
						target: 'http://localhost:5000',
						changeOrigin: true
					}
				}
			: undefined
	},
	plugins: [
		SvelteKitPWA({
			manifest: {
				name: 'Midwest Conservation Blueprint Explorer',
				short_name: 'Midwest Blueprint Explorer',
				start_url: process.env.DEPLOY_PATH || '/',
				scope: process.env.DEPLOY_PATH || '/',
				background_color: '#007ac2',
				theme_color: '#007ac2',
				display: 'minimal-ui',
				icons: [
					{
						src: 'favicon-16x16.png',
						sizes: '16x16',
						type: 'image/png'
					},
					{
						src: 'favicon-32x32.png',
						sizes: '32x32',
						type: 'image/png'
					},
					{
						src: 'favicon-64x64.png',
						sizes: '64x64',
						type: 'image/png'
					},
					{
						src: 'favicon-192x192.png',
						sizes: '192x192',
						type: 'image/png'
					},
					{
						src: 'favicon-512x512.png',
						sizes: '512x512',
						type: 'image/png'
					},
					{
						src: 'favicon-64x64.svg',
						sizes: '64x64',
						type: 'image/svg'
					}
				]
			},
			// create empty self-destroying service worker; can't seem to disable it
			// this still creates registerSW.js and sw.js files in output, but
			// we don't include them in app.html, so they shouldn't be used
			selfDestroying: true,
			strategies: 'injectManifest',
			injectManifest: {
				injectionPoint: undefined
			}
		}),
		tailwindcss(),
		enhancedImages(),
		sveltekit({
			preprocess: vitePreprocess(),

			adapter: adapter({
				pages: 'public',
				assets: 'public',
				fallback: '404.html',
				precompress: false,
				strict: true
			}),
			paths: {
				// @ts-expect-error DEPLOY_PATH is valid
				base: process.env.DEPLOY_PATH || ''
			}
		}),
		Icons({ compiler: 'svelte' }),
		// middleware to serve PMTtiles in development mode
		servePMTiles ? pmtilesServer() : undefined
	]
})
