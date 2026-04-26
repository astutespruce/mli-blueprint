<script lang="ts">
	import sourceSansPro from '@fontsource/montserrat/files/montserrat-latin-400-normal.woff2?url'
	import sourceSansProBold from '@fontsource/montserrat/files/montserrat-latin-900-normal.woff2?url'

	import { browser } from '$app/environment'
	import { GOOGLE_ANALYTICS_ID } from '$lib/env'

	import '../app.css'

	let { children } = $props()

	const handleGTAGLoad = () => {
		if (!window.dataLayer) {
			console.warn('GTAG not properly initialized')
			return
		}

		console.debug('setting up GTAG')

		function gtag() {
			dataLayer.push(arguments)
		}

		gtag('js', new Date())
		gtag('config', GOOGLE_ANALYTICS_ID)
		window.gtag = gtag
	}
</script>

<svelte:head>
	<link rel="preload" as="font" type="font/woff2" href={sourceSansPro} crossorigin="anonymous" />
	<link
		rel="preload"
		as="font"
		type="font/woff2"
		href={sourceSansProBold}
		crossorigin="anonymous"
	/>
	{#if browser && GOOGLE_ANALYTICS_ID}
		<script
			async
			src={`https://www.googletagmanager.com/gtag/js?id=${GOOGLE_ANALYTICS_ID}`}
			onload={handleGTAGLoad}
		></script>
	{/if}
</svelte:head>

<div class="flex flex-col h-full w-full overflow-none">
	{@render children()}
</div>
