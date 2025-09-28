#version 330 core
in vec3 in_pos;
in vec3 in_color;

uniform mat4 Mvp;

out vec3 color;

void main() {
    gl_Position = Mvp * vec4(in_pos, 1.0);
    color = in_color;
}
