<script lang="ts">
	import { getContext } from 'svelte'

	import HumanWellbeingIcon from '$images/h.svg'
	import LandscapeHealthIcon from '$images/l.svg'
	import WildlifeIcon from '$images/w.svg'
	import { cn } from '$lib/utils'
	import type { MapState } from '$lib/components/map'
	import { IndicatorGroup, IndicatorDetails } from './indicators'

	const indicatorGroupIcons = {
		h: HumanWellbeingIcon,
		l: LandscapeHealthIcon,
		w: WildlifeIcon
	}

	const {
		type,
		indicators,
		outside_extent_percent,
		rasterized_acres,
		class: className = ''
	} = $props()

	const mapState: MapState = getContext('map-state')
</script>

<section class={cn('flex-auto overflow-y-auto h-full', className)}>
	{#if mapState.selectedIndicator && !!indicators.indicators[mapState.selectedIndicator]}
		<IndicatorDetails
			{type}
			{...indicators.indicators[mapState.selectedIndicator]}
			{outside_extent_percent}
			{rasterized_acres}
			icon={indicatorGroupIcons[
				indicators.indicators[mapState.selectedIndicator].group
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
