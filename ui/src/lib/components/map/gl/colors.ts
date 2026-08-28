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
 * Create a flat list of float32 color values (4 entries per color)
 * @param colors Array of hex colors
 * @returns Float32 array
 */
export const makeRGBAFloat32Palette = (colors: (string | null)[]): Float32Array => {
	const palette: number[] = []
	colors.forEach((c) => {
		palette.push(...hexToRGBA(c).map((c) => c / 255.0))
	})
	return new Float32Array(palette)
}
