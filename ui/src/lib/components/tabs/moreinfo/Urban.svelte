<script lang="ts">
	import CheckIcon from '~icons/fa-solid/check'
	import { urban as urbanCategories } from '$lib/config/constants'
	import { cn } from '$lib/utils'

	import UrbanChart from './UrbanChart.svelte'

	const YEARS = [2001, 2004, 2006, 2008, 2011, 2013, 2016, 2019, 2021, 2030, 2040, 2050, 2060]

	const { type, urban, regions } = $props()
</script>

<div class="not-first:mt-8 not-first:border-t not-first:border-t-grey-2 not-first:pt-8">
	<h3 class="text-2xl">Urbanization</h3>

	{#if type === 'pixel'}
		{#if urban === null || urban === undefined}
			<div class="text-grey-8">
				Projected future urbanization data is not currently available for this area.
			</div>
		{:else}
			<!-- show as list with checkmarks -->
			<div class="text-grey-8">Probability of urbanization by 2060:</div>
			{#each urbanCategories as { value, label } (value)}
				<div
					class="flex items-baseline justify-between pl-2 border-b border-b-grey-2 pb-1 not-first:mt-1 gap-4"
				>
					<div
						class={cn('flex-auto text-grey-8', {
							'text-foreground font-bold': value === urban
						})}
					>
						{label}
					</div>
					<CheckIcon class={cn('size-4 flex-none invisible', { visible: value === urban })} />
				</div>
			{/each}
		{/if}
	{/if}
	{#if type !== 'pixel'}
		{#if !(urban && urban.length)}
			<div class="text-grey-8">
				This watershed is not impacted by projected urbanization up to 2100.
			</div>
		{:else}
			<div class="text-grey-8 leading-tight">
				Extent of past, current, and projected urbanization within this subwatershed:
			</div>

			<UrbanChart data={urban.map((y: number, i: number) => ({ x: YEARS[i], y }))} />
		{/if}
	{/if}

	<div class="mt-8 text-grey-8 leading-tight">
		Past and current (2021) urban levels based on developed land cover classes from the
		<a
			href="https://www.usgs.gov/centers/eros/science/national-land-cover-database"
			target="_blank"
		>
			National Land Cover Database
		</a>. Future urban growth estimates derived from
		<a href="https://www.sciencebase.gov/catalog/item/63f50297d34efa0476b04cf7" target="_blank">
			FUTURES model projections for the contiguous United States
		</a>
		developed by the
		<a href="https://cnr.ncsu.edu/geospatial/" target="_blank">
			Center for Geospatial Analytics
		</a>, NC State University. To explore maps of additional time periods,
		<a
			href="https://www.arcgis.com/apps/mapviewer/index.html?webmap=3d2eadbfd0b347eca3dcb927e9778dd9"
			target="_blank"
			aria-label="link for urbanization ArcGIS Online map"
		>
			click here
		</a>.
	</div>
</div>
