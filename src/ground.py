import numpy as np
from .graphics import Graphics
import glm

class Ground:
    def __init__(self, ctx, program, size=20.0):
        self.ctx = ctx
        self.position = glm.vec3(0, -1, 0)
        self.scale = glm.vec3(size, 1, size)
        # Plano blanco
        color = [1.0, 1.0, 1.0]  # RGB blanco
        vertices = [
            # posiciones         # color
            -1,0,-1, *color,  1,0,-1, *color,
            1,0,1, *color,   -1,0,1, *color
        ]
        indices = [
            0,1,2, 2,3,0
        ]
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
        return glm.scale(model, self.scale)
