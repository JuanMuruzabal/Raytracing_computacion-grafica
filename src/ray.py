import glm 

class Ray:
    def __init__(self, origin=glm.vec3(0), direction=glm.vec3(0,0,1)):
        self.__origin = glm.vec3(*origin)
        self.__direction = glm.normalize(glm.vec3(*direction))

    @property
    def origin(self) -> glm.vec3:
        return self.__origin
    
    @property 
    def direction(self) -> glm.vec3:
        return self.__direction

    def at(self, t):
        return self.__origin + t * self.__direction

    def reflect(self, normal):
        normal = glm.normalize(normal)
        return self.direction - 2 * glm.dot(self.direction, normal) * normal
