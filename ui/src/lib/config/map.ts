import { browser } from '$app/environment'
import { TILE_HOST } from '$lib/env'
import type { MapConfig } from '$lib/types'

export let tileHost = TILE_HOST

if (browser && !tileHost) {
	tileHost = `//${window.location.host}`
}

export const mapConfig: MapConfig = {
	// idealized bounds to be able to show legend in bottom right
	bounds: [-104.43574526673385, 31.819214112014564, -79.24672371745189, 50.81116573333625],
	maxBounds: [-180, -80, 180, 80],
	minZoom: 3,
	maxZoom: 14
}

export const sources = {
	blueprint: {
		type: 'raster',
		// tiles are at 512, but using 256 forces higher resolution
		tileSize: 256,
		minzoom: 3,
		maxzoom: 14,
		bounds: [-105.69088, 35.4594, -78.63988, 49.53074],
		tiles: [`${tileHost}/services/midwest_blueprint/tiles/{z}/{x}/{y}.png`]
	},
	mapUnits: {
		type: 'vector',
		minzoom: 3,
		maxzoom: 14,
		bounds: [-104.459724, 35.790944, -80.330658, 49.796336],
		tiles: [`${tileHost}/services/midwest_map_units/tiles/{z}/{x}/{y}.pbf`],
		// note: can use promoteId: 'id' to promote feature properties ID to feature ID
		promoteId: 'id'
	},
	pixelFeatures: {
		type: 'vector',
		minzoom: 3,
		maxzoom: 14,
		bounds: [-104.07486, 35.995647, -80.516052, 49.385949],
		tiles: [`${tileHost}/services/midwest_other_features/tiles/{z}/{x}/{y}.pbf`]
	}
}

export const layers = [
	// protected areas and subregions are added with no fill in order to detect features in pixel mode
	{
		id: 'protectedAreas',
		source: 'pixelFeatures',
		'source-layer': 'protectedAreas',
		type: 'fill',
		minzoom: 5,
		layout: {
			visibility: 'none'
		},
		paint: {
			'fill-color': '#FFF',
			'fill-opacity': 0
		}
	},
	{
		id: 'subregions',
		source: 'pixelFeatures',
		'source-layer': 'subregions',
		type: 'fill',
		minzoom: 3,
		layout: {
			visibility: 'none'
		},
		paint: {
			'fill-color': '#FFF',
			'fill-opacity': 0
		}
	},
	{
		id: 'blueprint',
		source: 'blueprint',
		type: 'raster',
		minzoom: 3,
		paint: {
			'raster-opacity': 0.7
		}
	},
	{
		id: 'midwest-boundary-outline',
		source: 'mapUnits',
		'source-layer': 'boundary',
		minzoom: 3,
		maxzoom: 14,
		type: 'line',
		paint: {
			'line-color': '#000',
			'line-width': {
				stops: [
					[6, 1],
					[8, 0.1]
				]
			}
		}
	},

	{
		id: 'unit-fill',
		source: 'mapUnits',
		'source-layer': 'units',
		minzoom: 8,
		type: 'fill',
		paint: {
			'fill-color': '#0892D0',
			'fill-opacity': ['case', ['boolean', ['feature-state', 'highlight'], false], 0.3, 0]
		}
	},
	{
		id: 'unit-outline',
		source: 'mapUnits',
		'source-layer': 'units',
		minzoom: 8,
		type: 'line',
		paint: {
			'line-opacity': 1,
			'line-color': '#000',
			'line-width': ['interpolate', ['linear'], ['zoom'], 8, 0.25, 10, 1, 13, 4]
		}
	},
	{
		id: 'unit-outline-highlight',
		source: 'mapUnits',
		'source-layer': 'units',
		type: 'line',
		filter: ['==', 'id', Infinity],
		paint: {
			'line-opacity': 1,
			'line-color': '#000000',
			'line-width': {
				stops: [
					[8, 3],
					[12, 6]
				]
			}
		}
	}
]
