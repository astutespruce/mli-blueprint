<script lang="ts">
	import { getContext } from 'svelte'

	import HumanWellbeingIcon from '$images/h.svg'
	import LandscapeHealthIcon from '$images/l.svg'
	import WildlifeIcon from '$images/w.svg'
	import { cn } from '$lib/utils'
	import type { MapData } from '$lib/components/map'
	import { IndicatorGroup, IndicatorDetails } from './indicators'

	const indicatorGroupIcons = {
		h: HumanWellbeingIcon,
		l: LandscapeHealthIcon,
		w: WildlifeIcon
	}

	const {
		type,
		indicators,
		outsideExtentPercent,
		rasterizedAcres,
		class: className = ''
	} = $props()

	const mapData: MapData = getContext('map-data')
</script>

<section class={cn('flex-auto overflow-y-auto h-full', className)}>
	{#if mapData.selectedIndicator && !!indicators.indicators[mapData.selectedIndicator]}
		<IndicatorDetails
			{type}
			{...indicators.indicators[mapData.selectedIndicator]}
			{outsideExtentPercent}
			{rasterizedAcres}
			icon={indicatorGroupIcons[
				indicators.indicators[mapData.selectedIndicator].group
					.id as keyof typeof indicatorGroupIcons
			]}
		/>
	{:else}
		{#each indicators.indicatorGroups as group (group.id)}
			<IndicatorGroup
				{type}
				{...group}
				icon={indicatorGroupIcons[group.id as keyof typeof indicatorGroupIcons]}
			/>
		{/each}
	{/if}
</section>
