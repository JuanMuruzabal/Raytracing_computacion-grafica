#version 330 core
in vec3 position;
in vec3 color;

uniform mat4 Mvp;

out vec3 frag_color;

void main() {
    gl_Position = Mvp * vec4(position, 1.0);
    frag_color = color;
}
