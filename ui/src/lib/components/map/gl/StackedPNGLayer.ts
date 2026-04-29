// Adapted from: https://github.com/visgl/deck.gl/blob/master/modules/layers/src/bitmap-layer/bitmap-layer.ts

import { Layer, project32 } from '@deck.gl/core'
import { Model } from '@luma.gl/engine'
import type { ShaderModule } from '@luma.gl/shadertools'
import { DynamicTexture } from '@luma.gl/engine'

import { pixelLayers } from '$lib/config/pixelLayers'
import { sum } from '$lib/util/data'

import createMesh from './mesh'

const numLayers = sum(pixelLayers.map((l) => l.encoding.length))

// NOTE: textures are defined directly in the shader and referenced here;
// they are not included in the uniform block but they are referenced in the
// uniform props below
const stackedPNGLayerUniformBlock = `\
layout(std140) uniform stackedPNGLayerUniforms {
	uniform float opacity;
	uniform int textureIndex;
	uniform int offset;
	uniform int bits;
	// encoded filters, with a bit set to 1 for each value that is present in the
	// set of activated filters.  -1 indicates no filtering for that layer.
	uniform int filterValues[${numLayers}];
} stackedPNGLayer;
`

type StackedPNGLayerUniformProps = {
	opacity?: number
	textureIndex?: number
	offset?: number
	bits?: number
	filterValues?: number[]
	palette?: DynamicTexture
	layer0?: DynamicTexture
	layer1?: DynamicTexture
	layer2?: DynamicTexture
	layer3?: DynamicTexture
	layer4?: DynamicTexture
}

const stackedPNGLayerUniforms = {
	name: 'stackedPNGLayer',
	fs: stackedPNGLayerUniformBlock,
	uniformTypes: {
		opacity: 'f32',
		textureIndex: 'i32',
		offset: 'i32',
		bits: 'i32',
		// @ts-expect-error filterValues is valid
		filterValues: ['i32', numLayers]
	}
} as const satisfies ShaderModule<StackedPNGLayerUniformProps>

type StackedPNGLayerProps = {
	bounds?: [number, number, number, number]
	images?: DynamicTexture[]
	renderTarget?: {
		id: string
		layer: {
			textureIndex: number
			offset: number
			bits: number
		}
		palette: DynamicTexture
	}
	filterValues?: number[]
	opacity?: number
}

class StackedPNGLayer extends Layer {
	static layerName = 'StackedPNGLayer'

	static defaultProps = {
		_imageCoordinateSystem: 'default',
		textureParameters: { type: 'object', ignore: true, value: null }
	}

	initializeState() {
		const attributeManager = this.getAttributeManager()
		attributeManager!.remove(['instancePickingColors'])
		const noAlloc = true

		attributeManager!.add({
			indices: {
				size: 1,
				isIndexed: true,
				update: (attribute) => {
					// @ts-expect-error indices is valid
					attribute.value = this.state!.mesh!.indices
				},
				noAlloc
			},
			positions: {
				size: 3,
				type: 'float64',
				fp64: this.use64bitPositions(),
				update: (attribute) => {
					// @ts-expect-error indices is valid
					attribute.value = this!.state!.mesh!.positions
				},
				noAlloc
			},
			texCoords: {
				size: 2,
				update: (attribute) => {
					// @ts-expect-error indices is valid
					attribute.value = this!.state!.mesh!.texCoords
				},
				noAlloc
			}
		})

		const {
			id,
			// @ts-expect-error shaders is valid
			shaders: { vs, fs }
		} = this.props

		this.state.model = new Model(this.context.device, {
			id,
			vs,
			fs,
			modules: [project32, stackedPNGLayerUniforms],
			bufferLayout: this.getAttributeManager()!.getBufferLayouts(),
			topology: 'triangle-list',
			isInstanced: false,
			vertexCount: 6
		}) as Model
	}

	updateState({
		props: { bounds, images = [], renderTarget, filterValues, opacity },
		oldProps: {
			bounds: oldBounds,
			images: oldImages = [],
			// @ts-expect-error oldRenderTarget is intentionally missing props
			renderTarget: oldRenderTarget = {},
			filterValues: oldFilterValues,
			opacity: oldOpacity
		}
	}: {
		props: StackedPNGLayerProps
		oldProps: StackedPNGLayerProps
	}) {
		if (bounds && bounds.length === 4 && bounds !== oldBounds) {
			const oldMesh = this.state.mesh

			const normalizedBounds = [
				[bounds[0], bounds[1]],
				[bounds[0], bounds[3]],
				[bounds[2], bounds[3]],
				[bounds[2], bounds[1]]
			]
			const mesh = createMesh(normalizedBounds, this.context.viewport.resolution)

			Object.keys(mesh).forEach((key) => {
				if (oldMesh && oldMesh[key as keyof typeof oldMesh] !== mesh[key as keyof typeof mesh]) {
					this.getAttributeManager()!.invalidate(key)
				}
			})

			this.setState({
				mesh,
				coordinateConversion: 0,
				bounds: [0, 0, 0, 0]
			})
		}

		let newProps: StackedPNGLayerUniformProps = {}

		if (images !== oldImages && images.length > 0 && images.every((item) => item)) {
			newProps = {
				...newProps,
				...Object.fromEntries(images.map((image, i) => [`layer${i}`, image]))
			}
		}

		if (renderTarget && renderTarget.layer && renderTarget.id !== oldRenderTarget.id) {
			newProps = {
				...newProps,
				textureIndex: renderTarget.layer.textureIndex,
				offset: renderTarget.layer.offset,
				bits: renderTarget.layer.bits,
				palette: renderTarget.palette
			}
		}

		if (
			filterValues &&
			(!oldFilterValues || !filterValues.every((v: number, i: number) => v === oldFilterValues[i]))
		) {
			newProps.filterValues = filterValues
		}
		if (opacity !== oldOpacity) {
			newProps.opacity = opacity
		}

		if (Object.keys(newProps).length > 0) {
			// @ts-expect-error shaderInputs is valid
			this.state.model.shaderInputs.setProps({ stackedPNGLayer: newProps })
		}
	}

	draw() {
		const { model } = this.state
		const { images } = this.props as StackedPNGLayerProps

		if (!model || !images || images.length === 0 || !images.every((item) => item)) {
			return
		}

		// @ts-expect-error model.draw is valid
		model.draw(this.context.renderPass)
	}

	finalizeState() {
		// @ts-expect-error finalizeState is valid
		super.finalizeState()

		const { images } = this.props as StackedPNGLayerProps

		// clear images to release memory
		if (images && images.length) {
			images.forEach((image) => {
				image.destroy()
			})
		}
	}
}

export default StackedPNGLayer
