<script lang="ts">
	import { getContext } from 'svelte'

	import { logGAEvent } from '$lib/util/log'
	import ModeTooltip from './ModeTooltip.svelte'
	import { cn } from '$lib/utils'
	import type { MapState } from '$lib/components/map'

	let { belowMinZoom } = $props()
	const mapState: MapState = getContext('map-state')

	const handleFilterClick = () => {
		mapState.mapMode = 'filter'
		logGAEvent('set-map-mode', { mode: 'filter' })
	}

	const handlePixelClick = () => {
		mapState.mapMode = 'pixel'
		logGAEvent('set-map-mode', { mode: 'pixel-identify' })
	}

	const handleUnitClick = () => {
		mapState.mapMode = 'unit'
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
			class={cn(mapState.mapMode === 'unit' ? activeClass : inactiveClass)}
		>
			Summarize data
		</ModeTooltip>

		<ModeTooltip
			content="Show values at a specific point for the blueprint, indicators, and other contextual information"
			onClick={handlePixelClick}
			class={cn(mapState.mapMode === 'pixel' ? activeClass : inactiveClass)}
		>
			View point data
		</ModeTooltip>

		<ModeTooltip
			content="Find your part of the blueprint by showing only areas that score within a certain range on indicators and more"
			onClick={handleFilterClick}
			class={cn('', mapState.mapMode === 'filter' ? activeClass : inactiveClass)}
		>
			Filter the blueprint
		</ModeTooltip>
	</div>
	<div class="text-xs md:text-sm text-center md:text-left ml-2 leading-none mt-1 md:mt-0">
		{#if (mapState.mapMode === 'unit' || mapState.mapMode === 'pixel') && belowMinZoom}
			<div class="lg:max-w-[6em]">
				Zoom in to select {mapState.mapMode === 'pixel' ? 'a point' : 'an area'}
			</div>
		{:else if mapState.mapMode === 'unit'}
			<div class="lg:max-w-[16em]">
				Select a subwatershed to show details
				<span class="hidden md:inline">in sidebar</span>
			</div>
		{:else if mapState.mapMode === 'pixel'}
			<div class="lg:max-w-[16em]">
				Pan the map behind the crosshairs to show details
				<span class="hidden md:inline"> in sidebar</span>
			</div>
		{:else if mapState.mapMode === 'filter'}
			<div class="lg:max-w-[18em]">
				Select data to filter and adjust
				<span class="hidden md:inline"><br /></span>
				the range to update the map
			</div>
		{/if}
	</div>
</div>
