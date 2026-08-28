<script lang="ts">
	import { getContext, onMount } from 'svelte'

	import { browser } from '$app/environment'
	import type { MapState } from '$lib/components/map'
	import { LegendElement } from '$lib/components/map/legend'
	import FiltersList from './FiltersList.svelte'
	import { BLUEPRINT_VERSION } from '$lib/env'

	const mapState: MapState = getContext('map-state')
	const { label: title, valueLabel: subtitle, categories } = $derived(mapState.displayLayer)

	let url: string | undefined = $state()

	onMount(() => {
		url = mapState.serializeFilterStateToURL()
	})
</script>

{#if browser}
	<div class="hidden print:block">
		<h1 class="text-2xl">Southeast Conservation Blueprint Explorer (2026)</h1>

		{#if mapState.mapImg !== null}
			<div class="mt-4">
				<img
					src={mapState.mapImg}
					class="block max-h-180 max-w-190 border border-grey-8/50 flex-none m-px"
					alt="map"
				/>

				<div class="text-muted-foreground text-xs [&_a]:text-muted-foreground">
					Basemap credits: © <a href="https://www.mapbox.com/about/maps/">Mapbox</a> ©
					<a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>
					<a href="https://www.mapbox.com/map-feedback/" target="_blank">Improve this basemap</a>
				</div>

				<!-- legend -->
				<div class="break-inside-avoid flex-auto mt-4">
					<div class="flex-auto font-bold leading-none text-lg">
						{title}
					</div>

					{#if subtitle}
						<div class="font-normal text-grey-8 leading-none text-[15px] mt-1 mb-3">
							{subtitle}
						</div>
					{/if}

					<div class="mt-2">
						{#each categories as element (element.label)}
							<LegendElement {...element} />
						{/each}
					</div>
				</div>
			</div>
		{/if}

		{#if mapState.mapMode === 'filter'}
			{#if mapState.numEnabledFilters > 0}
				<FiltersList />

				<p class="mt-12">
					<b>To reopen this map with these filters enabled in your browser, go to:</b>
					<br />
					<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -->
					<a href={url} class="text-xs leading-none break-all">{url}</a>

					<br />
					<span class="text-sm text-muted-foreground">
						Note: these filters are only valid for Midwest Blueprint {BLUEPRINT_VERSION}.
					</span>
				</p>
			{:else}
				<p class="mt-12">
					<b>To reopen this map in your browser, go to:</b>
					<br />
					<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -->
					<a href={url} class="text-xs leading-none break-all">{url}</a>
				</p>
			{/if}
		{/if}
	</div>
{/if}
