import glm
import math
from .graphics import Graphics
from .raytracer import RayTracer

class Scene:
    def __init__(self, ctx, camera):
        self.ctx = ctx
        self.objects = []
        self.camera = camera
        self.time = 0.0
        self.graphics = {}
        self.projection = self.camera.get_perspective_matrix()
        self.view = self.camera.get_view_matrix()


    def add_object(self, obj, material=None):
        self.objects.append(obj)
        # Create graphics for this object
        self.graphics[obj.name] = Graphics(self.ctx, obj, material)

        
    def start(self):
        print("Start!")

    def render(self):
        self.time += 0.01
        for obj in self.objects:
            if obj.name != "Sprite":
                obj.rotation += glm.vec3(0.8, 0.6, 0.4) 
                obj.position.x += math.sin(self.time) * 0.01
                
            model = obj.get_model_matrix()
            mvp = self.projection * self.view * model
            self.graphics[obj.name].render({"Mvp": mvp})
        
                
    def on_mouse_click(self, u, v):
        ray = self.camera.raycast(u, v)
        for obj in self.objects:
            hit, dist, point = obj.check_hit(ray.origin, ray.direction)
            if hit:
                print(f"Impacto en {obj.name}")
                print(f" → Distancia: {dist:.2f}")
                print(f" → Punto: ({point.x:.2f}, {point.y:.2f}, {point.z:.2f})")

    def on_resize(self, width, height):
        if self.camera:
            self.camera.aspect_ratio = width / height

class RayScene(Scene):
    def __init__(self, ctx, camera, width, height):
        super().__init__(ctx, camera)
        self.raytracer = RayTracer(camera, width, height)

    def start(self):
        self.raytracer.render_frame(self.objects)
        if "Sprite" in self.graphics:
            self.graphics["Sprite"].update_texture("u_texture", self.raytracer.get_texture())

    def render(self):
        super().render()

    def on_resize(self, width, height):
        super().on_resize(width, height)
        self.raytracer = RayTracer(self.camera, width, height)
        self.start()
    # Este método fue cambiado: recrea el raytracer y la textura al redimensionar la ventana.