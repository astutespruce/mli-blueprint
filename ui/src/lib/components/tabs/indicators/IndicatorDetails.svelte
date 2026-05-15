<script lang="ts">
	import { getContext } from 'svelte'

	import ReplyIcon from '~icons/fa-solid/reply'
	import { Button } from '$lib/components/ui/button'
	import type { MapData } from '$lib/components/map'
	import { formatPercent } from '$lib/util/format'
	import { sum } from '$lib/util/data'
	import { cn } from '$lib/utils'

	import { NeedHelp } from '../general'
	import IndicatorPercentTable from './IndicatorPercentTable.svelte'

	const {
		type,
		label,
		group,
		description,
		url,
		goodThreshold,
		values,
		valueLabel,
		outsideExtentPercent,
		icon
	} = $props()

	const mapData: MapData = getContext('map-data')

	const { totalIndicatorPercent, percentTableValues } = $derived.by(() => {
		const totalPercent = sum(values.map(({ percent }: { percent: number }) => percent))

		const tableValues = values
			.map((value: object, i: number) => ({
				...value,
				isHighValue: i === values.length - 1,
				isLowValue: i === 0
			}))
			.reverse()

		const notEvaluatedPercent = 100 - outsideExtentPercent - totalPercent
		if (notEvaluatedPercent >= 1) {
			tableValues.push({
				value: -1,
				label: 'Not evaluated for this indicator',
				percent: notEvaluatedPercent
			})
		}

		if (outsideExtentPercent >= 1) {
			tableValues.push({
				value: -3,
				label: 'Outside Midwest Blueprint',
				percent: outsideExtentPercent
			})
		}

		return {
			percentTableValues: tableValues,
			totalIndicatorPercent: totalPercent
		}
	})
</script>

<div class="flex flex-col h-full overflow-hidden">
	<div
		class="border-b p-1"
		style={`background-color:${group.color}; border-color:${group.borderColor};`}
	>
		<Button
			class="shadow-none rounded-none bg-transparent hover:bg-transparent w-full flex justify-between items-center pl-1 pr-4 text-foreground text-wrap whitespace-break-spaces h-auto gap-4 py-1"
			onclick={() => (mapData.selectedIndicator = null)}
		>
			<div class="flex items-start">
				<ReplyIcon class="size-3 flex-none text-grey-9/75" />
				<div class="flex gap-2 flex-auto items-center">
					<img
						src={icon}
						alt={`${group.label} icon`}
						class="flex-none size-10 bg-white rounded-full block border-[1.5px] border-[#999999] p-px"
					/>
					<div class="flex flex-col leading-tight items-start text-left">
						<div class="font-sm color-grey-8">
							{group.label}
						</div>
						<h4 class="text-xl leading-tight">
							{label}
						</h4>
					</div>
				</div>
			</div>
			{#if type !== 'pixel'}
				<div class="flex-none text-grey-8 text-sm text-right leading-tight">
					<b>{formatPercent(totalIndicatorPercent)}%</b>
					<br />
					of area
				</div>
			{/if}
		</Button>
	</div>

	<div class="px-4 pb-4 h-full flex-auto overflow-y-auto">
		{#if valueLabel}
			<div class="mt-4 -mb-6 font-bold">{valueLabel}:</div>
		{/if}

		<IndicatorPercentTable values={percentTableValues} {goodThreshold} />

		<div
			class={cn('text-md leading-snug mt-2', {
				'mt-1': type === 'pixel'
			})}
		>
			{description}
		</div>

		<div class="mt-8">
			To learn more and explore the GIS data,
			<a href={url} target="_blank">
				view this indicator in the Midwest Conservation Action Portal</a
			>.
		</div>

		<NeedHelp />
	</div>
</div>
