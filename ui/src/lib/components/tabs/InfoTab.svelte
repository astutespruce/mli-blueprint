<script lang="ts">
	import { resolve } from '$app/paths'
	import { BLUEPRINT_URL, DEPLOY_ENV } from '$lib/env'
	import TimesCircle from '~icons/fa-solid/times-circle'
	import { Root as Alert } from '$lib/components/ui/alert'
	import MLILogo from '$images/MLI_logo_graphic.svg'
	import { cn } from '$lib/utils'

	const isStaging = DEPLOY_ENV === 'staging'

	const { class: className } = $props()
</script>

<section class={cn('overflow-y-auto px-4 h-full pt-4 pb-8', className)}>
	{#if isStaging}
		<Alert variant="destructive" class="text-md my-4">
			<b>WARNING</b>: this is a test version of this application used for verifying recent changes;
			it is not intended for general use.
		</Alert>
	{/if}

	<p class="text-lg">
		<b
			>The Midwest Conservation Blueprint is a basemap of priority lands and waters for
			conservation,</b
		>
		reflecting a diverse set of 20+ social and environmental values.
		<br />
		<br />
		It serves as an invitation to better coordinate voluntary conservation actions and investments across
		the Midwest by focusing and aligning conservation work, attracting and directing funding for conservation,
		and connecting partners and opening the door to all audiences.
		<br /><br />

		For more information, visit the
		<a href={BLUEPRINT_URL} target="_blank"> blueprint webpage </a>.
		<br />
		<br />
		The <b>Midwest Conservation Blueprint Explorer</b> is an online viewer designed to help you understand
		the blueprint and discover how your area of interest scores on the blueprint priorities, indicators,
		and other landscape-level information. Here, you can:
	</p>

	<ul class="text-lg list-disc pl-6 mt-1 [&>li]:pb-2">
		<li>
			<b>Summarize data</b> to show charts and information for a subwatershed
		</li>
		<li>
			<b>View point data</b> to discover what is driving the blueprint priorities and show values at a
			specific location for indicators, threats, and more
		</li>
		<li>
			<b>Filter the blueprint</b> to find your part of the blueprint by showing only areas that score
			within a certain range on indicators and other data
		</li>
		<li>
			<b>Upload a shapefile</b> to create detailed custom reports of the blueprint, underlying indicators,
			and other landscape-level information in your area
		</li>
	</ul>

	<p class="hidden md:block text-lg mt-2">
		<a href={resolve('/help')} target="_blank" rel="noreferrer">
			Read instructions on how to use this viewer
		</a>.
	</p>

	<div class="md:hidden">
		<hr class="my-6" />
		<h2 class="text-2xl">How To Use This Viewer</h2>
		<h3 class="text-xl">Subwatershed details:</h3>
		<p class="mt-1 text-lg">
			Choose <b>Summary data</b> from the button bar below the map. Click on any subwatershed for
			details. You may need to zoom in futher to select an area.
			<br />
			<br />
			Use the tabs in the bottom bar to navigate the different types of summary information available.
			<br />
			<br />
			On the indicators tab, you can see which indicators are present in that area. Click on an indicator
			for more information and to see the range of values that occur there.
			<br />
			<br />
			To unselect the area, click on the <TimesCircle
				class="size-4.5 mx-1 text-grey-8 inline-block"
			/> button in the top bar.
		</p>

		<h3 class="text-xl mt-10">Pixel-level details:</h3>
		<p class="text-lg mt-1">
			Choose <b>View point data</b> from the button bar below the map. The crosshairs in the center
			of the map will pinpoint a specific place and show details for that location in the sidebar.
			You may have to zoom in for the crosshairs to appear. Zoom in further to choose a more precise
			location, especially in areas that are highly pixelated.
			<br />
			<br />
			Use the tabs in the bottom bar to navigate the different types of point-level information available
			for priorities, indicators, threats, and partners.
			<br />
			<br />
			The indicators tab shows the pixel value for each indicator present at that point. Click on an indicator
			for more information about it.
			<br />
			<br />
			Note: this approach uses pixels that have been resampled and reprojected for each zoom level. This
			means that the values shown in the tool may not exactly match the blueprint and indicator data for
			that specific ground location, especially in areas of high variability in the data. To view and
			/ or download more precise spatial data, please visit the
			<a href={BLUEPRINT_URL} target="_blank">
				blueprint page of the Midwest Conservation Action Portal
			</a>.
			<br />
			<br />
			To unselect the pixel, click on the <TimesCircle
				class="size-4.5 mx-1 text-grey-8 inline-block"
			/> button in top bar.
		</p>
		<h3 class="text-xl mt-10">To find a specific area:</h3>
		<p class="text-lg mt-1">
			Use the <b>Find Location</b> tab at the bottom to search for a place by name. When you tap on
			a place to select it from the list, it will show a marker at that location on the map.
			<br />
			You can also choose to add a marker at your current location (if allowed by your device).
		</p>
	</div>

	<hr class="my-8" />

	<div class="flex flex-wrap lg:flex-nowrap gap-4 leading-snug">
		<div class="flex-none">
			<img src={MLILogo} class="w-16" alt="MLI logo" />
		</div>
		<div class="flex-auto">
			<p>
				<b>Citation:</b> Midwest Landscape Initiative. 2026. Midwest Conservation Blueprint 2026.
				<a href={BLUEPRINT_URL} target="_blank">
					{BLUEPRINT_URL}
				</a>.
			</p>
		</div>
	</div>
	<p class="mt-4 leading-snug">
		This application was developed by
		<a href="https://astutespruce.com" target="_blank"> Astute Spruce, LLC </a>
		in partnership with the U.S. Fish and Wildlife Service.
	</p>
</section>
