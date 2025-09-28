class Vertex:
    def __init__(self,  name, format, array):
        self.__name = name
        self.__format = format
        self.__array = array

    @property 
    def name(self):
        return self.__name
    
    @property
    def format(self):
        return self.__format
    
    @property
    def array(self):
        return self.__array
    

class VertexLayout:
    def __init__(self):
        self.__vertices = []
    
    def add_vertex(self, name, format, array):
        vertex = Vertex(name, format, array)
        self.__vertices.append(vertex)
    
    def get_attributes(self):
        return self.__vertices
    

class Model:
    def __init__(self, vertices = None, indices = None, colors = None, normals = None, texcoords = None):
        self.indices = indices
        self.vertex_layout = VertexLayout()
        if vertices is not None:
            self.vertex_layout.add_vertex("position", "3f", vertices)
        if colors is not None:
            self.vertex_layout.add_vertex("color", "3f", colors)
        if normals is not None:
            self.vertex_layout.add_vertex("normal", "3f", normals)
        if texcoords is not None:
            self.vertex_layout.add_vertex("texcoord", "2f", texcoords)
         
       