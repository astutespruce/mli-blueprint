// import { Texture2D } from '@luma.gl/webgl'
import { Device, Texture } from '@luma.gl/core'
import { DynamicTexture } from '@luma.gl/engine'
import type { ImageType } from '@loaders.gl/loader-utils'

/**
 * Convert hex string to RGBA array
 * Only 6 character form is supported
 * @param {String} hex
 */
const hexToRGBA = (hex: string | null) => {
	if (hex === null) {
		return [0, 0, 0, 0]
	}

	if (hex.length === 9) {
		return [
			parseInt(`0x${hex[1]}${hex[2]}`, 16),
			parseInt(`0x${hex[3]}${hex[4]}`, 16),
			parseInt(`0x${hex[5]}${hex[6]}`, 16),
			parseInt(`0x${hex[7]}${hex[8]}`, 16)
		]
	}
	return [
		parseInt(`0x${hex[1]}${hex[2]}`, 16),
		parseInt(`0x${hex[3]}${hex[4]}`, 16),
		parseInt(`0x${hex[5]}${hex[6]}`, 16),
		255
	]
}

/**
 * Create a flattened palette of RGBA values based on hex colors
 * @param {*} colors
 * @returns Uint8Array of RGBA data
 */
const makeRGBAPalette = (colors: (string | null)[]) => {
	const palette: number[] = []
	colors.forEach((c) => {
		palette.push(...hexToRGBA(c))
	})
	return new Uint8Array(palette)
}

/**
 * Create a WebGL texture from an array of hex colors
 * values
 */
export const createPaletteTexture = (device: Device, colors: string[]): Texture => {
	// IMPORTANT: palette must always include as its first entry a color for nodata
	const palette = makeRGBAPalette([
		null, // nodata value
		...colors
	])
	const texture = device.createTexture({
		data: palette,
		width: palette.length / 4,
		height: 1,
		format: 'rgba8unorm',
		sampler: {
			minFilter: 'nearest',
			magFilter: 'nearest',
			addressModeU: 'clamp-to-edge',
			addressModeV: 'clamp-to-edge'
		}
	})

	return texture
}

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
