import { TileLayer, _getURLFromTemplate } from '@deck.gl/geo-layers'
import { load } from '@loaders.gl/core'
import { ImageLoader } from '@loaders.gl/images'
import { Device } from '@luma.gl/core'
import { dequal as deepEqual } from 'dequal'

// have to use the raw loader to load shaders
import vertexShader from './vertex.vs?raw'
import fragmentShader from './fragment.fs?raw'

import { getFilterExpr, getFilterValues } from './filters'
import StackedPNGLayer from './StackedPNGLayer'
import { createPNGTexture, createPaletteTexture } from './texture'

/**
 * Fetch a tile image asynchronously and load into a GL texture
 */
const fetchImage = async (device: Device, url: string, signal: any, skip = false) => {
	const data = skip
		? null
		: await load(url, ImageLoader, {
				image: { type: 'imagebitmap' },
				fetch: { signal }
			})

	// always create a texture, which can be empty if there is no data
	return createPNGTexture(device, data)
}

/**
 * StackedPNGTileLayer provides a tile-loading interface that wraps
 * StackedPNGLayer instances (one per tile).
 */
export default class StackedPNGTileLayer extends TileLayer {
	initializeState() {
		super.initializeState()

		const { device } = this.context
		// @ts-expect-error props defined dynamically
		const { layers, filters, renderLayer } = this.props
		const encodingSchemes = layers.map(({ encoding }) => encoding)

		this.setState({
			tileset: null,
			isLoaded: false,
			shaders: {
				vs: vertexShader,
				fs: fragmentShader.replace('// <FILTER_EXPR>', getFilterExpr(encodingSchemes))
			},
			// following variables change over time and are updated via updateState
			filterValues: getFilterValues(
				layers.map(({ encoding }) => encoding),
				filters || {}
			),
			renderTarget: {
				...renderLayer,
				palette: createPaletteTexture(device, renderLayer.colors)
			}
		})
	}

	updateState(props) {
		super.updateState(props)

		const newState = {}
		const {
			props: { layers, renderLayer: newRenderLayer, filters: newFilters = null },
			oldProps: { renderLayer: oldRenderLayer, filters: oldFilters = null }
		} = props

		// only update filters when they've changed
		if (!deepEqual(oldFilters, newFilters)) {
			newState.filterValues = getFilterValues(
				layers.map(({ encoding }) => encoding),
				newFilters || {}
			)
		}

		// only update render target when these are different
		if (oldRenderLayer && newRenderLayer.id !== oldRenderLayer.id) {
			const { device } = this.context
			newState.renderTarget = {
				...newRenderLayer,
				palette: createPaletteTexture(device, newRenderLayer.colors)
			}
		}

		if (Object.keys(newState).length > 0) {
			this.setState(newState)
		}
	}

	async getTileData(tile) {
		// prevent fetching tiles if layer is not visible
		if (!this.props.visible) {
			return { images: null }
		}

		const {
			bbox: { west, south, east, north },
			signal
		} = tile

		const imageRequests = this.props.layers.map(({ url, bounds: [xmin, ymin, xmax, ymax] }) => {
			// intersect tile bounds and layer bounds and skip if no overlap
			const skip = west > xmax || east < xmin || south > ymax || north < ymin
			return fetchImage(this.context.device, _getURLFromTemplate(url, tile), signal, skip)
		})

		const images = await Promise.all(imageRequests)

		return { images }
	}

	renderLayers() {
		// prescreen to make sure all visible tiles are loaded before having them render
		const allLoaded = this.state.tileset.tiles
			.filter((tile) => this.state.tileset.isTileVisible(tile))
			.every((tile) => tile.isLoaded)

		return this.state.tileset.tiles.map((tile) => {
			if (!allLoaded) {
				// nothing to show until all are loaded, but have to return existing layers
				// for existing tiles
				return tile.layers
			}

			const subLayerProps = this.getSubLayerPropsByTile(tile)
			if (!tile.isLoaded && !tile.content) {
				// nothing to show
			} else if (!tile.layers) {
				// cache the rendered layer in the tile
				const layer = this.renderSubLayers({
					...this.props,
					...this.getSubLayerProps({
						id: tile.id,
						updateTriggers: this.props.updateTriggers
					}),
					data: tile.content,
					_offset: 0,
					tile
				})
				if (layer) {
					tile.layers = [layer.clone({ tile, ...subLayerProps })]
				} else {
					tile.layers = []
				}
			} else if (
				subLayerProps &&
				tile.layers[0] &&
				Object.keys(subLayerProps).some(
					(propName) => tile.layers[0].props[propName] !== subLayerProps[propName]
				)
			) {
				tile.layers = tile.layers.map((layer) => layer.clone(subLayerProps))
			}
			return tile.layers
		})
	}

	// @ts-expect-error use of props here is OK
	renderSubLayers(props) {
		if (!props.visible) {
			return null
		}

		// @ts-expect-error these state fields are defined dynamically
		const { shaders, renderTarget, filterValues } = this.state

		const {
			tile: { boundingBox },
			data: { images } = {}
		} = props

		if (images === null) {
			return null
		}

		return new StackedPNGLayer(props, {
			// @ts-expect-error shaders are valid
			shaders,
			bounds: [boundingBox[0][0], boundingBox[0][1], boundingBox[1][0], boundingBox[1][1]],
			images,
			filterValues,
			renderTarget
		})
	}
}

StackedPNGTileLayer.layerName = 'StackedPNGTileLayer'
StackedPNGTileLayer.defaultProps = {
	...TileLayer.defaultProps,
	filters: null,
	pickable: false
}
