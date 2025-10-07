import glm
import numpy as np
from .model import Model


class TranslationGizmo:
    def __init__(self, position=(0,0,0), size=1.0):
        self.position = glm.vec3(*position)
        self.size = size
        self.axis_length = 2.0 * size
        self.arrow_size = 0.1 * size

        # Create the 3 axes with arrows
        self.x_axis = self._create_axis_arrow((1,0,0), (1,0,0,1))  # Red
        self.y_axis = self._create_axis_arrow((0,1,0), (0,1,0,1))  # Green
        self.z_axis = self._create_axis_arrow((0,0,1), (0,0,1,1))  # Blue

    def _create_axis_arrow(self, direction, color):
        """Create a simple arrow along the given direction"""
        direction = glm.vec3(*direction)
        dir_normalized = glm.normalize(direction)

        # Create vertices for a simple arrow (line + arrowhead)
        vertices = []

        # Arrow shaft (cylinder approximated by line)
        vertices.extend([0, 0, 0, *color])  # Start
        vertices.extend([self.axis_length * direction.x,
                        self.axis_length * direction.y,
                        self.axis_length * direction.z, *color])  # End

        # Arrowhead (simple triangle/diamond)
        head_start = self.axis_length - self.arrow_size
        head_positions = [
            (head_start * direction.x, head_start * direction.y, head_start * direction.z),
            ((head_start + self.arrow_size) * direction.x, (head_start + self.arrow_size) * direction.y, (head_start + self.arrow_size) * direction.z),
        ]

        # Add triangle vertices for arrowhead
        vertices.extend([head_positions[0][0], head_positions[0][1], head_positions[0][2], *color])
        vertices.extend([head_positions[1][0], head_positions[1][1], head_positions[1][2], *color])

        indices = [0, 1, 2, 3]  # Line + triangle

        return {
            'vertices': np.array(vertices, dtype='f4'),
            'indices': np.array(indices, dtype='i4'),
            'direction': direction,
            'color': color
        }

    def get_model_matrix(self, axis='x'):
        model = glm.mat4(1)
        model = glm.translate(model, self.position)

        if axis == 'x':
            return model
        elif axis == 'y':
            return glm.rotate(model, glm.radians(-90), glm.vec3(0, 0, 1))
        elif axis == 'z':
            return glm.rotate(model, glm.radians(90), glm.vec3(0, 1, 0))

        return model

    def check_gizmo_hit(self, ray_origin, ray_direction, axis):
        """Simple sphere intersection for gizmo selection"""
        axis_pos = self.position + self.axis_length * 0.5 * self._get_axis_dir(axis)
        radius = self.arrow_size

        oc = ray_origin - axis_pos
        a = glm.dot(ray_direction, ray_direction)
        b = 2.0 * glm.dot(oc, ray_direction)
        c = glm.dot(oc, oc) - radius * radius
        discriminant = b * b - 4 * a * c

        return discriminant >= 0

    def _get_axis_dir(self, axis):
        if axis == 'x': return glm.vec3(1, 0, 0)
        if axis == 'y': return glm.vec3(0, 1, 0)
        if axis == 'z': return glm.vec3(0, 0, 1)
        return glm.vec3(0, 0, 0)
