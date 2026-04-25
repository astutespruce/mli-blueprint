// import { Texture2D } from '@luma.gl/webgl'
import { GL } from '@luma.gl/constants'

/**
 * Convert hex string to RGBA array
 * Only 6 character form is supported
 * @param {String} hex
 */
const hexToRGBA = (hex) => {
  if (hex === null) {
    return [0, 0, 0, 0]
  }

  if (hex.length === 9) {
    return [
      parseInt(`0x${hex[1]}${hex[2]}`, 16),
      parseInt(`0x${hex[3]}${hex[4]}`, 16),
      parseInt(`0x${hex[5]}${hex[6]}`, 16),
      parseInt(`0x${hex[7]}${hex[8]}`, 16),
    ]
  }
  return [
    parseInt(`0x${hex[1]}${hex[2]}`, 16),
    parseInt(`0x${hex[3]}${hex[4]}`, 16),
    parseInt(`0x${hex[5]}${hex[6]}`, 16),
    255,
  ]
}

/**
 * Create a flattened palette of RGBA values based on hex colors
 * @param {*} colors
 * @returns Uint8Array of RGBA data
 */
const makeRGBAPalette = (colors) => {
  const palette = []
  colors.forEach((c) => {
    palette.push(...hexToRGBA(c))
  })
  return new Uint8Array(palette)
}

/**
 * Create a WebGL texture from an array of hex colors
 * values
 * @param {*} device - WebGL device
 * @param {Array} colors - array of hex colors
 * @returns WebGL texture
 */
export const createPaletteTexture = (device, colors) => {
  // IMPORTANT: palette must always include as its first entry a color for nodata
  const palette = makeRGBAPalette([
    null, // nodata value
    ...colors,
  ])
  return device.createTexture({
    data: palette,
    width: palette.length / 4,
    height: 1,
    format: 'rgba8unorm',
    dataFormat: GL.RGBA,
    type: GL.UNSIGNED_BYTE,
    sampler: {
      minFilter: 'nearest',
      magFilter: 'nearest',
      addressModeU: 'clamp-to-edge',
      addressModeV: 'clamp-to-edge',
    },
    mipmaps: false,
  })
}

/**
 * Create a texture from a PNG image data
 * @param {*} device - WebGL device
 * @param {*} data - PNG data or null
 * @returns WebGL texture
 */
export const createPNGTexture = (device, data) =>
  device.createTexture({
    data,
    format: 'rgba8unorm',
    dataFormat: GL.RGBA,
    type: GL.UNSIGNED_BYTE,
    sampler: {
      minFilter: 'nearest',
      magFilter: 'nearest',
      addressModeU: 'clamp-to-edge',
      addressModeV: 'clamp-to-edge',
    },
    mipmaps: false,
  })
