#version 330

in vec2 in_pos;
in vec2 in_uv;
out vec2 v_uv;

uniform mat4 Mvp;

void main(){
    gl_Position = Mvp * vec4(in_pos, 0.0, 1.0);
    v_uv = in_uv;
}
