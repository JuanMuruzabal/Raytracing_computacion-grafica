import glm
import math
from .ray import Ray

class Camera:
    def __init__(self, position, target, up, fov, aspect, near, far):
        self.position = glm.vec3(*position)
        self.target = glm.vec3(*target)
        self.fov = fov
        self.aspect = aspect
        self.near = near
        self.far = far
        self.__sky_color_top = None
        self.__sky_color_bottom = None
        self.world_up = glm.vec3(*up)  # Store the world up vector

        # Calculate initial yaw and pitch from target
        self.yaw = 0.0
        self.pitch = 0.0
        self._update_yaw_pitch_from_target()

    def set_sky_colors(self, top, bottom):
        self.__sky_color_top = glm.vec3(*top)      # Solo RGB
        self.__sky_color_bottom = glm.vec3(*bottom)# Solo RGB
    
    def get_sky_gradient(self, height):
        point = pow(0.5 * (height + 1.0), 1.5)
        return (1.0 - point) * self.__sky_color_bottom + point * self.__sky_color_top
    # Esta función fue cambiada: ahora retorna RGBA para evitar errores de broadcasting.

    @property
    def aspect_ratio(self):
        return self.aspect
    
    @aspect_ratio.setter
    def aspect_ratio(self, value):
        self.aspect = value
        self.projection = glm.perspective(glm.radians(self.fov), value, self.near, self.far)
        
    def update_view(self):
        self.view = glm.lookAt(self.position, self.target, self.up)

        
    def get_perspective_matrix(self):
        return glm.perspective(glm.radians(self.fov), self.aspect, self.near, self.far)
    
    def get_view_matrix(self):
        return self.get_view_matrix_rotated()
    
    def get_inverse_view_matrix(self):
        view = self.get_view_matrix()
        return glm.inverse(view)

    def _update_yaw_pitch_from_target(self):
        direction = self.target - self.position
        direction = glm.normalize(direction)

        self.yaw = math.atan2(direction.z, direction.x)
        self.pitch = math.asin(direction.y)

    @property
    def forward(self):
        return glm.vec3(
            math.cos(self.yaw) * math.cos(self.pitch),
            math.sin(self.pitch),
            math.sin(self.yaw) * math.cos(self.pitch)
        )

    @property
    def right(self):
        forward = self.forward
        return glm.normalize(glm.cross(forward, glm.vec3(0, 1, 0)))

    @property
    def up(self):
        forward = self.forward
        right = self.right
        return glm.cross(right, forward)

    def get_view_matrix_rotated(self):
        eye = self.position
        center = eye + self.forward
        up = self.up
        return glm.lookAt(eye, center, up)

    def rotate(self, yaw_delta, pitch_delta):
        self.yaw += yaw_delta
        self.pitch += pitch_delta
        # Clamp pitch to avoid gimbal lock
        self.pitch = glm.clamp(self.pitch, -glm.radians(89.0), glm.radians(89.0))

        # Update target and view after rotation
        self.target = self.position + self.forward
        self.update_view()

    def raycast(self, u, v):
        # Paso 1: Convertir screen coords (0-1) a NDC (-1 a 1)
        # NDC: x -1 left to 1 right, y -1 bottom to 1 top
        # Screen: u 0 left to 1 right, v 0 top to 1 bottom
        ndc_x = 2.0 * u - 1.0
        ndc_y = - (2.0 * v - 1.0)  # Flip y: v=0 -> 1 (top), v=1 -> -1 (bottom)

        # Paso 2: Calcular dirección en near plane usando proyección perspectiva correcta
        tan_fov_half = math.tan(math.radians(self.fov) / 2.0)
        near_plane_dir = glm.vec3(
            ndc_x * self.aspect * tan_fov_half,
            ndc_y * tan_fov_half,
            -1.0  # Pointing into screen (negative Z)
        )

        # Paso 3: Transformar por la vista inversa para llevar a espacio mundo
        view_matrix = self.get_view_matrix_rotated()
        inv_view = glm.inverse(view_matrix)
        world_dir = glm.normalize(inv_view * glm.vec4(near_plane_dir, 0.0))

        return Ray(self.position, glm.vec3(world_dir))
