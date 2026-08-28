<script lang="ts">
	import { getContext, untrack } from 'svelte'
	import { SvelteSet } from 'svelte/reactivity'
	import { MapboxOverlay } from '@deck.gl/mapbox'
	import * as mapboxgl from 'mapbox-gl/esm'
	import type { LngLatLike, Map, Marker, SourceSpecification } from 'mapbox-gl/esm'
	import 'mapbox-gl/dist/mapbox-gl.css'

	import CrosshairsIcon from '$images/CrosshairsIcon.svg'
	import Spinner from '~icons/fa-solid/spinner'

	import { subregionIndex } from '$lib/config/constants'
	import { mapConfig as config, sources, layers } from '$lib/config/map'
	import { pixelLayers } from '$lib/config/pixelLayers'
	import { MAPBOX_TOKEN } from '$lib/env'
	import type { LocationData } from '$lib/types'
	import { indexBy } from '$lib/util/data'
	import { debounce, eventHandler } from '$lib/util/func'

	import { unpackFeatureData } from './features'
	import FindLocation from './FindLocation.svelte'
	import { extractPixelData, StackedPNGTileLayer } from './gl'
	import { Legend } from './legend'

	import LayerToggle from './LayerToggle.svelte'
	import { ModeToggle } from './mode'
	import { MapState } from './state.svelte'
	import StyleToggle from './StyleToggle.svelte'
	import { serializeMapCenterZoomToURL, deserializeMapCenterZoomFromURL } from './util'
	import { getCenterAndZoom } from './viewport'

	let map: Map
	let marker: Marker | null = null

	const mapState: MapState = getContext('map-state')
	const locationData: LocationData = getContext('location-data')

	let isLoaded: boolean = $state(false)
	let currentZoom: number = $state(3)
	let highlightId: number | string | undefined = $state()

	// mapIsDrawing is used to show the spinner; it only gets set via a deounced callback to prevent short duration flashes
	let mapIsDrawing: boolean = $state(false)
	// delayedMapIsDrawing is toggled immediately when map enters drawing state and is used in callback to determine if should toggle mapIsDrawing
	let delayedMapIsDrawing: boolean = $state(false)

	const deckGLHandler = eventHandler(50)
	const updateMapIsDrawing = debounce(() => {
		mapIsDrawing = delayedMapIsDrawing
	}, 1500)

	// resize map to handle layout shift on mobile
	const resizeMap = debounce(() => {
		map.resize()
	}, 10)

	// layer in Mapbox Light that we want to come AFTER our layers here
	const beforeLayer = 'waterway-label'

	const minPixelLayerZoom = 7 // minimum reasonable zoom for getting pixel data
	const minSummaryZoom = layers.filter(({ id }) => id === 'unit-outline')[0].minzoom

	const setPixelLayerProps = (newProps: object) => {
		if (!map) return

		// this happens in hot reload
		// @ts-expect-error __deck is dynamically defined
		if (!(map && map.__deck && map.__deck.layerManager)) return

		// @ts-expect-error __deck is valid
		map.__deck.setProps({
			// @ts-expect-error __deck is dynamically defined
			layers: [map.__deck.layerManager.layers[0].clone(newProps)]
		})
	}

	const getPixelData = debounce(async () => {
		if (mapState.mapMode !== 'pixel' || !map) {
			return
		}

		if (currentZoom < minPixelLayerZoom) {
			mapState.setData(null)
			resizeMap()
			return
		}

		// don't fetch data if layer is not yet available or is not visible
		// @ts-expect-error layer.deck is dynamically defined
		if (!map?.__deck?.layerManager?.layers[0]?.props?.visible) {
			return
		}

		const { lng: longitude, lat: latitude } = map.getCenter()

		// If protected areas tiles aren't loaded yet, schedule a callback once tiles are loaded
		if (!(
			map?.style?._otherSourceCaches.protectedAreas &&
			map.style._otherSourceCaches.protectedAreas.loaded()
		)) {
			mapState.setData({
				type: 'pixel',
				location: {
					longitude,
					latitude
				},
				isLoading: true
			})
			resizeMap()
			map.once('idle', () => {
				getPixelData()
			})
		}

		const pixelData = await extractPixelData(map, map.getCenter())

		if (pixelData === null) {
			// tile data not yet loaded for correct zoom, try again after next deckGL
			// render pass
			deckGLHandler.once(() => {
				getPixelData()
			})
		}

		mapState.setData({
			type: 'pixel',
			location: {
				longitude,
				latitude
			},
			isLoading: pixelData === null,
			...(pixelData || {})
		})
		resizeMap()
	}, 10)

	const updateVisibleSubregions = debounce(() => {
		if (mapState.mapMode !== 'filter' || !map) {
			return
		}

		const subregions = new SvelteSet<string>()
		map
			.queryRenderedFeatures(null, { layers: ['subregions'] })
			// @ts-expect-error subregion is OK
			.forEach(({ properties: { subregion } }) => {
				subregions.add(subregion)
			})

		mapState.visibleSubregions = subregions
	}, 10)

	// use a callback to actually update the layers, since may style may still
	// be loading
	const updateVisibleLayers = () => {
		mapIsDrawing = true

		// toggle layer visibility
		if (mapState.mapMode === 'unit') {
			map.setLayoutProperty('unit-fill', 'visibility', 'visible')
			map.setLayoutProperty('unit-outline', 'visibility', 'visible')
			map.setLayoutProperty(
				'blueprint',
				'visibility',
				mapState.renderLayerIsVisible ? 'visible' : 'none'
			)
			map.setLayoutProperty('protectedAreas', 'visibility', 'none')
			map.setLayoutProperty('subregions', 'visibility', 'none')

			// disable pixel layer event listener
			// @ts-expect-error __deck is dynamically defined
			map.__deck.setProps({
				onAfterRender: () => {} // no-op
			})
			setPixelLayerProps({
				visible: false,
				filterMode: mapState.filterMode,
				filters: mapState.activeFilterValues,
				data: { visible: false }
			})

			updateMapIsDrawing()

			return
		}
		// pixel identify / filter modes
		else if (mapState.mapMode === 'pixel') {
			// enable pixel layer event listener
			// @ts-expect-error __deck is dynamically defined
			map.__deck.setProps({
				onAfterRender: deckGLHandler.handler
			})

			// immediately try to retrieve pixel data if in pixel mode
			if (map.getZoom() >= minPixelLayerZoom) {
				map.once('idle', () => {
					getPixelData()
				})
			}
		} else if (mapState.mapMode === 'filter') {
			// disable pixel layer event listener
			// @ts-expect-error __deck is dynamically defined
			map.__deck.setProps({
				onAfterRender: () => {} // no-op
			})
		}

		map.setLayoutProperty('unit-fill', 'visibility', 'none')
		map.setLayoutProperty('unit-outline', 'visibility', 'none')
		// reset selected outline
		map.setFilter('unit-outline-highlight', ['==', 'id', Infinity])
		map.setLayoutProperty('blueprint', 'visibility', 'none')
		map.setLayoutProperty('protectedAreas', 'visibility', 'visible')
		map.setLayoutProperty('subregions', 'visibility', 'visible')

		if (mapState.mapMode === 'filter') {
			map.once('idle', () => {
				updateVisibleSubregions()
			})
		}

		setPixelLayerProps({
			visible: true,
			filterMode: mapState.filterMode,
			filters: mapState.activeFilterValues,
			// have to use opacity to hide so that pixel mode still works when hidden
			opacity: mapState.renderLayerIsVisible ? 0.7 : 0,
			// data prop is used to force loading of tiles if they aren't already loaded
			data: { visible: true }
		})

		updateMapIsDrawing()
	}

	const hideGulfOfMexico = () => {
		if (map === null) {
			return
		}
		// hide Gulf of Mexico
		if (map.style?._layers['marine-label-md-pt']) {
			map.setFilter('marine-label-md-pt', [
				'all',
				['==', '$type', 'Point'],
				['in', 'labelrank', 2, 3],
				['!=', 'name', 'Gulf of Mexico']
			])
		} else if (map.style?._layers['water-point-label']) {
			map.setFilter('water-point-label', [
				'all',
				[
					'match',
					['get', 'class'],
					// remove 'sea'; this category includes the gulf
					['ocean', 'reservoir', 'water'],
					true,
					false
				],
				['==', ['geometry-type'], 'Point']
			])
		}
	}

	const createMap = (mapNode: HTMLDivElement) => {
		const { bounds, maxBounds, minZoom, maxZoom } = config

		let center: LngLatLike
		let zoom

		const { center: urlCenter, zoom: urlZoom } = deserializeMapCenterZoomFromURL()

		if (urlCenter !== undefined) {
			center = urlCenter
			zoom = urlZoom
		} else {
			const boundsCenterZoom = getCenterAndZoom(mapNode, bounds, 0)
			center = boundsCenterZoom.center as LngLatLike
			zoom = boundsCenterZoom.zoom
		}

		map = new mapboxgl.Map({
			container: mapNode,
			accessToken: MAPBOX_TOKEN,
			style: 'mapbox://styles/mapbox/light-v9',
			center,
			zoom,
			minZoom,
			maxZoom,
			maxBounds,
			preserveDrawingBuffer: true
		})

		map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), 'top-right')
		map.dragRotate.disable()
		map.touchZoomRotate.disableRotation()

		window.map = map // for easier debugging and querying via console

		map.on('style.load', hideGulfOfMexico)

		map.on('load', () => {
			map._canvas.setAttribute(
				'aria-label',
				'interactive map showing Midwest Conservation Blueprint'
			)

			// add full extent button manually so it has proper tab order
			const button = document.createElement('button')
			button.onclick = zoomFullExtent
			button.title = 'zoom to full extent'
			button.tabIndex = 0
			button.classList = '!hidden md:!block'

			const span = document.createElement('span')
			span.classList = 'mapboxgl-ctrl-icon'
			// from @lucide/svelte/icons/home
			span.style =
				'background-image:url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9ImN1cnJlbnRDb2xvciIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiIGNsYXNzPSJsdWNpZGUgbHVjaWRlLWhvdXNlLWljb24gbHVjaWRlLWhvdXNlIj48cGF0aCBkPSJNMTUgMjF2LThhMSAxIDAgMCAwLTEtMWgtNGExIDEgMCAwIDAtMSAxdjgiLz48cGF0aCBkPSJNMyAxMGEyIDIgMCAwIDEgLjcwOS0xLjUyOGw3LTZhMiAyIDAgMCAxIDIuNTgyIDBsNyA2QTIgMiAwIDAgMSAyMSAxMHY5YTIgMiAwIDAgMS0yIDJINWEyIDIgMCAwIDEtMi0yeiIvPjwvc3ZnPg==);'
			button.appendChild(span)

			const container = document.querySelector('.mapboxgl-ctrl-top-right .mapboxgl-ctrl-group')
			container?.appendChild(button)

			// add sources
			Object.entries(sources).forEach(([id, source]) => {
				map.addSource(id, source as SourceSpecification)
			})

			// add DeckGL pixel layer
			// by default, renders the blueprint
			const deckGLOverlay = new MapboxOverlay({
				interleaved: true,

				layers: [
					new StackedPNGTileLayer({
						id: 'pixelLayers',
						// @ts-expect-error interleaved is fine
						interleaved: true,
						beforeId: beforeLayer,
						refinementStrategy: 'no-overlap',
						debounceTime: 10, // slightly debounce tile requests during major zoom / pan events
						layers: pixelLayers,
						extent: bounds,
						maxRequests: 20, // because these are on HTTP/2, we can fetch many at once
						opacity: 0.7,
						filterMode: mapState.filterMode,
						filters: mapState.activeFilterValues,
						visible: false,
						renderLayer: mapState.renderLayer,
						tileSize: 512,
						useWebGL2: true
					})
				]
			})
			map.addControl(deckGLOverlay)

			map.once('idle', () => {
				// update state once to trigger other components to update with map object
				isLoaded = true
			})

			// add normal mapbox layers// add layers
			layers.forEach((layer) => {
				// @ts-expect-error layer is valid
				map.addLayer(layer, beforeLayer)
			})

			// if map is initialized in pixel or filter mode
			if (mapState.mapMode === 'pixel' || mapState.mapMode === 'filter') {
				map.setLayoutProperty('unit-fill', 'visibility', 'none')
				map.setLayoutProperty('unit-outline', 'visibility', 'none')
				map.setLayoutProperty('blueprint', 'visibility', 'none')
				map.setLayoutProperty('protectedAreas', 'visibility', 'visible')
				map.setLayoutProperty('subregions', 'visibility', 'visible')

				map.once('idle', () => {
					setPixelLayerProps({
						visible: true,
						filterMode: mapState.filterMode,
						filters: mapState.activeFilterValues,
						data: { visible: true }
					})
					map.once('idle', () => {
						getPixelData()
					})
				})
			}

			// enable event listener for renderer
			if (mapState.mapMode === 'pixel') {
				// @ts-expect-error __deck is dynamically defined
				map.__deck.setProps({
					onAfterRender: deckGLHandler.handler
				})
			} else if (mapState.mapMode === 'filter') {
				map.once('idle', () => {
					updateVisibleSubregions()
				})
			}

			currentZoom = map.getZoom()

			map.on('move', () => {
				if (mapState.mapMode === 'pixel') {
					getPixelData()
				}
			})

			map.on('moveend', () => {
				serializeMapCenterZoomToURL(map)

				delayedMapIsDrawing = true
				if (mapState.mapMode === 'filter') {
					updateVisibleSubregions()
				}
				updateMapIsDrawing()
			})

			map.on('zoomend', () => {
				serializeMapCenterZoomToURL(map)

				if (mapState.mapMode === 'pixel') {
					getPixelData()
				} else if (mapState.mapMode === 'filter') {
					updateVisibleSubregions()
				}
				currentZoom = map.getZoom()
			})

			mapState.map = map
		})

		map.on('idle', () => {
			mapIsDrawing = false
			delayedMapIsDrawing = false
		})

		map.on('click', ({ lngLat: point }) => {
			if (mapState.mapMode === 'pixel') {
				return
			}

			const features = map.queryRenderedFeatures(map.project(point), {
				layers: ['unit-fill']
			})

			if (!(features && features.length > 0)) {
				mapState.setData(null)
				resizeMap()
				return
			}

			const { properties } = features[0]

			// highlight selected
			map.setFilter('unit-outline-highlight', ['==', 'id', properties!.id])

			// @ts-expect-error properties is fine
			mapState.setData(unpackFeatureData(properties, subregionIndex))
			resizeMap()
		})

		// Highlight units on mouseover
		map.on('mousemove', 'unit-fill', ({ features }) => {
			if (!map.isStyleLoaded()) {
				return
			}

			map.getCanvas().style.cursor = 'pointer'

			if (!(features && features.length > 0)) {
				return
			}

			const { id } = features[0] as { id: string | number }

			if (highlightId !== undefined && highlightId !== id) {
				map.setFeatureState(
					{ source: 'mapUnits', sourceLayer: 'units', id: highlightId },
					{ highlight: false }
				)
			}
			map.setFeatureState({ source: 'mapUnits', sourceLayer: 'units', id }, { highlight: true })
			highlightId = id
		})

		// Unhighlight all hover features on mouseout
		map.on('mouseout', () => {
			if (!map.isStyleLoaded()) {
				return
			}

			if (highlightId !== undefined) {
				map.setFeatureState(
					{ source: 'mapUnits', sourceLayer: 'units', id: highlightId },
					{ highlight: false }
				)
			}
			highlightId = undefined
		})

		// when this component is destroyed, remove the map
		return () => {
			map?.remove()
		}
	}

	const handleBasemapChange = (styleID: string) => {
		if (!(map && isLoaded)) {
			return
		}

		const updateStyle = () => {
			map!.setStyle(`mapbox://styles/mapbox/${styleID}`)

			map!.once('style.load', () => {
				hideGulfOfMexico()

				const {
					sources: styleSources,
					layers: styleLayers,
					// @ts-expect-error mapbox:origin is fine
					metadata: { 'mapbox:origin': curStyleId }
				} = map!.getStyle()
				const layerIndex = indexBy(styleLayers, 'id')

				if (curStyleId === 'satellite-streets-v11') {
					// make satellite a bit more washed out
					map!.setPaintProperty('background', 'background-color', '#FFF')
					map!.setPaintProperty('satellite', 'raster-opacity', 0.75)
				}

				// add sources back
				Object.entries(sources).forEach(([id, source]) => {
					// make sure we're not trying to reload the same style, which already has these
					if (!styleSources[id]) {
						// @ts-expect-error source is fine
						map!.addSource(id, source)
					}
				})

				// add regular layers and reapply filters / visibility
				layers.forEach((l) => {
					// make sure we're not trying to reload the same layers
					if (layerIndex[l.id]) {
						return
					}

					const layer = { ...l }

					if (mapState.mapMode !== 'unit') {
						if (l.id === 'blueprint' || l.id === 'unit-fill' || l.id === 'unit-outline') {
							layer.layout = {
								visibility: 'none'
							}
						}
						if (l.id === 'protectedAreas' || l.id === 'subregions') {
							layer.layout = {
								visibility: 'visible'
							}
						}
					} else {
						if (l.id === 'blueprint' && !mapState.renderLayerIsVisible) {
							layer.layout = {
								visibility: 'none'
							}
						}
						if (l.id === 'unit-outline-highlight' && mapState.data !== null) {
							// re-highlight selected layer
							layer.filter = ['==', 'id', mapState.data.id]
						}
					}

					// @ts-expect-error layer is fine
					map!.addLayer(layer, beforeLayer)
				})
			})
		}

		// wait for previous to finish loading, if necessary
		if (map.isStyleLoaded()) {
			updateStyle()
		} else {
			map.once('idle', updateStyle)
		}
	}

	// effect for changing renderLayer
	$effect(() => {
		// eslint-disable-next-line @typescript-eslint/no-unused-expressions
		mapState.renderLayer

		if (!untrack(() => isLoaded)) {
			return
		}

		setPixelLayerProps({ renderLayer: $state.snapshot(mapState.renderLayer) })
	})

	// effect for setting a location
	$effect(() => {
		// eslint-disable-next-line @typescript-eslint/no-unused-expressions
		locationData.location

		untrack(() => {
			if (!isLoaded) {
				return
			}

			if (locationData.location !== null) {
				const {
					location: { latitude, longitude }
				} = locationData
				map.jumpTo({ center: [longitude, latitude], zoom: 12 })
				map.once('idle', () => {
					updateVisibleSubregions()
				})

				if (!marker) {
					marker = new mapboxgl.Marker().setLngLat([longitude, latitude]).addTo(map)
				} else {
					marker?.setLngLat([longitude, latitude])
				}
			} else {
				marker?.remove()
				marker = null
			}
		})
	})

	// effect for updates to mapMode
	$effect(() => {
		// eslint-disable-next-line @typescript-eslint/no-unused-expressions
		mapState.mapMode

		if (!untrack(() => isLoaded)) {
			return
		}

		if (!map.isStyleLoaded()) {
			map.once('idle', () => {
				updateVisibleLayers()
			})

			// stop any transitions underway
			map.stop()

			return
		}

		// stop any transitions underway
		map.stop()

		updateVisibleLayers()
	})

	// effect for changed mapState to reset boundary highlight
	$effect(() => {
		/* eslint-disable @typescript-eslint/no-unused-expressions */
		mapState.mapMode
		mapState.data
		/* eslint-enable @typescript-eslint/no-unused-expressions */

		if (!untrack(() => isLoaded)) {
			return
		}

		if (mapState.mapMode === 'unit' && mapState.data === null) {
			map.setFilter('unit-outline-highlight', ['==', 'id', Infinity])
		}
	})

	// effect for update to filters
	$effect(() => {
		// NOTE: have to specifically mark activeFilterValues to trigger this effect
		/* eslint-disable @typescript-eslint/no-unused-expressions */
		mapState.filterMode
		mapState.activeFilterValues
		/* eslint-enable @typescript-eslint/no-unused-expressions */

		if (!untrack(() => isLoaded)) {
			return
		}

		setPixelLayerProps({ filterMode: mapState.filterMode, filters: mapState.activeFilterValues })
	})

	// effect for update to renderLayerIsVisible
	$effect(() => {
		// eslint-disable-next-line @typescript-eslint/no-unused-expressions
		mapState.renderLayerIsVisible
		// NOTE: we intentionally do not track mapMode here but use in untrack

		untrack(() => {
			if (!isLoaded) {
				return
			}

			if (mapState.mapMode === 'unit') {
				map.setLayoutProperty(
					'blueprint',
					'visibility',
					mapState.renderLayerIsVisible ? 'visible' : 'none'
				)
			} else {
				// have to toggle opacity not visibility so that pixel-level identify
				// still works
				setPixelLayerProps({ opacity: mapState.renderLayerIsVisible ? 0.7 : 0 })
			}
		})
	})

	const belowMinZoom = $derived(
		mapState.mapMode === 'pixel'
			? currentZoom < minPixelLayerZoom
			: currentZoom < (minSummaryZoom || 0)
	)

	const zoomFullExtent = () => {
		map.fitBounds(config.bounds, { padding: 100 })
	}
</script>

<div
	class="h-full w-full flex-auto relative md:border-l-2 border-l-grey-2 has-focus-visible:border-l-primary overflow-hidden print:hidden"
>
	<div class="h-full w-full print:hidden" {@attach createMap}></div>

	{#if mapIsDrawing}
		<div
			class="absolute left-0 top-0 bottom-0 right-0 bg-grey-0/50 flex justify-center items-center"
		>
			<Spinner class="size-6 animate-spin" />
		</div>
	{:else if mapState.mapMode === 'pixel' && currentZoom >= minPixelLayerZoom}
		<img
			src={CrosshairsIcon}
			alt="Crosshairs icon"
			class="absolute block z-0 right-0 bottom-0 left-[50%] top-[50%] -ml-4 -mt-4 pointer-events-none size-8 print:hidden"
		/>
	{/if}

	{#if isLoaded}
		<ModeToggle {belowMinZoom} />
		<FindLocation />
		<StyleToggle onChange={handleBasemapChange} />
		<LayerToggle />
		<Legend />
	{/if}
</div>
