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
       if(not self.hittable):
           return False
       else: 
         origin = glm.vec3(*origin)
         direction = glm.normalize(glm.vec3(*direction))

         min_bounds = self.position - self.scale
         max_bounds = self.position + self.scale

         t_min = (min_bounds - origin) / direction
         t_max = (max_bounds - origin) / direction

         t1 = glm.min(t_min, t_max)
         t2 = glm.max(t_min, t_max)

         t_near = glm.max(t1.x, t1.y, t1.z)
         t_far = glm.min(t2.x, t2.y, t2.z)

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
      
         if(not self.hittable):
              return False
         else: 
            origin = glm.vec3(*origin)
            direction = glm.normalize(glm.vec3(*direction))
    
            min_bounds = self.position - self.scale
            max_bounds = self.position + self.scale
    
            t_min = (min_bounds - origin) / direction
            t_max = (max_bounds - origin) / direction
    
            t1 = glm.min(t_min, t_max)
            t2 = glm.max(t_min, t_max)
    
            t_near = glm.max(t1.x, t1.y, t1.z)
            t_far = glm.min(t2.x, t2.y, t2.z)
    
            return t_near <= t_far and t_far >= 0
