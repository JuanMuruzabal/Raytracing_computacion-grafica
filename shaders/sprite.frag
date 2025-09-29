#version 330 core
in vec2 texcoord_out;
out vec4 out_color;
uniform sampler2D u_texture;

void main() {
    out_color = texture(u_texture, texcoord_out);
}

