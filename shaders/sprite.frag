#version 330 core

uniform sampler2D u_texture;
in vec2 v_uv;
out vec4 f_Color;

void main() {
    f_Color = texture(u_texture, v_uv);
}

