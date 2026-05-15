<script lang="ts">
	import { getContext } from 'svelte'

	import { logGAEvent } from '$lib/util/log'
	import ModeTooltip from './ModeTooltip.svelte'
	import { cn } from '$lib/utils'
	import type { MapData } from '$lib/components/map'

	let { belowMinZoom } = $props()
	const mapData: MapData = getContext('map-data')

	const handleFilterClick = () => {
		mapData.mapMode = 'filter'
		logGAEvent('set-map-mode', { mode: 'filter' })
	}

	const handlePixelClick = () => {
		mapData.mapMode = 'pixel'
		logGAEvent('set-map-mode', { mode: 'pixel-identify' })
	}

	const handleUnitClick = () => {
		mapData.mapMode = 'unit'
		logGAEvent('set-map-mode', { mode: 'summary-unit' })
	}

	const inactiveClass = {
		'bg-blue-2': true
	}

	const activeClass = {
		'bg-primary': true,
		'text-white': true
	}
</script>

<div
	class="flex flex-col md:flex-wrap md:flex-row justify-center md:justify-start items-center md:gap-2 absolute text-center pt-3 pb-2 px-4 bg-white text-foreground shadow-md shadow-grey-9/75 z-1 left-0 md:left-[21px] right-0 md:right-auto bottom-0 md:bottom-auto md:top-0 md:rounded-b-xl"
>
	<div class="flex items-center flex-nowrap justify-center md:justify-start gap-0.5">
		<ModeTooltip
			content="Show data summaries and charts for a subwatershed"
			onClick={handleUnitClick}
			class={cn(mapData.mapMode === 'unit' ? activeClass : inactiveClass)}
		>
			Summarize data
		</ModeTooltip>

		<ModeTooltip
			content="Show values at a specific point for the blueprint, indicators, and other contextual information"
			onClick={handlePixelClick}
			class={cn(mapData.mapMode === 'pixel' ? activeClass : inactiveClass)}
		>
			View point data
		</ModeTooltip>

		<ModeTooltip
			content="Find your part of the blueprint by showing only areas that score within a certain range on indicators and more"
			onClick={handleFilterClick}
			class={cn('', mapData.mapMode === 'filter' ? activeClass : inactiveClass)}
		>
			Filter the blueprint
		</ModeTooltip>
	</div>
	<div class="text-xs md:text-sm text-center md:text-left ml-2 leading-none mt-1 md:mt-0">
		{#if (mapData.mapMode === 'unit' || mapData.mapMode === 'pixel') && belowMinZoom}
			<div class="max-w-[7em]">
				Zoom in to select {mapData.mapMode === 'pixel' ? 'a point' : 'an area'}
			</div>
		{:else if mapData.mapMode === 'unit'}
			<div class="max-w-[12em] xl:max-w-[18em]">
				Select a subwatershed to show details
				<span class="hidden md:inline">in sidebar</span>
			</div>
		{:else if mapData.mapMode === 'pixel'}
			<div class="max-w-[12em] xl:max-w-[18em]">
				Pan the map behind the crosshairs to show details
				<span class="hidden md:inline"> in sidebar</span>
			</div>
		{:else if mapData.mapMode === 'filter'}
			<div class="max-w-[12em] xl:max-w-[18em]">
				Select data to filter and adjust the range to update the map
			</div>
		{/if}
	</div>
</div>
