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
