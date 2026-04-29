#version 300 es
#define SHADER_NAME stackedpng_fragment_shader

#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif

in vec2 vTexCoord;
out vec4 fragColor;

uniform sampler2D palette;

// uniforms for textures for each layer
uniform sampler2D layer0;
uniform sampler2D layer1;
uniform sampler2D layer2;
uniform sampler2D layer3;
uniform sampler2D layer4;


// return 32-bit integer from vector components
int rgbToInt32(ivec3 v) {
  return (v.r << 16) + (v.g << 8) + v.b;
}

int bitmask(int bits) {
  return int(pow(2., float(bits))) - 1;
}

bool matchValue(int valueRGB, int offset, int numBits, int filterValue) {
  int value = (valueRGB >> offset) & bitmask(numBits);

  // use left shift to set the bit in the value position to 1
  // then use bitwise AND to verify that value is also turned on in active
  // filters. If the value is 0, then value is not present in active filters.
  return (filterValue & (1 << value)) > 0;
}

void main(void) {
  int valueRGB0 = rgbToInt32(ivec3(texture(layer0, vTexCoord).rgb * 255.));
  int valueRGB1 = rgbToInt32(ivec3(texture(layer1, vTexCoord).rgb * 255.));
  int valueRGB2 = rgbToInt32(ivec3(texture(layer2, vTexCoord).rgb * 255.));
  int valueRGB3 = rgbToInt32(ivec3(texture(layer3, vTexCoord).rgb * 255.));
  int valueRGB4 = rgbToInt32(ivec3(texture(layer4, vTexCoord).rgb * 255.));

  // canRender is True where all filters are either not set or value is one
  // of active filter values

  // replaced dynamically from JS; sets canRender
  // <FILTER_EXPR>

  int valueRGB;
  if (stackedPNGLayer.textureIndex == 0) {
    valueRGB = valueRGB0;
  }
  else if (stackedPNGLayer.textureIndex == 1) {
    valueRGB = valueRGB1;
  } else if (stackedPNGLayer.textureIndex == 2) {
    valueRGB = valueRGB2;
  } else if (stackedPNGLayer.textureIndex == 3) {
    valueRGB = valueRGB3;
  } else if (stackedPNGLayer.textureIndex == 4) {
    valueRGB = valueRGB4;
  }

  int renderValue = (valueRGB >> stackedPNGLayer.offset) & bitmask(stackedPNGLayer.bits);
  fragColor = texelFetch(palette, ivec2(renderValue, 0), 0);

  fragColor.a = fragColor.a * stackedPNGLayer.opacity;
  if (!canRender) {
    fragColor.a = 0.0;
  }
}