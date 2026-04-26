<script lang="ts">
	import { setContext, untrack } from 'svelte'
	import { dev } from '$app/environment'
	import { asset } from '$app/paths'
	import { QueryClient, QueryClientProvider } from '@tanstack/svelte-query'

	import ExclamationTriangleIcon from '~icons/fa-solid/exclamation-triangle'

	import type { LocationData } from '$lib/types'
	import {
		Footer,
		Header,
		MobileDetailsHeader,
		MobileTabs,
		SidebarDetailsHeader
	} from '$lib/components/layout'
	import { Map, MapData } from '$lib/components/map'
	import {
		ContactTab,
		FiltersTab,
		FindLocationTab,
		IndicatorsTab,
		InfoTab,
		MoreInfoTab,
		PrioritiesTab
	} from '$lib/components/tabs'
	import { cn } from '$lib/utils'

	let isMobile: boolean = $state(false)

	const mapData = new MapData()
	setContext('map-data', mapData)

	let locationData: LocationData = $state({ location: null })
	setContext('location-data', locationData)

	// TODO: may not need this, may be able to have every tab scroll itself instead
	let contentNode: Element | null = $state(null)

	// default tabs: info, filter, map (mobile), find (mobile), contact (mobile)
	// data tabs: map (mobile), selected-priorities, selected-indicators, selected-more-info
	let tab = $state('info') // will be set to map if detected on mobile in attachment below
	let prevMobileTab: string | null = $state(null)

	$effect(() => {
		tab
		isMobile
		mapData.mapMode
		mapData.data

		let nextTab = tab

		if (isMobile) {
			if (mapData.data === null && tab.startsWith('selected-')) {
				nextTab = 'map'
			}
		} else {
			if (mapData.data === null && tab.startsWith('selected-')) {
				nextTab = 'info'
			} else if (mapData.mapMode === 'filter' && tab !== 'filter') {
				nextTab = 'filter'
			} else if (tab === 'filter' && mapData.mapMode !== 'filter') {
				nextTab = mapData.data !== null ? 'selected-priorities' : 'info'
			} else if (tab === 'info' && mapData.data !== null) {
				nextTab = 'selected-priorities'
			}
		}

		if (nextTab !== tab) {
			if (nextTab !== 'selected-indicators') {
				mapData.selectedIndicator = null
			}

			tab = nextTab
		}
	})

	const handleSetLocation = () => {
		if (tab === 'find' && !!locationData.location) {
			tab = 'map'
		}
	}

	const handleTabChange = (newTab: string) => {
		tab = newTab

		// reset selected indicator on intentional tab change
		mapData.selectedIndicator = null

		// scroll content to top
		if (contentNode) {
			contentNode.scrollTop = 0
		}
	}

	const handleWindowMatchMediaChange = ({ matches: nextIsMobile }: { matches: boolean }) => {
		let nextTab = tab

		if (isMobile && !nextIsMobile) {
			prevMobileTab = tab

			// switched from mobile to desktop; if on any of the mobile-only tabs, switch to info
			if (tab === 'map' || tab === 'find' || tab === 'contact') {
				// reset to info tab (default) on desktop
				nextTab = 'info'
			}
		} else if (!isMobile && nextIsMobile) {
			// switched from desktop to mobile
			if (tab === 'info') {
				// reset to map tab (default) on mobile
				nextTab = prevMobileTab || 'map'
			}
		}

		isMobile = nextIsMobile
		tab = nextTab
	}

	const windowMediaQueryHandler = (w: Window) => {
		// match tailwind "md" breakpoint
		const mediaQueryList = w.matchMedia('(max-width:768px)')

		// set mobile default tab on init
		if (mediaQueryList.matches && untrack(() => tab) === 'info') {
			tab = 'map'
		}

		isMobile = mediaQueryList.matches
		mediaQueryList.addEventListener('change', handleWindowMatchMediaChange)

		return () => {
			mediaQueryList.removeEventListener('change', handleWindowMatchMediaChange)
		}
	}
</script>

<svelte:head>
	<title>Midwest Conservation Blueprint Explorer</title>
	{#if !dev}
		<!-- only include manifest in production build -->
		<link rel="manifest" href={asset('/manifest.webmanifest')} />
	{/if}
</svelte:head>

<svelte:window {@attach windowMediaQueryHandler} />

<QueryClientProvider client={new QueryClient()}>
	<Header hasData={mapData && mapData.data !== null} />
	{#if isMobile && mapData && mapData.data}
		<MobileDetailsHeader {...mapData.data} onClose={() => mapData.setData(null)} />
	{/if}

	<main class="h-full w-full flex-auto overflow-auto">
		<div class="flex flex-col h-full flex-auto">
			<div class="flex h-full flex-auto overflow-y-hidden relative">
				<!-- sidebar -->
				<div
					bind:this={contentNode}
					class={cn(
						'md:flex h-full bg-white grow shrink-0 basis-full md:basis-[360px] lg:basis-[468px] w-max-[100%] md:w-max-[360px] lg:w-max-[468px] flex-col overflow-hidden absolute md:relative left-0 right-0 top-0 bottom-0 z-10000 md:z-1',
						{
							hidden: tab === 'map'
						}
					)}
				>
					{#if !isMobile && mapData.data !== null}
						<SidebarDetailsHeader {tab} onTabChange={handleTabChange} />
					{/if}

					<InfoTab class={tab === 'info' ? '' : 'hidden'} />

					<!-- primary tabs are hidden via css instead of omitted from template to preserve
					state of filters and location tabs -->
					<FiltersTab class={tab === 'filter' ? '' : 'hidden'} />
					<FindLocationTab
						onSetLocation={handleSetLocation}
						class={tab === 'find' ? '' : 'hidden'}
					/>
					<ContactTab class={tab === 'contact' ? '' : 'hidden'} />

					<!-- selected data tabs -->
					{#if mapData.data !== null}
						{#if mapData.data.isLoading}
							<div class="mt-8 text-center text-lg text-grey-8">Loading...</div>
						{:else if mapData.data.blueprint === undefined || mapData.data.blueprint === null}
							<div class="flex gap-2 items-center mt-8 px-4">
								<ExclamationTriangleIcon class="size-6 flex-none text-accent" />
								<text class="text-grey-8 flex-auto font-bold">
									No pixel-level details are available for this area.
								</text>
							</div>
						{:else if tab === 'selected-priorities'}
							<PrioritiesTab {...mapData.data} />
						{:else if tab === 'selected-indicators'}
							<IndicatorsTab {...mapData.data} />
						{:else if tab === 'selected-more-info'}
							<MoreInfoTab {...mapData.data} />
						{/if}
					{/if}
				</div>

				<Map />
			</div>

			<!-- mobile bottom tabs	-->
			<MobileTabs {tab} onChange={handleTabChange} />
		</div>
	</main>
	<Footer />
</QueryClientProvider>
