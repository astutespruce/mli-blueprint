<script lang="ts">
	import { getContext } from 'svelte'

	import EnvelopeIcon from '~icons/fa-solid/envelope'
	import FilterIcon from '~icons/fa-solid/filter'
	import InfoIcon from '~icons/fa-solid/info-circle'
	import LineChartIcon from '~icons/fa-solid/chart-line'
	import MapIcon from '~icons/fa-solid/map'
	import PieChartIcon from '~icons/fa-solid/chart-pie'
	import SearchIcon from '~icons/fa-solid/search-location'
	import TasksIcon from '~icons/fa-solid/tasks'
	import { Button } from '$lib/components/ui/button'
	import { MapData } from '$lib/components/map'
	import { cn } from '$lib/utils'

	const mapData: MapData = getContext('map-data')
	const { tab, onChange } = $props()

	const defaultTabs = [
		{ id: 'info', label: 'Info', icon: InfoIcon },
		{ id: 'map', label: 'Map', icon: MapIcon },
		{ id: 'find', label: 'Find Location', icon: SearchIcon },
		{ id: 'contact', label: 'Contact', icon: EnvelopeIcon }
	]

	const dataTabs = [
		{ id: 'map', label: 'Map', icon: MapIcon },
		{ id: 'selected-priorities', label: 'Priorities', icon: PieChartIcon },
		{ id: 'selected-indicators', label: 'Indicators', icon: TasksIcon },
		{ id: 'selected-more-info', label: 'More info', icon: LineChartIcon }
	]

	const filterTabs = [
		{ id: 'map', label: 'Map', icon: MapIcon },
		{ id: 'filter', label: 'Filter', icon: FilterIcon },
		{ id: 'find', label: 'Find Location', icon: SearchIcon },
		{ id: 'contact', label: 'Contact', icon: EnvelopeIcon }
	]

	let tabs = $derived.by(() => {
		if (mapData.mapMode === 'filter') {
			return filterTabs
		} else if (mapData.data !== null && !mapData.data.isLoading) {
			return dataTabs
		}
		return defaultTabs
	})

	const handleClick = (id: string) => () => {
		onChange(id)
	}
</script>

<div class="md:hidden flex-none border-t border-t-grey-9 leading-snug">
	<nav class="grid auto-cols-fr grid-flow-col gap-0 items-center">
		{#each tabs as { id, label, icon: Icon } (id)}
			<Button
				class={cn(
					'flex flex-col gap-0 items-center justify-center text-center grow p-2 h-10 select-none rounded-none text-grey-1 text-[10px]',
					{
						'text-white': id === tab,
						'bg-blue-9': id === tab
					}
				)}
				onclick={handleClick(id)}
			>
				<Icon class="size-3.5" />
				{label}
			</Button>
		{/each}
	</nav>
</div>
