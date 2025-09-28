import numpy as np
from .graphics import Graphics
import glm

class Skybox:
    def __init__(self, ctx, program, size=50.0):
        self.ctx = ctx
        self.position = glm.vec3(0)
        self.scale = glm.vec3(size)
        # Un cubo grande, color cielo (azul claro)
        color = [0.5, 0.7, 1.0]  # RGB cielo
        vertices = [
            # posiciones         # color
            -1,-1,-1, *color,  1,-1,-1, *color,
            1,1,-1, *color,   -1,1,-1, *color,
            -1,-1,1, *color,   1,-1,1, *color,
            1,1,1, *color,    -1,1,1, *color
        ]
        indices = [
            0,1,2,2,3,0,    # back
            4,5,6,6,7,4,    # front
            0,4,7,7,3,0,    # left
            1,5,6,6,2,1,    # right
            3,2,6,6,7,3,    # top
            0,1,5,5,4,0     # bottom
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
