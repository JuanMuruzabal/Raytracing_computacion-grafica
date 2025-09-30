import glm

class Hit:
    def __init__(self, get_model_matrix, hittable=True):
        self.__model_matrix = get_model_matrix
        self.hittable = hittable

    @property
    def model_matrix(self):
        return self.__model_matrix()

    @property
    def position(self):
        m = self.model_matrix
        return glm.vec3(m[3].x, m[3].y, m[3].z)

    @property
    def scale(self):
        m = self.model_matrix
        return glm.vec3(
            glm.length(glm.vec3(m[0])),
            glm.length(glm.vec3(m[1])),
            glm.length(glm.vec3(m[2])))

    def check_hit(self, origin, direction):
        raise NotImplementedError("Subclasses must implement this method")

class HitBoxOBB(Hit):
    def __init__(self, get_model_matrix, hittable=True):
        super().__init__(get_model_matrix, hittable)

    def check_hit(self, origin, direction):
        if not self.hittable:
            return False
        
        origin = glm.vec3(origin)
        direction = glm.normalize(glm.vec3(direction))
        inv_model = glm.inverse(self.model_matrix)
        local_origin = inv_model * glm.vec4(origin, 1.0)
        local_dir = inv_model * glm.vec4(direction, 0.0)

        local_origin = glm.vec3(local_origin)
        local_dir = glm.normalize(glm.vec3(local_dir))

        min_bounds = glm.vec3(-1, -1, -1)
        max_bounds = glm.vec3(1, 1, 1)

        tmin = (min_bounds - local_origin) / local_dir
        tmax = (max_bounds - local_origin) / local_dir

        t1 = glm.min(tmin, tmax)
        t2 = glm.max(tmin, tmax)

        t_near = max(t1.x, t1.y, t1.z)
        t_far = min(t2.x, t2.y, t2.z)

        return t_near <= t_far and t_far >= 0

class Hitbox(Hit):
    def __init__(self, position=(0,0,0), scale=(1,1,1), hittable=True):
        self._position = glm.vec3(*position)
        self._scale = glm.vec3(*scale)
        super().__init__(get_model_matrix=lambda: self._get_model_matrix(), hittable=hittable)

    def _get_model_matrix(self):
        model = glm.mat4(1)
        model = glm.translate(model, self._position)
        model = glm.scale(model, self._scale)
        return model

    @property
    def position(self):
        return self._position

    @property
    def scale(self):
        return self._scale

    def check_hit(self, origin, direction):
        if not self.hittable:
            return False
        
        origin = glm.vec3(*origin)
        direction = glm.normalize(glm.vec3(*direction))
        
        min_bounds = self.position - self.scale
        max_bounds = self.position + self.scale
        
        # Proper ray-AABB intersection algorithm
        tmin = (min_bounds.x - origin.x) / direction.x
        tmax = (max_bounds.x - origin.x) / direction.x
        
        if tmin > tmax:
            tmin, tmax = tmax, tmin
            
        tymin = (min_bounds.y - origin.y) / direction.y
        tymax = (max_bounds.y - origin.y) / direction.y
        
        if tymin > tymax:
            tymin, tymax = tymax, tymin
            
        if tmin > tymax or tymin > tmax:
            return False
            
        tmin = glm.max(glm.vec3(tmin, tymin, 0))
        tmax = glm.min(glm.vec3(tmax, tymax, 0))
        
        tzmin = (min_bounds.z - origin.z) / direction.z
        tzmax = (max_bounds.z - origin.z) / direction.z
        
        if tzmin > tzmax:
            tzmin, tzmax = tzmax, tzmin
            
        if tmin > tzmax or tzmin > tmax:
            return False
            
        tmin = glm.max(glm.vec3(tmin, tzmin, 0))
        tmax = glm.min(glm.vec3(tmax, tzmax, 0))
        
        return tmax >= glm.max(glm.vec3(0, tmin, 0))
