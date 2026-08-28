// import { Texture2D } from '@luma.gl/webgl'
import { Device } from '@luma.gl/core'
import { DynamicTexture } from '@luma.gl/engine'
import type { ImageType } from '@loaders.gl/loader-utils'

/**
 * Create a texture from a PNG image data
 */
export const createPNGTexture = (device: Device, data: ImageType | null): DynamicTexture => {
	const { width = 1, height = 1 } = data || {}

	const texture = new DynamicTexture(device, {
		data,
		width,
		height,
		format: 'rgba8unorm',
		dimension: '2d',
		sampler: {
			minFilter: 'nearest',
			magFilter: 'nearest',
			addressModeU: 'clamp-to-edge',
			addressModeV: 'clamp-to-edge'
		}
	})

	return texture
}
