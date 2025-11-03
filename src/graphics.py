import glm
import moderngl

from .texture import Texture
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
            [*self.__vbo],
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
                    texture.get_bytes()
                )
                if texture_ctx.build_mipmaps:
                    texture_ctx.build_mipmaps()
                texture_ctx.repeat_x = texture.repeat_x
                texture_ctx.repeat_y = texture.repeat_y
                textures[texture.name] = (texture, texture_ctx)
        return textures
    # Esta función fue cambiada: ahora usa un diccionario y asegura que los datos sean bytes.

    def bind_to_image(self, name = "u_texture", unit = 0, read = False, write = True):
        self.__textures[name][1].bind_to_image(unit, read, write)


    def render(self, uniforms):
        for name, value in uniforms.items():
            if name in self.__material.shader_program.program:
                self.__material.set_uniform(name, value)

        for i, (texture, texture_ctx) in enumerate(self.__textures.values()):  # Usa .values() para iterar
            texture_ctx.use(i)
            self.__material.shader_program.set_uniform(texture.name, i)

        self.__vao.render()
    
    def update_texture(self, texture_name, new_data):
        if texture_name not in self.__textures:
            return ValueError(f"Texture {texture_name} not found")

        texture, texture_ctx = self.__textures[texture_name]
        texture.update_data(new_data)
        texture_ctx.write(texture.get_bytes())
    # Esta función fue cambiada: ahora solo sube los datos nuevos, eliminando errores de métodos inexistentes.

    def cleanup(self):
        """Clean up OpenGL resources to prevent memory leaks"""
        try:
            # Release VBOs
            if hasattr(self, '__vbo') and self.__vbo:
                for vbo_tuple in self.__vbo:
                    if len(vbo_tuple) >= 1 and hasattr(vbo_tuple[0], 'release'):
                        vbo_tuple[0].release()

            # Release IBO
            if hasattr(self, '__ibo') and self.__ibo:
                self.__ibo.release()

            # Release VAO
            if hasattr(self, '__vao') and self.__vao:
                self.__vao.release()

            # Release textures
            if hasattr(self, '__textures') and self.__textures:
                for texture_name, (texture_obj, texture_ctx) in self.__textures.items():
                    if texture_ctx and hasattr(texture_ctx, 'release'):
                        texture_ctx.release()

            # Clear references
            self.__vbo = None
            self.__ibo = None
            self.__vao = None
            self.__textures = {}

        except Exception as e:
            print(f"Warning: Error during graphics cleanup: {e}")

   
class ComputeGraphics(Graphics):
    def __init__(self, ctx, model, material):
       self.__ctx = ctx
       self.__model = model
       self.__material = material
       self.textures = material.textures_data
       super().__init__(ctx, model, material)

    def create_primitive(self, primitives):
        amin, amax = self.__model.aabb
        primitives.append({"aabb_min": amin, "aabb_max": amax})

    def create_transformation_matrix(self, transformations_matrix, index):
        m = self.__model.get_model_matrix()
        transformations_matrix[index] = np.array(m.to_list(), dtype='f4').reshape(16)

    def create_inverse_transformation_matrix(self, inv_transformations_matrix, index):
        m = self.__model.get_model_matrix()
        inv_m = glm.inverse(m)
        inv_transformations_matrix[index] = np.array(inv_m.to_list(), dtype='f4').reshape(16)

    def create_material_matrix(self, materials_matrix, index):
        reflectivity = self.__material.reflectivity
        r,g,b = self.__material.colorRGB

        r = r / 255.0 if r > 1.0 else r
        g = g / 255.0 if g > 1.0 else g
        b = b / 255.0 if b > 1.0 else b

        materials_matrix[index, :] = np.array([r, g, b, reflectivity], dtype='f4')
