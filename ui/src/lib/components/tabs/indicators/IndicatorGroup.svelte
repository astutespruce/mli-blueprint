<script lang="ts">
	import type { Indicator } from '$lib/types'
	import IndicatorListItem from './IndicatorListItem.svelte'
	import PixelIndicatorListItem from './PixelIndicatorListItem.svelte'

	type PropType = {
		type: string
		label: string
		icon: string
		color: string
		borderColor: string
		indicators: Indicator[]
		onSelectIndicator: Function
	}

	const { type, label, icon, color, borderColor, indicators, onSelectIndicator }: PropType =
		$props()
</script>

<div class="w-full grow shrink-0">
	<div
		class="flex items-center justify-between px-4 py-2 border-b border-t"
		style={`background-color: ${color}; border-color: ${borderColor}`}
	>
		<div class="flex items-center gap-2">
			<img
				src={icon}
				alt={`${label} icon`}
				class="flex-none w-8 h-8 bg-white rounded-full border-[1.5px] border-grey-8 p-px"
			/>
			<h3 class="flex-auto text-xl">{label} indicators</h3>
		</div>
	</div>

	<div>
		{#if type === 'pixel'}
			{#each indicators as indicator (indicator.id)}
				<PixelIndicatorListItem {indicator} onSelect={onSelectIndicator} />
			{/each}
		{:else}
			{#each indicators as indicator (indicator.id)}
				<IndicatorListItem {indicator} />
			{/each}
		{/if}
	</div>
</div>
