import glm
import math
from .ray import Ray
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
        self.view = self.camera.get_view_matrix_rotated()


    def add_object(self, obj, material=None):
        self.objects.append(obj)
        # Create graphics for this object
        self.graphics[obj.name] = Graphics(self.ctx, obj, material)

    def remove_object(self, obj):
        if obj in self.objects:
            self.objects.remove(obj)
            if obj.name in self.graphics:
                del self.graphics[obj.name]

    def add_object_at_position(self, obj_class, position, material=None, hittable=True, **kwargs):
        """Create and add a new object at the given position"""
        # Ensure hittable is passed to the object constructor
        if 'hittable' not in kwargs:
            kwargs['hittable'] = hittable

        obj = obj_class(position=position, **kwargs)
        success = self.add_object(obj, material)
        return obj if success else False

    def get_selected_object(self):
        return getattr(self, 'selected_object', None)

    def set_selected_object(self, obj):
        self.selected_object = obj

        
    def start(self):
        print("Start!")

    def render(self):
        # Update projection and view matrices each frame to reflect camera changes
        self.projection = self.camera.get_perspective_matrix()
        self.view = self.camera.get_view_matrix_rotated()

        self.time += 0.01
        for obj in self.objects:
            if (obj.animated):
                obj.rotation += glm.vec3(0.8, 0.6, 0.4)
                obj.position.x += math.sin(self.time) * 0.01

            model = obj.get_model_matrix()
            mvp = self.projection * self.view * model
            self.graphics[obj.name].render({"Mvp": mvp})
        
                
    def on_mouse_click(self, u, v):
        current_ray = self.camera.raycast(u, v)
        max_bounces = 5
        bounce_count = 0

        while bounce_count < max_bounces:
            closest_hit = None
            closest_dist = float('inf')
            closest_normal = None

            for obj in self.objects:
                if hasattr(obj, 'hittable') and not obj.hittable:
                    continue  # Skip non-hittable objects like floor

                result = obj.check_hit(current_ray.origin, current_ray.direction)
                if isinstance(result, tuple) and len(result) >= 4:
                    hit, dist, point, normal = result
                else:
                    hit, dist, point = result
                    normal = None

                if hit and dist > 1e-6 and dist < closest_dist:  # Avoid self-intersection with small offset
                    closest_hit = (obj, dist, point)
                    closest_dist = dist
                    closest_normal = normal

            if closest_hit:
                obj, dist, point = closest_hit
                if closest_normal is not None:
                    print(f"Bounce {bounce_count}: Hit {obj.name} (dist: {dist:.2f}), normal: {closest_normal}")

                    # Compute reflected ray
                    reflected_direction = current_ray.reflect(closest_normal)
                    # Offset origin slightly to avoid immediate self-intersection
                    reflected_origin = point + glm.normalize(reflected_direction) * 1e-6
                    current_ray = Ray(reflected_origin, reflected_direction)
                    bounce_count += 1
                else:
                    print(f"Hit {obj.name} (dist: {dist:.2f}) but no normal available")
                    break
            else:
                if bounce_count > 0:
                    print(f"No more hits after {bounce_count} bounces")
                else:
                    print(f"No hit at ({u:.3f}, {v:.3f})")
                break

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
    def __init__(self, ctx, camera, width, height, output_model, output_material, max_objects=100):
       self.ctx = ctx
       self.camera = camera
       self.width = width
       self.height = height
       self.max_objects = max_objects  # Nuevo: límite máximo de objetos (default 100)
       self.raytracer = None

       self.output_graphics = Graphics(ctx, output_model, output_material)
       self.raytracer = RayTracerGPU(ctx, camera, width, height, self.output_graphics)

       self._needs_buffer_update = False  # Flag para optimización: actualizar buffers solo cuando cambian objetos
       self._cached_primitives = None  # Cache para evitar reconstruir BVH innecesariamente

       super().__init__(self.ctx, self.camera)

    def add_object(self, model, material):
        if len(self.objects) >= self.max_objects:  # Validación: límite de objetos alcanzado
            return False

        self.objects.append(model)
        self.graphics[model.name] = ComputeGraphics(self.ctx, model, material)
        self._needs_buffer_update = True  # Marcar para actualizar GPU buffers
        return True

    def remove_object(self, model):
        if model in self.objects:
            self.objects.remove(model)
            if model.name in self.graphics:
                del self.graphics[model.name]
            # Forzar actualización de buffers cuando se elimina objeto
            self._needs_buffer_update = True
            return True
        return False

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

    def update_gpu_buffers(self):
        """Update GPU buffers when objects list changes"""
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
            # Actualizar buffers solo si cambiaron los objetos
            if self._needs_buffer_update:
                self.update_gpu_buffers()
                self._needs_buffer_update = False
                # Reset primitive cache
                self._cached_primitives = None

            self._update_matrix()
            self._matrix_to_ssbo()
            self.raytracer.run()
                
    def on_resize(self, width, height):
        super().on_resize(width, height)
        self.width, self.height = width, height
        self.camera.aspect = width / height
