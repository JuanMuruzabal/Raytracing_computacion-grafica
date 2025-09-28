import glm 

class Ray:
    def _init__(self, origin=glm.vec3(0), direction=glm.vec3(0,0,1)):
        self.__origin = glm.vec3(*origin)
        self.__direction = glm.normalize(glm.vec3(*direction))

    @property
    def origin(self) -> glm.vec3:
        return self.__origin
    
    @property 
    def direction(self) -> glm.vec3:
        return self.__direction