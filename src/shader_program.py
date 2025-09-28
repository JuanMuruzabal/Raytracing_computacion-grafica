from moderngl import Attribute, Uniform
import glm

class ShaderProgram:
    def __init__(self, ctx, vertex_shader_path, fragment_shader_path):
       with open(vertex_shader_path) as file:
           vertex_shader = file.read()
       with open(fragment_shader_path) as file:
              fragment_shader = file.read()
       self.program = ctx.program(vertex_shader=vertex_shader, fragment_shader=fragment_shader)

       attributes = []
       uniforms = []
       for name in self.program:
            member = self.program[name]
            if type(member) is Attribute:
                attributes.append(name)
            if type(member) is Uniform:
                uniforms.append(name)

       self.attributes = list(attributes)
       self.uniforms = list(uniforms)


    def set_uniform(self,name,value):
        if name in self.uniforms:
            uniform = self.program[name]
            if isinstance(value,glm.mat4):
                uniform.write(value.to_bytes())
            elif hasattr(uniform, "value"):
                uniform.value = value
    
        
    def load_program(self, vertex_path, fragment_path):
        with open(vertex_path) as file:
            vertex_shader = file.read()
        with open(fragment_path) as file:
            fragment_shader = file.read()
        return self.ctx.program(
            vertex_shader=vertex_shader,
            fragment_shader=fragment_shader
        )
    
    def __getitem__(self, name):
        return self.program[name]
