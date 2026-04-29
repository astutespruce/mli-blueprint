import { DynamicTexture } from '@luma.gl/engine'
import type { Map, Point, Layer, LngLatLike } from 'mapbox-gl'

import { indexBy, setIntersection, sum } from '$lib/util/data'
import type { IndicatorValue } from '$lib/types'

const TILE_SIZE = 512 // physical tile size (layer tile size may be set differently to increase resolution)

const getTileID = (
	zoom: number,
	mercX: number,
	mercY: number,
	minZoom: number,
	maxZoom: number,
	tileSize: number
) => {
	// zoom adapted from: https://github.com/visgl/deck.gl/blob/8.7-release/modules/geo-layers/src/tile-layer/utils.js::getTileIndices
	let z = Math.round(zoom + Math.log2(TILE_SIZE / tileSize))

	// clip to [minZoom, maxZoom]
	if (Number.isFinite(minZoom) && z < minZoom) {
		z = minZoom
	} else if (Number.isFinite(maxZoom) && z > maxZoom) {
		z = maxZoom
	}

	const numTilesAtZoom = 1 << z
	return {
		z,
		x: Math.floor(mercX * numTilesAtZoom),
		y: Math.floor(mercY * numTilesAtZoom)
	}
}

const getTile = (map: Map, screenPoint: Point) => {
	// resolve the StackedPNGTileLayer; layers[1:n] are StackedPNGLayers
	// @ts-expect-error map.__deck is dynamically defined
	const tileLayer = map.__deck.layerManager.layers[0]
	const {
		props: { minZoom, maxZoom, tileSize },
		state: { tileset }
	} = tileLayer

	// calculate tile containing point
	const { x: mercX, y: mercY } = map.transform.pointCoordinate(screenPoint)
	const tileID = getTileID(map.getZoom(), mercX, mercY, minZoom, maxZoom, tileSize)

	// rescale Mercator coordinates to tile coords
	const scale = (2 ** tileID.z * tileSize) / tileSize
	const offsetX = Math.floor((mercX * scale - tileID.x) * TILE_SIZE)
	const offsetY = Math.floor((mercY * scale - tileID.y) * TILE_SIZE)

	const { z: searchZ, x: searchX, y: searchY } = tileID

	// tileset.selectedTiles  contain all tiles at current zoom level
	const [tile] = tileset.selectedTiles.filter(
		({ index: { z, x, y } }: { index: { z: number; x: number; y: number } }) =>
			z === searchZ && x === searchX && y === searchY
	)
	return {
		tile: tile || null,
		offsetX,
		offsetY
	}
}

const extractIndicators = (data, indicatorGroupInfo, indicatorInfo, subregions: Set<string>) => {
	const indicatorGroupIndex = indexBy(indicatorGroupInfo, 'id')

	// only show indicators that are either present or likely present based on
	// subregion
	let indicators = indicatorInfo
		.filter(({ id, subregions: indicatorSubregions }: { id: string; subregions: Set<string> }) => {
			const present = data[id] !== undefined && data[id] !== null
			return present || setIntersection(indicatorSubregions, subregions).size > 0
		})
		.map(({ id, values: valuesInfo, ...indicator }: { id: string; values: IndicatorValue[] }) => {
			const present = data[id] !== undefined && data[id] !== null

			const values = valuesInfo.map(({ value, ...rest }) => ({
				...rest,
				value,
				percent: data[id] === value ? 100 : 0
			}))

			return {
				...indicator,
				id,
				values,
				total: present ? 100 : 0,
				group: indicatorGroupIndex[id.split('_')[0]]
			}
		})

	// aggregate these up by indicator group for indicator groups that are present
	const indicatorGroupsPresent = new Set(
		indicators
			.filter(
				({ values }: { values: [{ percent: number }] }) =>
					sum(values.map(({ percent }: { percent: number }) => percent)) > 0
			)
			.map(({ group: { id } }: { group: { id: string } }) => id)
	)

	indicators = indexBy(indicators, 'id')

	const indicatorGroups = indicatorGroupInfo
		.filter(({ id }: { id: string }) => indicatorGroupsPresent.has(id))
		.map(
			({
				id: groupId,
				label,
				color,
				borderColor,
				indicators: groupIndicators,
				...rest
			}: {
				id: string
				label: string
				color: string
				borderColor: string
				indicators: string[]
			}) => {
				const indicatorsPresent = groupIndicators.filter((indicatorId) => indicators[indicatorId])

				return {
					...rest,
					id: groupId,
					label,
					color,
					borderColor,
					indicators: indicatorsPresent.map((indicatorId) => ({
						...indicators[indicatorId]
					}))
				}
			}
		)

	return { indicatorGroups, indicators }
}

export const extractPixelData = async (
	map: Map,
	point: LngLatLike,
	indicatorGroupInfo,
	indicatorInfo
) => {
	const screenPoint = map.project(point)

	const { tile, offsetX, offsetY } = getTile(map, screenPoint)

	if (!(tile && tile.data && tile.data.images)) {
		// console.debug('no tile available')
		// Note: this is a special case because it happens while map is still loading
		// and tileset claims it is loaded, but for the wrong zoom levels
		return null
	}

	// images are at tile.data.images
	const {
		data: { images }
	} = tile

	// read each texture at the offset; each 4 bytes corresponds
	// to the R,G,B,A values of a given tile
	const pixels = await Promise.all(
		images.map(async (image: DynamicTexture) => {
			if (image.props.width > 1 && image.props.height > 1) {
				const buffer = await image.readAsync({
					width: 1,
					height: 1,
					x: offsetX,
					y: offsetY
				})

				return [...new Uint8Array(buffer)]
			}
			return [0, 0, 0, 0]
		})
	)

	// ignore alpha values
	const pixelValues = pixels.map(([r, g, b]: [number, number, number]) => (r << 16) | (g << 8) | b)

	// decode pixel values
	// @ts-expect-error props is dynamically defined
	const layers = map.__deck.layerManager.layers[0].props.layers

	const data = {}

	// layers will be empty array if there are no tiles for any of the pixel layers
	layers.forEach(({ encoding }, i) => {
		const pixelValue = pixelValues[i]
		if (pixelValue === 0) {
			// console.debug('pixel value is 0')
			// if entire pixel is 0 (NODATA), it can be ignored
			return
		}

		encoding.forEach(
			({
				id,
				offset,
				bits,
				valueShift = 0
			}: {
				id: string
				offset: number
				bits: number
				valueShift: number
			}) => {
				let value = (pixelValue >> offset) & (2 ** bits - 1)
				// if value is 0, it is NODATA
				if (value > 0) {
					value -= valueShift
					data[id] = value
				}
			}
		)
	})

	// if data is empty, then pixel is is outside blueprint area
	if (Object.keys(data).length === 0) {
		return {}
	}

	// extract info from feature data
	const features = map.queryRenderedFeatures(screenPoint, {
		layers: ['protectedAreas', 'subregions']
	})

	// @ts-expect-error subregion is an expected property
	const [{ properties: { subregion } } = { properties: {} }] = features.filter(
		// @ts-expect-error id is an expected field of layer
		({ layer: { id } }) => id === 'subregions'
	)

	const subregions = new Set([subregion])

	// unpack indicators and indicator groups
	data.indicators = extractIndicators(data, indicatorGroupInfo, indicatorInfo, subregions)

	// extract protected areas from vector tiles
	const protectedAreasList: string[] = []
	// @ts-expect-error id is an expected field of layer
	const protectedAreasFeatures = features.filter(({ layer: { id } }) => id === 'protectedAreas')
	if (protectedAreasFeatures.length > 0) {
		// @ts-expect-error name and owner are expected properties
		protectedAreasFeatures.forEach(({ properties: { name, owner } }) => {
			if (owner) {
				protectedAreasList.push(`${name} (${owner})`)
			} else {
				protectedAreasList.push(name)
			}
		})
	}

	return {
		subregions,
		outsideExtentPercent: 0,
		...data,
		protectedAreasList,
		numProtectedAreas: protectedAreasList.length
	}
}
