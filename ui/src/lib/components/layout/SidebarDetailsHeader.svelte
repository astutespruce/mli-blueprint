<script lang="ts">
	import { getContext } from 'svelte'

	import LineChartIcon from '~icons/fa-solid/chart-line'
	import PieChartIcon from '~icons/fa-solid/chart-pie'
	import TasksIcon from '~icons/fa-solid/tasks'
	import TimesCircleIcon from '~icons/fa-regular/times-circle'
	import { Button } from '$lib/components/ui/button'
	import type { MapData } from '$lib/components/map'
	import { SummaryReportModal } from '$lib/components/report'
	import { formatNumber } from '$lib/util/format'
	import { cn } from '$lib/utils'

	const { tab, onTabChange } = $props()
	const mapData: MapData = getContext('map-data')

	const tabs = [
		{ id: 'selected-priorities', label: 'Priorities', icon: PieChartIcon },
		{ id: 'selected-indicators', label: 'Indicators', icon: TasksIcon },
		{ id: 'selected-more-info', label: 'More info', icon: LineChartIcon }
	]

	const handleTabClick = (id: string) => () => {
		onTabChange(id)
	}
</script>

<div class="flex-none hidden md:block">
	{#if mapData.data.type === 'pixel'}
		<div class="flex justify-between items-center gap-4 p-4">
			<div class="text-grey-9 text-lg flex-auto">
				Coordinates: {mapData.data.location.latitude.toPrecision(5)}°N, {mapData.data.location.longitude.toPrecision(
					5
				)}°
			</div>
			<div
				class={cn('flex-none justify-end items-center invisible', {
					visible: mapData.numEnabledFilters > 0
				})}
			>
				<Button onclick={() => mapData.resetFilters()} class="text-sm h-7">
					<TimesCircleIcon class="size-4" />
					reset {mapData.numEnabledFilters} pixel filter{mapData.numEnabledFilters > 1 ? 's' : ''}
				</Button>
			</div>
		</div>
	{:else}
		<div class="flex justify-between items-start gap-4 pt-4 pl-4 min-h-28">
			<div class="flex-auto">
				<h2 class="text-2xl leading-none">
					{mapData.data.name}
					{#if mapData.data.type === 'subwatershed'}
						<span class="text-sm font-normal">(HUC12)</span>
					{/if}
				</h2>
				{#if mapData.data.acres !== null}
					<div class="text-grey-8 text-md">
						{formatNumber(mapData.data.acres)} acres
					</div>
				{/if}
			</div>
			<Button
				aria-label="unselect summary unit"
				class="flex-none text-grey-9/40 hover:text-grey-9 bg-transparent hover:bg-transparent shadow-none rounded-full m-0 p-0 h-6"
				onclick={() => {
					mapData.setData(null)
				}}
			>
				<TimesCircleIcon class="size-6" />
			</Button>
		</div>

		<div class="px-4">
			<SummaryReportModal id={mapData.data.id} type={mapData.data.type} />
		</div>
	{/if}

	<nav class="grid auto-cols-fr grid-flow-col gap-0 items-center border-t-2 border-t-grey-2">
		{#each tabs as { id, label, icon: Icon } (id)}
			<div
				class={cn('p-1 bg-grey-1 border-b border-b-grey-2', {
					'bg-white hover:bg-white border-b-transparent': id === tab
				})}
			>
				<Button
					class="w-full flex gap-2 items-center justify-center text-center grow p-2 h-8 select-none rounded-none text-grey-9 text-md bg-transparent hover:bg-transparent shadow-none"
					onclick={handleTabClick(id)}
				>
					<Icon class="size-6" />
					{label}
				</Button>
			</div>
		{/each}
	</nav>
</div>
