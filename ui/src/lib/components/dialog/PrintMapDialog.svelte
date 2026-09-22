<script lang="ts">
	import Spinner from '~icons/fa-solid/spinner'
	import { getContext } from 'svelte'
	import { browser } from '$app/environment'
	import PrintIcon from '~icons/fa-solid/file-import'
	import { Root, Trigger, Content, Header, Title, Footer, Close } from '$lib/components/ui/dialog'
	import { Button } from '$lib/components/ui/button'
	import type { AppState } from '$lib/types'
	import type { MapState } from '$lib/components/map'

	const appState: AppState = getContext('app-state')
	const mapState: MapState = getContext('map-state')

	let open = $state(false)
	let isLoading = $state(false)

	const handlePrint = () => {
		if (browser) {
			window.print()
		}
		open = false
	}

	$effect(() => {
		if (open) {
			isLoading = true
			appState.isPrint = true
			mapState.renderMapImage()
		} else {
			appState.isPrint = false
		}
	})

	$effect(() => {
		if (mapState.mapImg !== null) {
			isLoading = false
		}
	})
</script>

{#if !appState.isMobile}
	<Root bind:open>
		<Trigger>
			{#snippet child({ props })}
				<Button {...props} variant="ghost" class="hover:bg-transparent h-auto p-1!">
					<PrintIcon />
					<b>Print / save map to PDF</b>
				</Button>
			{/snippet}
		</Trigger>

		<Content class="pt-4 pb-6 print:hidden">
			<Header class="border-b pb-2 mb-2 border-b-grey-2">
				<Title class="text-3xl">Print map / save to PDF</Title>
			</Header>
			{#if isLoading}
				<p class="text-lg text-center">Saving map image...</p>
			{:else}
				<p class="text-lg">
					This will use your browser's print interface to save a screenshot of your map and any
					enabled filters.
					<br /><br />
					In your browser's print dialog, you can choose to save this to PDF instead of printing it.
				</p>
			{/if}
			<Footer class="border-t border-t-grey-2 mt-2 pt-2">
				<Close class="text-lg cursor-pointer">Cancel</Close>
				<Button onclick={handlePrint} disabled={isLoading} class="text-lg">
					{#if isLoading}
						<Spinner class="size-4 animate-spin" />
					{:else}
						<PrintIcon class="size-4" />
					{/if}

					Print / Save map to PDF
				</Button>
			</Footer>
		</Content>
	</Root>
{/if}
