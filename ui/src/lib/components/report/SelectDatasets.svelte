<script lang="ts">
	import CheckIcon from '@lucide/svelte/icons/check'
	import CaretDown from '~icons/fa-solid/caret-down'
	import CaretRight from '~icons/fa-solid/caret-right'
	import BlueprintIcon from '$images/blueprint.svg'
	import HumanWellbeingIcon from '$images/h.svg'
	import LandscapeHealthIcon from '$images/l.svg'
	import WildlifeIcon from '$images/w.svg'
	import OtherInfoIcon from '$images/otherInfo.svg'

	import { cn } from '$lib/utils'

	import {
		blueprint,
		indicatorGroups,
		indicatorsIndex,
		urbanByDecade,
		protectedAreas
	} from '$lib/config/constants'
	import { Button } from '$lib/components/ui/button'
	import { Checkbox } from '$lib/components/ui/checkbox'
	import * as Collapsible from '$lib/components/ui/collapsible'
	import { Label } from '$lib/components/ui/label'
	import { InfoTooltip } from '$lib/components/tooltip'

	const priorityDatasets = [blueprint]
	// polygon versions of protected areas are automatically included
	// when their raster versions are included and not itemized individually
	const otherInfoDatasets = [protectedAreas, urbanByDecade]

	const indicatorGroupIcons = {
		h: HumanWellbeingIcon,
		l: LandscapeHealthIcon,
		w: WildlifeIcon
	}

	type Props = {
		availableDatasets: Record<string, boolean>
		selectedDatasets: Record<string, boolean>
	}

	let { availableDatasets, selectedDatasets = $bindable() }: Props = $props()

	let openCategories: Record<string, boolean> = $state({
		priorities: true,
		...Object.fromEntries(indicatorGroups.map(({ id }) => [id, true])),
		otherInfo: true
	})

	const categories = $derived.by(() => {
		// always show all priority datasets; by definition they must be present
		const out = [
			{
				id: 'priorities',
				icon: BlueprintIcon,
				label: 'Priorities',
				color: '#4d004b0d',
				borderColor: '#4d004b2b',
				datasets: priorityDatasets
			}
		]

		indicatorGroups.forEach(({ id, label, color, borderColor, indicators }) => {
			const indicatorsPresent = indicators
				.filter((indicatorId) => availableDatasets[indicatorId])
				.map((indicatorId) => indicatorsIndex[indicatorId])
			if (indicatorsPresent.length > 0) {
				out.push({
					id,
					icon: indicatorGroupIcons[id as keyof typeof indicatorGroupIcons],
					label: `${label} indicators`,
					color,
					borderColor,
					datasets: indicatorsPresent
				})
			}
		})

		// only show the other info datasets that are present, and omit the category if not
		const otherInfoDatasetsPresent = otherInfoDatasets.filter(({ id }) => availableDatasets[id])
		if (otherInfoDatasetsPresent.length > 0) {
			out.push({
				id: 'otherInfo',
				icon: OtherInfoIcon,
				label: 'More info',
				color: '#f3c6a830',
				borderColor: '#f3c6a891',
				datasets: otherInfoDatasetsPresent
			})
		}

		return out
	})

	const handleSelectAll = () => {
		Object.entries(availableDatasets).forEach(([id]) => {
			selectedDatasets[id] = true
		})
	}

	const handleSelectNone = () => {
		// blueprint is always checked
		Object.entries(availableDatasets)
			.filter(([id]) => id !== blueprint.id)
			.forEach(([id]) => {
				selectedDatasets[id] = false
			})
	}
</script>

<div>
	<div class="sm:flex gap-4">
		<div class="text-2xl font-bold">Choose datasets to include:</div>
		<div class="flex items-center gap-2 flex-none justify-end">
			<Button variant="link" class="p-0 text-base" onclick={handleSelectAll}>select all</Button>
			<div class="text-grey-2">|</div>
			<Button variant="link" class=" p-0 text-base" onclick={handleSelectNone}>select none</Button>
		</div>
	</div>

	<p>
		Choose the datasets you want to include in your analysis from the following datasets that
		overlap your analysis units. You may only choose from datasets that overlap; other datsets are
		not shown here.
	</p>

	<div class="mt-6">
		{#each categories as category (category.id)}
			<Collapsible.Root
				bind:open={openCategories[category.id]}
				class="not-first-of-type:mt-2 not-last-of-type:mb-8"
			>
				<Collapsible.Trigger
					class="w-full py-2 border-t border-b items-center flex gap-2 text-start px-2 cursor-pointer"
					style={`background-color: ${category.color}; border-color: ${category.borderColor}`}
				>
					{#if openCategories[category.id]}
						<CaretDown class="size-6" aria-hidden="true" />
					{:else}
						<CaretRight class="size-6" aria-hidden="true" />
					{/if}
					<img
						src={category.icon}
						alt=""
						aria-hidden="true"
						class={cn('size-8 bg-white rounded-full ', {
							'border-[1.5px] border-grey-8':
								category.id !== 'priorities' && category.id !== 'otherInfo'
						})}
					/>

					<div class="font-bold text-xl">
						{category.label}
					</div>
				</Collapsible.Trigger>
				<Collapsible.Content class="mt-2">
					{#each category.datasets as dataset (dataset.id)}
						<div class="flex items-center gap-2">
							{#if dataset.id === blueprint.id}
								<CheckIcon class="size-5" />
								<div>
									{dataset.label}
									<span class="text-sm text-muted-foreground">(always included)</span>
								</div>
							{:else}
								<Checkbox
									id={dataset.id}
									aria-label={`Select / deselect ${dataset.label}`}
									class="cursor-pointer size-5 rounded-xs disabled:border-grey-8/50 border-2 [&_svg]:size-4"
									bind:checked={selectedDatasets[dataset.id]}
								/>
								<Label for={dataset.id} class="text-base cursor-pointer">
									{dataset.label}
								</Label>
							{/if}
							<div class="mt-2">
								<InfoTooltip
									title={dataset.label}
									description={dataset.description}
									aria-label={`Show details for ${dataset.label}`}
								/>
							</div>
						</div>
					{/each}
				</Collapsible.Content>
			</Collapsible.Root>
		{/each}
	</div>
</div>
