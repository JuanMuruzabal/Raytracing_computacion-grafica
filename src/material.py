from .texture import Texture

class Material:
    def __init__(self, shader_program, textures_data = []):
        self.__shader_program = shader_program
        self.__textures_data = textures_data

    @property
    def shader_program(self):
        return self.__shader_program

    @property
    def textures_data(self):
        return self.__textures_data

    def set_uniform(self, name, value):
        self.__shader_program.set_uniform(name, value)

class StandardMaterial(Material):
    def __init__(self, shader_program, albedo: Texture, reflectivity = 0.0):
       self.reflectivity = reflectivity
       self.colorRGB = albedo.image_data.data[0,0]
       super().__init__(shader_program, textures_data=[albedo])