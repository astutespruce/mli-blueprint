<script lang="ts">
	import { getContext } from 'svelte'

	import ExclamationTriangle from '~icons/fa-solid/exclamation-triangle'
	import FilterIcon from '~icons/fa-solid/filter'
	import TimesCircle from '~icons/fa-solid/times-circle'
	import { Button } from '$lib/components/ui/button'
	import BlueprintIcon from '$images/blueprint.svg'
	import HumanWellbeingIcon from '$images/h.svg'
	import LandscapeHealthIcon from '$images/l.svg'
	import WildlifeIcon from '$images/w.svg'
	import OtherInfoIcon from '$images/otherInfo.svg'
	import type { MapData } from '$lib/components/map'
	import { setIntersection } from '$lib/util/data'
	import type { Filter } from '$lib/types'
	import { cn } from '$lib/utils'
	import { indicatorGroups, indicatorsIndex } from '$lib/config/constants'
	import {
		priorityFilters as rawPriorityFilters,
		otherInfoFilters as rawOtherInfoFilters
	} from '$lib/config/filters'
	import { FilterGroup } from '$lib/components/filter'

	const indicatorGroupIcons = {
		h: HumanWellbeingIcon,
		l: LandscapeHealthIcon,
		w: WildlifeIcon
	}

	const { class: className } = $props()
	const mapData: MapData = getContext('map-data')

	type FilterVisibilityStub = {
		canBeVisible: boolean
		enabled: boolean
	}

	let { priorityFilters, otherInfoFilters, ...indicatorGroupFilters } = $derived.by(() => {
		return {
			priorityFilters: rawPriorityFilters
				.map((entry) => ({
					...entry,
					...mapData.filters[entry.id],
					canBeVisible: mapData.visibleSubregions.size > 0
				}))
				.filter(
					({ canBeVisible, enabled }: FilterVisibilityStub) => canBeVisible || enabled // mapData.filters[id].enabled
				),

			...Object.fromEntries(
				indicatorGroups.map(({ id: groupId, indicators }) => {
					const indicatorFilters = indicators
						.map((id) => {
							const { subregions: indicatorSubregions, values, ...rest } = indicatorsIndex[id]

							return {
								id,
								...rest,
								// sort indicator values in descending order
								values: values.slice().reverse(),
								...mapData.filters[id],
								// null / empty subregions indicates the indicator is visible everywhere
								canBeVisible:
									indicatorSubregions.size === 0 ||
									setIntersection(indicatorSubregions, mapData.visibleSubregions).size > 0
							}
						})
						.filter(({ canBeVisible, enabled }: FilterVisibilityStub) => canBeVisible || enabled)

					return [groupId, indicatorFilters]
				})
			),

			otherInfoFilters: rawOtherInfoFilters
				.map((entry) => ({
					...entry,
					...mapData.filters[entry.id],
					canBeVisible: true
				}))
				.filter(({ canBeVisible, enabled }: FilterVisibilityStub) => canBeVisible || enabled)
		}
	})

	const handleFilterChange = ({ id, enabled, activeValues }: Filter & { id: string }) => {
		mapData.setLayerFilterValues(id, { enabled, activeValues })
	}

	const handleResetFilters = () => {
		mapData.resetFilters()
	}
</script>

<section class={cn('flex flex-col h-full', className)}>
	<div class="flex justify-between flex-none pt-4 pb-2 px-2 border-b border-b-grey-2">
		<div class="flex items-center gap-2">
			<FilterIcon class="size-5" />
			<h2 class="text-2xl leading-tight">Filter the blueprint</h2>
		</div>
		<div
			class={cn('flex justify-end items-center', {
				hidden: mapData.numEnabledFilters === 0
			})}
		>
			<Button onclick={handleResetFilters} class="text-sm px-2 gap-1 py-0 h-7">
				<TimesCircle width="1em" height="1em" class="p-0 m-0" />
				reset {mapData.numEnabledFilters} filter{mapData.numEnabledFilters > 1 ? 's' : ''}
			</Button>
		</div>
	</div>

	<div class="flex-auto h-full overflow-y-auto">
		{#if mapData.filtersLoading}
			<div class="mt-4 text-center text-xl text-grey-8">Loading...</div>
		{:else if mapData.hasVisibleFilters}
			<div class="flex flex-col overflow-y-auto flex-auto h-full relative">
				<div class="px-4 py-2 leading-tight text-grey-8">
					Filters can help you find the part of the blueprint that aligns with your mission,
					interest, or specific question. Enable the filters below to narrow down the Blueprint to
					the part that falls within a range of values for one or more layers.
				</div>

				<FilterGroup
					id="priorities"
					label="Filter by priorities"
					icon={BlueprintIcon}
					color="#4d004b0d"
					borderColor="#4d004b2b"
					entries={priorityFilters}
					onChange={handleFilterChange}
				/>

				{#each indicatorGroups as { id, label, color, borderColor } (id)}
					<FilterGroup
						{id}
						label={`Filter by ${label.toLowerCase()}`}
						icon={indicatorGroupIcons[id as keyof typeof indicatorGroupIcons]}
						{color}
						{borderColor}
						entries={indicatorGroupFilters[id as keyof typeof indicatorGroupFilters]}
						onChange={handleFilterChange}
					/>
				{/each}

				<FilterGroup
					id="other-info"
					label="More filters"
					icon={OtherInfoIcon}
					color="#f3c6a830"
					borderColor="#f3c6a891"
					entries={otherInfoFilters}
					onChange={handleFilterChange}
				/>
			</div>
		{:else}
			<div class="py-8 pl-4 pr-8 flex justify-center">
				<div class="flex items-center gap-2">
					<ExclamationTriangle class="size-6 flex-none text-[orange]" />
					<div class="flex-auto text-grey-8 text-lg">No filters are available for this area.</div>
				</div>
			</div>
		{/if}
	</div>
</section>
