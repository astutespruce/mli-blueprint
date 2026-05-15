<script lang="ts">
	import CheckIcon from '~icons/fa-solid/check'
	import { blueprint as blueprintCategories } from '$lib/config/constants'
	import { PieChart } from '$lib/components/chart'
	import { cn } from '$lib/utils'
	import { NeedHelp } from './general'

	type Props = {
		type: string
		blueprint: number[] | number | null
		outsideExtentPercent: number
		class: string | undefined
	}

	const { type, blueprint, outsideExtentPercent, class: className = '' }: Props = $props()

	type Category = {
		value: number
		label: string
		color: string
	}

	const blueprintPixelValue = $derived(type === 'pixel' ? blueprint : null)
	const blueprintChartData = $derived.by(() => {
		if (type === 'pixel') {
			return null
		}

		if (blueprint === null) {
			return []
		}

		const blueprintPercents = (blueprint as number[]).slice().reverse()
		const data: Category[] = blueprintCategories
			.map(({ color, label, shortLabel, ...rest }, i) => ({
				...rest,
				// add transparency to match map
				color: `${color}bf`,
				value: blueprintPercents[i],
				label: shortLabel || label
			}))
			.filter(({ value }) => value > 0)

		if (outsideExtentPercent) {
			data.push({
				value: outsideExtentPercent,
				color: '#fde0dd',
				label: 'Outside Midwest Blueprint'
			})
		}
		return data
	})
</script>

<section class={cn('flex-auto overflow-y-auto h-full p-4', className)}>
	<h3 class="text-2xl">Midwest Blueprint 2026 Priority</h3>
	<div class="text-grey-9">for the wellbeing of people and nature</div>
	{#if type !== 'pixel'}
		<PieChart categories={blueprintChartData} class="mt-6 mb-4" />
	{/if}

	{#if outsideExtentPercent < 100}
		<div class="mt-2">
			{#each blueprintCategories as { value, label, percent, color, description } (value)}
				<div
					class={cn(
						'flex justify-between items-start gap-2 text-grey-8 border border-transparent py-2 px-4 rounded-[0.5rem] bg-white not-first:mt-2',
						{
							'border-grey-2 shadow-md text-foregrund': value === blueprintPixelValue
						}
					)}
				>
					<div
						class="border border-grey-2 w-4 h-8 rounded-[0.25em] flex-none"
						style={`background-color:${color}bf;`}
					></div>
					<div class="flex-auto">
						<div class="font-bold">{label}</div>
						<div class="text-sm leading-snug">
							{description} This class covers {percent}% of the Midwest Blueprint geography.
						</div>
					</div>
					{#if value === blueprintPixelValue}
						<CheckIcon class="flex-none size-4" />
					{/if}
				</div>
			{/each}
		</div>
	{/if}

	<div class="text-grey-9 text-sm mt-8 pt-8 border-t border-t-grey-2">
		Subwatershed boundary is based on the
		<a href="https://www.usgs.gov/national-hydrography/watershed-boundary-dataset" target="_blank">
			National Watershed Boundary Dataset
		</a>
		(2025), U.S. Geological Survey.
	</div>

	<NeedHelp />
</section>
