#version 300 es
#define SHADER_NAME stackedpng_vertex_shader

in vec2 texCoords;
in vec3 positions;
in vec3 positions64Low;

out vec2 vTexCoord;

void main(void) {
  vTexCoord = texCoords;

  gl_Position = project_common_position_to_clipspace(vec4(project_position(positions, positions64Low), 1.0));
}