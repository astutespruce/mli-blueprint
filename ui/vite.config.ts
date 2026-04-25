import { sveltekit } from '@sveltejs/kit/vite'
import { defineConfig } from 'vite'
import { enhancedImages } from '@sveltejs/enhanced-img'
import Icons from 'unplugin-icons/vite'
import tailwindcss from '@tailwindcss/vite'
import { config as dotEnvConfig } from 'dotenv'
import { VitePWA } from 'vite-plugin-pwa'

// have to configure dotenv to load correct .env file
dotEnvConfig({ path: `.env.${process.env.NODE_ENV}` })

export default defineConfig({
	build: {
		rollupOptions: {
			output: {
				// split mapbox & deck.gl into their own chunk; they are huge
				manualChunks: function (id) {
					if (id.includes('mapbox-gl') || id.includes('deck.gl')) {
						return 'map-vendor'
					}
				}
			}
		}
	},
	plugins: [
		VitePWA({
			manifest: {
				name: 'Midwest Conservation Blueprint Explorer',
				short_name: 'Midwest Blueprint Explorer',
				start_url: process.env.DEPLOY_PATH || '/',
				scope: process.env.DEPLOY_PATH || '/',
				background_color: '#21496b',
				theme_color: '#21496b',
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
		sveltekit(),
		Icons({ compiler: 'svelte' })
	]
})
