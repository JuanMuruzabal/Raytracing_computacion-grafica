class Material:
    def __init__(self, shader_program, textures_data = []):
        self.shader_program = shader_program
        self.textures_data = textures_data

    @property
    def shader_program(self):
        return self._shader_program

    @shader_program.setter
    def shader_program(self, value):
        self._shader_program = value

    @property
    def textures_data(self):
        return self._textures_data

    @textures_data.setter
    def textures_data(self, value):
        self._textures_data = value

    def set_uniform(self, name, value):
        self.shader_program.set_uniform(name, value)