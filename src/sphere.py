import glm
import numpy as np
from .graphics import Graphics

class Sphere:
    def __init__(self, ctx, program, radius=1.0, sectors=32, stacks=16):
        self.ctx = ctx
        self.position = glm.vec3(0)
        self.rotation = glm.vec3(0)
        self.scale = glm.vec3(1)

        vertices = []
        indices = []

        for i in range(stacks + 1):
            stack_angle = np.pi / 2 - i * np.pi / stacks
            xy = radius * np.cos(stack_angle)
            z = radius * np.sin(stack_angle)
            for j in range(sectors + 1):
                sector_angle = j * 2 * np.pi / sectors
                x = xy * np.cos(sector_angle)
                y = xy * np.sin(sector_angle)
                # Color simple basado en posición
                r = (x + radius) / (2 * radius)
                g = (y + radius) / (2 * radius)
                b = (z + radius) / (2 * radius)
                vertices.extend([x, y, z, r, g, b])

        for i in range(stacks):
            for j in range(sectors):
                first = i * (sectors + 1) + j
                second = first + sectors + 1
                indices.extend([first, second, first + 1])
                indices.extend([second, second + 1, first + 1])

        self.vertices = np.array(vertices, dtype='f4')
        self.indices = np.array(indices, dtype='i4')

        self.graphics = Graphics(
            ctx=self.ctx,
            program=program,
            vertices=self.vertices,
            indices=self.indices
        )

    def get_model_matrix(self):
        model = glm.mat4(1.0)
        model = glm.translate(model, self.position)
        model = glm.rotate(model, self.rotation.x, glm.vec3(1,0,0))
        model = glm.rotate(model, self.rotation.y, glm.vec3(0,1,0))
        model = glm.rotate(model, self.rotation.z, glm.vec3(0,0,1))
        return glm.scale(model, self.scale)
