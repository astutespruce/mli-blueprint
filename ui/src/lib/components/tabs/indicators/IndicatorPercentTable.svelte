<script lang="ts">
	import ArrowUpIcon from '~icons/fa-solid/arrow-up'
	import ArrowDownIcon from '~icons/fa-solid/arrow-down'
	import { cn } from '$lib/utils'

	import IndicatorPercentChart from './IndicatorPercentChart.svelte'
	import { formatPercent } from '$lib/util/format'
	const { values, goodThreshold = null } = $props()
	// remainder values, like area outside SE, are assigned values < 0
	const remainders = $derived(values.filter(({ value }: { value: number }) => value < 0))

	type Value = {
		value: number
		label: string
		percent: number
	}

	// not currently used
	// const { goodPercents, totalGoodPercent, notGoodPercents, totalNotGoodPercent } = $derived.by(
	// 	() => {
	// 		if (goodThreshold === null) {
	// 			return
	// 		}

	// 		const good: Value[] = []
	// 		let goodPercent = 0
	// 		const notGood: Value[] = []
	// 		let notGoodPercent = 0
	// 		values.forEach(({ value, percent, ...rest }: Value) => {
	// 			if (value >= goodThreshold) {
	// 				good.push({ value, percent, ...rest })
	// 				goodPercent += percent
	// 			} else if (value >= 0 && value < goodThreshold) {
	// 				notGood.push({ value, percent, ...rest })
	// 				notGoodPercent += percent
	// 			}
	// 		})

	// 		return {
	// 			goodPercents: good,
	// 			totalGoodPercent: goodPercent,
	// 			notGoodPercents: notGood,
	// 			totalNotGoodPercent: notGoodPercent
	// 		}
	// 	}
	// )
</script>

<div class="my-8">
	{#if goodThreshold === null}
		{#each values.filter(({ value }: { value: number }) => value >= 0) as { label, percent, isHighValue, isLowValue } (label)}
			<div class={cn('flex not-first:mt-4 items-start', { 'items-end': isLowValue })}>
				<div class="flex items-center gap-1 flex-none w-20 font-bold text-sm">
					{#if isHighValue}
						<ArrowUpIcon class="size-4" />
						High:
					{:else if isLowValue}
						<ArrowDownIcon class="size-4" />
						Low:
					{/if}
				</div>
				<IndicatorPercentChart {label} {percent} />
			</div>
		{/each}
		<!-- {:else}
		{#each goodPercents as { label, percent, isHighValue } (label)}
			<div class="flex not-first:mt-4">
				<div class="flex items-center gap-1 flex-none w-20 font-bold text-sm">
					{#if isHighValue}
						<ArrowUpIcon class="size-4" />
						High:
					{/if}
				</div>
				<IndicatorPercentChart {label} {percent} />
			</div>
		{/each}

		<div class="mt-6 text-grey-8 text-sm">
			<div class="flex justify-center items-center gap-1">
				<ArrowUpIcon class="size-4" />
				<div class="w-[14em]">
					{formatPercent(totalGoodPercent)}% in good condition
				</div>
			</div>
			<div class="border-b border-dashed border-b-grey-9/50 h-[1px] my-2"></div>
			<div class="flex justify-center items-center gap-1">
				<ArrowDownIcon class="size-4" />
				<div class="w-[14em]">
					{formatPercent(totalNotGoodPercent)}% not in good condition
				</div>
			</div>
		</div>

		{#each notGoodPercents as { label, percent, isLowValue } (label)}
			<div class="flex not-first:mt-4 items-end">
				<div class="flex items-center gap-1 flex-none w-20 font-bold text-sm">
					{#if isLowValue}
						<ArrowDownIcon class="size-4" />
						Low:
					{/if}
				</div>
				<IndicatorPercentChart {label} {percent} />
			</div>
		{/each} -->
	{/if}

	{#if remainders.length > 0}
		<hr class="mb-6" />
		{#each remainders as { label, percent } (label)}
			<div class="flex mt-4">
				<div class="flex-none w-20 font-bold text-sm"></div>
				<IndicatorPercentChart {label} {percent} />
			</div>
		{/each}
	{/if}
</div>
