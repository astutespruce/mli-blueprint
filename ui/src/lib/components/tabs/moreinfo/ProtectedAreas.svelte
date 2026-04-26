<script lang="ts">
	import CheckIcon from '~icons/fa-solid/check'
	import { PercentBarChart } from '$lib/components/chart'
	import { protectedAreas as categories } from '$lib/config/constants'
	import { formatNumber } from '$lib/util/format'
	import { cn } from '$lib/utils'

	const { type, protectedAreas, protectedAreasList, numProtectedAreas } = $props()

	const bars = $derived(
		categories.map((category) => ({
			...category,
			percent: protectedAreas ? protectedAreas[category.value] || 0 : 0
		}))
	)
</script>

<div class="not-first:mt-8 not-first:border-t not-first:border-t-grey-2 not-first:pt-8">
	<h3 class="text-2xl">Protected Areas</h3>

	{#if type === 'pixel'}
		<div class="ml-2 mt-2">
			{#each categories as { value, label } (value)}
				<div
					class="flex items-baseline justify-between pl-2 border-b border-b-grey-2 pb-1 not-first:mt-1 gap-4"
				>
					<div
						class={cn('flex-auto text-grey-8', {
							'text-foreground font-bold': value === protectedAreas
						})}
					>
						{label}
					</div>

					<CheckIcon
						class={cn('size-4 flex-none invisible', { visible: value === protectedAreas })}
					/>
				</div>
			{/each}
		</div>
	{:else}
		{#each bars as bar (bar.label)}
			<PercentBarChart {...bar} class="mt-2 mb-4" />
		{/each}
	{/if}

	{#if protectedAreasList && protectedAreasList.length > 0}
		<div class="mt-6">
			<div class="font-bold">Protected areas at this location</div>
			<ul class="mt-2 list-disc ml-4 text-grey-9">
				{#each protectedAreasList as name, i (`${name}-${i}`)}
					<li class="not-first:mt-2">{name}</li>
				{/each}

				{#if numProtectedAreas && numProtectedAreas - protectedAreasList.length > 0}
					<li class="not-first:mt-2">
						...and {formatNumber(numProtectedAreas - protectedAreasList.length)} more...
					</li>
				{/if}
			</ul>
		</div>
	{/if}

	<div class="mt-8 text-grey-8 leading-snug">
		Protected areas are derived from the
		<a
			href="https://www.usgs.gov/programs/gap-analysis-project/science/pad-us-data-download"
			target="_blank"
		>
			Protected Areas Database of the United States
		</a>
		(PAD-US v4.1) and include Fee, Designation, Easement, Marine, and Proclamation (Dept. of Defense lands
		only) boundaries.

		{#if protectedAreasList && protectedAreasList.length > 0}
			Areas are listed based on name, ownership, and boundary information in the Protected Areas
			Database of the United States, which may include overlapping and duplicate areas.
		{/if}
	</div>
</div>
