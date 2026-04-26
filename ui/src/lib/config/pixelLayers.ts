import { indexBy } from '$lib/util/data'
import type {
	Indicator,
	PixelLayerBounds,
	PixelLayerEncodings,
	PixelLayerIndex,
	PixelLayer
} from '$lib/types'

import {
	blueprint,
	blueprintCategories,
	indicatorsIndex,
	protectedAreas,
	urban,
	pixelLayers0,
	pixelLayers1,
	pixelLayers2,
	pixelLayers3,
	pixelLayers4,
	indicatorGroups
} from './constants'

import { tileHost } from './map'

const pixelLayerEncoding: PixelLayerEncodings = {
	0: pixelLayers0,
	1: pixelLayers1,
	2: pixelLayers2,
	3: pixelLayers3,
	4: pixelLayers4
}

// this is copy-pasted from bounds reported by the tile services
const pixelLayerBounds: PixelLayerBounds = {
	0: [-105.69088, 35.4594, -78.63988, 49.53074],
	1: [-105.69088, 35.4594, -78.63988, 49.53074],
	2: [-105.69088, 35.4594, -78.63988, 49.53074],
	3: [-105.69088, 35.4594, -78.63988, 49.53074],
	4: [-92.16659, 41.0852, -79.24692, 48.32932]
}

const pixelLayerSourceConfig = { tileSize: 512, minzoom: 3, maxzoom: 14 }

export const pixelLayers = [...Array(5).keys()].map((i) => ({
	...pixelLayerSourceConfig,
	id: `pixels${i}`,
	url: `${tileHost}/services/midwest_pixel_layers_${i}/tiles/{z}/{x}/{y}.png`,
	bounds: pixelLayerBounds[i],
	encoding: pixelLayerEncoding[i]
}))

// create index of encoded layers
export const pixelLayerIndex: PixelLayerIndex = {}
pixelLayers.forEach(({ encoding }, textureIndex) => {
	encoding.forEach(({ id, bits, offset, valueShift }) => {
		pixelLayerIndex[id] = { textureIndex, bits, offset, valueShift }
	})
})

const coreLayers: PixelLayer[] = [
	{
		id: 'blueprint',
		label: 'Blueprint priority',
		// valueLabel: 'for a connected network of lands and waters', // used in legend
		// sort colors in ascending value; blueprint is in descending order
		colors: blueprint.map(({ color, value }) => (value === 0 ? null : color)).reverse(),
		categories: blueprintCategories,
		layer: pixelLayerIndex.blueprint
	}
]

const otherInfoLayers: PixelLayer[] = [
	{
		id: 'urban',
		label: 'Probability of urbanization by 2060',
		colors: urban.map(({ color }) => color),
		categories: urban.map(({ color, ...rest }) => ({
			...rest,
			color: color || '#FFFFFF',
			outlineWidth: 1,
			outlineColor: 'grey.5'
		})),
		layer: pixelLayerIndex.urban
	},
	{
		id: 'protectedAreas',
		label: 'Protected areas',
		colors: protectedAreas.map(({ color }) => color),
		categories: protectedAreas.filter(({ color }) => color !== null),
		layer: pixelLayerIndex.protectedAreas
	}
]

const layers = coreLayers.concat(otherInfoLayers)

export const renderLayerGroups = [
	{
		id: 'core',
		label: 'Priorities',
		layers: coreLayers
	}
]

indicatorGroups.forEach(({ id: groupId, label: groupLabel, indicators: groupIndicators }) => {
	const group = {
		id: groupId,
		label: `${groupLabel} indicators`,
		layers: groupIndicators.map((id) => {
			const { label, values, valueLabel } = indicatorsIndex[id] as Indicator
			return {
				id,
				label,
				colors: values.map(({ color }) => color),
				categories: values.filter(({ color }) => color !== null).reverse(),
				valueLabel,
				layer: pixelLayerIndex[id]
			}
		})
	}

	renderLayerGroups.push(group)
	layers.push(...group.layers)
})

renderLayerGroups.push({
	id: 'otherInfo',
	label: 'More information',
	layers: otherInfoLayers
})

export const renderLayersIndex = indexBy(layers, 'id')
