import glm
from .ray import Ray 

class Camera:
    def __init__(self, position, target, up, fov, aspect, near, far):
        self.position = glm.vec3(*position)
        self.target = glm.vec3(*target)
        self.up = glm.vec3(*up)
        self.fov = fov
        self.aspect = aspect
        self.near = near
        self.far = far
        
        
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
    
    def get_projection_matrix(self):
        # Alias para compatibilidad con Scene
        return self.get_perspective_matrix()
    
    def get_view_matrix(self):
        return glm.lookAt(self.position, self.target, self.up)
    
    def raycast(self, u, v):
        fov_adjustment = glm.tan(glm.radians(self.fov) / 2)

        ndc_x = (2 * u - 1) * self.aspect * fov_adjustment
        ndc_y = (2 * v - 1) * fov_adjustment
        
        ray_dir_camera = glm.vec3(ndc_x, ndc_y, -1.0)
        ray_dir_camera = glm.normalize(ray_dir_camera)

        view = self.get_view_matrix()
        inv_view = glm.inverse(view)
        ray_dir_world = glm.vec3(
            inv_view * glm.vec4(ray_dir_camera, 0.0)
        )

        return Ray(self.position, ray_dir_world)