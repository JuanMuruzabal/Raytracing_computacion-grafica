import moderngl

from . import texture
from .shader_program import ShaderProgram
import numpy as np

class Graphics:
    def __init__(self, ctx, model, material):
        self.__ctx = ctx
        self.__model = model
        self.__material = material
      
        self.__vbo = self.create_buffers()
        self.__ibo = self.__ctx.buffer(model.indices.tobytes())
        self.__vao = self.__ctx.vertex_array(
            material.shader_program.program,
            self.__vbo,
            self.__ibo
        )
        self.__textures = self.load_textures(material.textures_data)
        
    def create_buffers(self):
       buffers = []
       shader_attributes = self.__material.shader_program.attributes

       for attribute in self.__model.vertex_layout.get_attributes():
              if attribute.name in shader_attributes:
                vbo = self.__ctx.buffer(attribute.array.tobytes())
                buffers.append((vbo, attribute.format, attribute.name))
       return buffers

    def load_textures(self, textures_data):
        textures = {}  # Cambia de lista a diccionario
        for texture in textures_data:
            if texture.image_data:
                texture_ctx = self.__ctx.texture(
                    texture.size,
                    texture.channels_amount,
                    texture.image_data.tobytes() if hasattr(texture.image_data, "tobytes") else texture.image_data
                )
                if texture_ctx.build_mipmaps:
                    texture_ctx.build_mipmaps()
                texture_ctx.repeat_x = texture.repeat_x
                texture_ctx.repeat_y = texture.repeat_y
                textures[texture.name] = (texture.name, texture_ctx)
        return textures
    # Esta función fue cambiada: ahora usa un diccionario y asegura que los datos sean bytes.

    def render(self, uniforms):
        for name, value in uniforms.items():
            if name in self.__material.shader_program.program:
                self.__material.set_uniform(name, value)
        for i, (name, texture) in enumerate(self.__textures.values()):  # Usa .values() para iterar
            texture.use(location=i)
            self.__material.shader_program.set_uniform(name, i)
        self.__vao.render()
    
    def update_texture(self, texture_name, new_data):
        if texture_name not in self.__textures:
            return ValueError(f"Texture {texture_name} not found")
        
        _, texture_ctx = self.__textures[texture_name]
        texture_ctx.write(new_data.tobytes() if hasattr(new_data, "tobytes") else new_data)
    # Esta función fue cambiada: ahora solo sube los datos nuevos, eliminando errores de métodos inexistentes.
