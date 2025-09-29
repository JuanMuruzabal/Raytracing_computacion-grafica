import moderngl
from src import texture
from .shader_program import ShaderProgram
import numpy as np

class Graphics:
    def __init__(self, ctx, model, material):
        self.ctx = ctx
        self.model = model
        self.material = material

        self.__vbo = self.create_buffers()
        self.__ibo = self.ctx.buffer(model.indices.tobytes())
        # Usar self.ctx.vertex_array y material.shader_program.program
        self.__vao = self.ctx.vertex_array(
            self.material.shader_program.program,
            [(vbo, fmt, name) for vbo, fmt, name in self.__vbo],
            self.__ibo
        )
        self.__textures = self.load_textures(material.textures_data)
        
    def create_buffers(self):
        buffers = []
        shader_attributes = self.material.shader_program.attributes

        for attribute in self.model.vertex_layout.get_attributes():
            if attribute.name in shader_attributes:
                vbo = self.ctx.buffer(attribute.array.tobytes())
                buffers.append((vbo, attribute.format, attribute.name))
        return buffers

    def load_textures(self, textures_data):
        textures = []
        for tex in textures_data:
            if tex.image_data:
                texture_ctx = self.ctx.texture(tex.size, tex.channels_amount, tex.image_data)
                if tex.build_mipmaps:
                    texture_ctx.build_mipmaps()
                texture_ctx.repeat_x = tex.repeat_x
                texture_ctx.repeat_y = tex.repeat_y
                textures.append((tex.name, texture_ctx))
        return textures
    
    def render(self, uniforms):
        for name, value in uniforms.items():
            if name in self.material.shader_program.program:
                self.material.set_uniform(name, value)
        for i, (name, tex) in enumerate(self.__textures):
            tex.use(location=i)
            self.material.shader_program.set_uniform(name, i)
        self.__vao.render()