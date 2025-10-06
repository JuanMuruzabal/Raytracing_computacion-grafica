import glm
import math
from .graphics import Graphics, ComputeGraphics
from .raytracer import RayTracer, RayTracerGPU
import numpy as np

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
            if (obj.animated):
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

class RaySceneGPU(Scene):
    def __init__(self, ctx, camera, width, height, output_model, output_material):
       self.ctx = ctx
       self.camera = camera
       self.width = width
       self.height = height
       self.raytracer = None

       self.output_graphics = Graphics(ctx, output_model, output_material)
       self.raytracer = RayTracerGPU(ctx, camera, width, height, self.output_graphics)

       super().__init__(self.ctx, self.camera)

def add_object(self, model, material):
    self.objects.append(model)
    self.graphics[model.name] = ComputeGraphics(self.ctx, model, material)

def _update_matrix(self):
    self.primitives = []

    for i, (name, graphics) in enumerate(self.graphics.items()):
        graphics.create_primitive(self.primitives)
        graphics.create_transformation_matrix(self.models_f, i)
        graphics.create_inverse_transformation_matrix(self.inv_f, i)
        graphics.create_material_matrix(self.mats_f, i)

def _matrix_to_ssbo(self):
    self.raytracer.matrix_to_ssbo(self.models_f, 0)
    self.raytracer.matrix_to_ssbo(self.inv_f, 1)
    self.raytracer.matrix_to_ssbo(self.mats_f, 2)
    self.raytracer.primitives_to_ssbo(self.primitives, 3)


def start(self):
    print("Start!")
    self.primitives = []
    n = len(self.objects)
    self.models_f = np.zeros((n, 16), dtype='f4')
    self.inv_f = np.zeros((n, 16), dtype='f4')
    self.mats_f = np.zeros((n, 4), dtype='f4')

    self._update_matrix()
    self._matrix_to_ssbo()

def render(self):
    self.time += 0.01
    for obj in self.objects:
        if (obj.animated):
            obj.rotation += glm.vec3(0.8, 0.6, 0.4) 
            obj.position.x += math.sin(self.time) * 0.01

    if (self.raytracer is not None):
        self._update_matrix()
        self._matrix_to_ssbo()
        self.raytracer.run()
            
def on_resize(self, width, height):
    super().on_resize(width, height)
    self.width, self.height = width, height
    self.camera.aspect = width / height