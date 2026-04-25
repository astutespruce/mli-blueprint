// Adapted from: https://github.com/visgl/deck.gl/blob/master/modules/layers/src/bitmap-layer/bitmap-layer.ts

import { COORDINATE_SYSTEM, Layer, project32 } from '@deck.gl/core'
import { Model } from '@luma.gl/engine'

import createMesh from './mesh'

class StackedPNGLayer extends Layer {
  static layerName = 'StackedPNGLayer'

  static defaultProps = {
    _imageCoordinateSystem: COORDINATE_SYSTEM.DEFAULT,
    textureParameters: { type: 'object', ignore: true, value: null },
  }

  initializeState() {
    const attributeManager = this.getAttributeManager()
    attributeManager.remove(['instancePickingColors'])
    const noAlloc = true

    attributeManager.add({
      indices: {
        size: 1,
        isIndexed: true,
        update: (attribute) => {
          /* eslint-disable-next-line no-param-reassign */
          attribute.value = this.state.mesh.indices
        },
        noAlloc,
      },
      positions: {
        size: 3,
        type: 'float64',
        fp64: this.use64bitPositions(),
        update: (attribute) => {
          /* eslint-disable-next-line no-param-reassign */
          attribute.value = this.state.mesh.positions
        },
        noAlloc,
      },
      texCoords: {
        size: 2,
        update: (attribute) => {
          /* eslint-disable-next-line no-param-reassign */
          attribute.value = this.state.mesh.texCoords
        },
        noAlloc,
      },
    })

    const {
      id,
      shaders: { vs, fs },
    } = this.props

    // TODO: figure out how to unset or avoid geometryUniforms, etc
    this.state.model = new Model(this.context.device, {
      id,
      vs,
      fs,
      modules: [project32],
      bufferLayout: this.getAttributeManager().getBufferLayouts(),
      topology: 'triangle-list',
      isInstanced: false,
      vertexCount: 6,
    })
  }

  updateState({
    props: { bounds, images = [], renderTarget, filterValues, opacity },
    oldProps: {
      bounds: oldBounds,
      images: oldImages = [],
      renderTarget: oldRenderTarget = {},
      filterValues: oldFilterValues,
      opacity: oldOpacity,
    },
  }) {
    const attributeManager = this.getAttributeManager()

    if (bounds !== oldBounds) {
      const oldMesh = this.state.mesh

      const normalizedBounds = [
        [bounds[0], bounds[1]],
        [bounds[0], bounds[3]],
        [bounds[2], bounds[3]],
        [bounds[2], bounds[1]],
      ]
      const mesh = createMesh(
        normalizedBounds,
        this.context.viewport.resolution
      )

      Object.keys(mesh).forEach((key) => {
        if (oldMesh && oldMesh[key] !== mesh[key]) {
          attributeManager.invalidate(key)
        }
      })

      this.setState({
        mesh,
        coordinateConversion: 0,
        bounds: [0, 0, 0, 0],
      })

      this.state.model.setUniforms({ bounds })
    }

    if (
      images !== oldImages &&
      images.length > 0 &&
      images.every((item) => item)
    ) {
      this.state.model.setBindings({
        ...Object.fromEntries(images.map((image, i) => [`layer${i}`, image])),
      })
    }

    if (
      renderTarget &&
      renderTarget.layer &&
      renderTarget.id !== oldRenderTarget.id
    ) {
      this.state.model.setUniforms({
        renderLayerPaletteSize: renderTarget.palette.width,
        renderLayerTextureIndex: renderTarget.layer.textureIndex,
        renderLayerOffset: renderTarget.layer.offset,
        renderLayerBits: renderTarget.layer.bits,
      })
      this.state.model.setBindings({
        renderLayerPalette: renderTarget.palette,
      })
    }

    if (
      filterValues &&
      (!oldFilterValues ||
        !filterValues.every((v, i) => v === oldFilterValues[i]))
    ) {
      this.state.model.setUniforms({ filterValues })
    }
    if (opacity !== oldOpacity) {
      this.state.model.setUniforms({ opacity })
    }
  }

  draw() {
    const { model } = this.state
    const { images } = this.props

    if (
      !model ||
      !images ||
      images.length === 0 ||
      !images.every((item) => item)
    ) {
      return
    }

    model.draw(this.context.renderPass)
  }

  finalizeState() {
    super.finalizeState()

    const { images } = this.props

    // clear images to release memory
    if (images && images.length) {
      images.forEach((image) => {
        image.destroy()
      })
    }
  }
}

export default StackedPNGLayer
