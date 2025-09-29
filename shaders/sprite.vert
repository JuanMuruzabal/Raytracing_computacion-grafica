#version 330 core

in vec3 position;
in vec2 texcoord;
out vec2 texcoord_out;

uniform mat4 Mvp;

void main() {
    gl_Position = Mvp * vec4(position, 1.0);
    texcoord_out = texcoord;
}
