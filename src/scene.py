import glm
import math
from .graphics import Graphics

class Scene:
    def __init__(self, window, camera):
        self.window = window
        self.objects = []
        self.camera = camera
        self.time = 0.0
        self.graphics = {}
        
    def add_object(self, obj, material):
        self.objects.append((obj, material))
        # Create graphics for this object
        self.graphics[obj.name] = Graphics(self.window.ctx, obj, material)
        
    def render(self):
        self.time += 0.01
        # Update projection and view matrices from camera
        self.projection = self.camera.get_projection_matrix()
        self.view = self.camera.get_view_matrix()
        
        for obj, material in self.objects:
            if obj.name != "Sprite":
                obj.rotation += glm.vec3(0.8, 0.6, 0.4) 
                obj.position.x += math.sin(self.time) * 0.01
                
            model = obj.get_model_matrix()
            mvp = self.projection * self.view * model
            self.graphics[obj.name].render({"Mvp": mvp})
        

    def on_mouse_click(self, u, v):
        ray = self.camera.raycast(u, v)
        for obj, material in self.objects:
            if obj.check_hit(ray.origin, ray.direction):
                print(f"Golpeaste al chaval tio: {obj.name}")
                

    def on_resize(self, width, height):
        if self.camera:
            self.camera.aspect_ratio = width / height
