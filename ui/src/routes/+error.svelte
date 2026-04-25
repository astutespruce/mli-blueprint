<script>
	import { browser } from '$app/environment'
	import { page } from '$app/state'
	import { CONTACT_EMAIL } from '$lib/env'
	import { Footer, Header } from '$lib/components/layout'

	console.error(page.status)
	console.error(page.error)

	if (page.status !== 404 && browser && window.Sentry) {
		window.Sentry.captureException(page.error)
	}
</script>

<svelte:head>
	<title>{page.status} | Midwest Conservation Blueprint Explorer</title>
</svelte:head>

<Header />
<main class="h-full w-full flex-auto overflow-auto">
	{#if page.status === 404}
		<div class="relative flex-auto h-full">
			<div class="hidden md:block absolute top-0 bottom-0 left-0 right-0 overflow-hidden">
				<enhanced:img src="$images/48754428566_d34b348ac3_o.jpg" alt="" class="brightness-80" />
				<div class="sticky bottom-0">
					<div class="absolute bottom-0 right-0 bg-black/65 text-white px-2 text-sm">
						Photo:
						<a
							href="https://flickr.com/photos/usfwssoutheast/48754428566/"
							target="_blank"
							class="text-white"
						>
							G. Peeples / U.S. Fish and Wildlife Service Southeast Region</a
						>
					</div>
				</div>
			</div>
			<div class="relative mx-auto max-w-200 p-4 bg-white top-10">
				<h1 class="text-5xl">PAGE NOT FOUND</h1>
				<h2 class="text-3xl">Sorry, we could not find what you were looking for here.</h2>
			</div>
		</div>
	{:else}
		<div class="mx-auto max-w-[800px] p-4 my-20">
			<h1 class="text-5xl">Uh oh!</h1>
			<h2 class="text-3xl">There was an unexpected error</h2>
			<div class="mt-4 text-xl">
				Please try again in a few minutes. If that still doesn't work, please
				<a href={`mailto:${CONTACT_EMAIL}`}> let us know</a>!
			</div>
		</div>
	{/if}
</main>
<Footer />
