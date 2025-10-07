from .model import Model
from .hit import HitBoxOBB
import numpy as np
import glm


class Sphere(Model):

    def __init__(self, position=(0,0,0), rotation=(0,0,0), scale=(1,1,1), radius=1.0, name="sphere", animated=True, hittable=True):
        self.name = name
        self.animated = animated
        self.position = glm.vec3(*position)
        self.rotation = glm.vec3(*rotation)
        self.scale = glm.vec3(*scale)
        self.radius = radius
        self.__colision = HitBoxOBB(get_model_matrix=lambda: self.get_model_matrix(), hittable=hittable)

        # Generate sphere vertices for rendering
        vertices, indices = self._generate_sphere_vertices(radius, 32, 16)

        colors = np.random.uniform(0.0, 1.0, size=(len(vertices)//3, 3)).astype('f4')  # Random colors for now
        normals = vertices.copy()  # Normals point outward from center
        texcoords = np.zeros((len(vertices)//3, 2), dtype='f4')  # Placeholder UVs

        super().__init__(vertices, indices, colors=colors, normals=normals, texcoords=texcoords)

    @property
    def aabb(self):
        # Axis-aligned bounding box for sphere in world space
        center = self.position
        # Sphere extends radius in all directions from center
        radius_vec = glm.vec3(self.radius * max(self.scale))  # Use maximum scale component
        min_bounds = center - radius_vec
        max_bounds = center + radius_vec
        return (min_bounds, max_bounds)

    def _generate_sphere_vertices(self, radius, sectors, stacks):
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
                vertices.extend([x, y, z])

        for i in range(stacks):
            for j in range(sectors):
                first = i * (sectors + 1) + j
                second = first + sectors + 1
                indices.extend([first, second, first + 1])
                indices.extend([second, second + 1, first + 1])

        return np.array(vertices, dtype='f4'), np.array(indices, dtype='i4')

    def check_hit(self, origin, direction):
        return self.__colision.check_hit(origin, direction)

    def get_model_matrix(self):
        model = glm.mat4(1)
        model = glm.translate(model, self.position)
        model = glm.rotate(model, glm.radians(self.rotation.x % 360), glm.vec3(1, 0, 0))
        model = glm.rotate(model, glm.radians(self.rotation.y % 360), glm.vec3(0, 1, 0))
        model = glm.rotate(model, glm.radians(self.rotation.z % 360), glm.vec3(0, 0, 1))
        model = glm.scale(model, self.scale)
        return model
