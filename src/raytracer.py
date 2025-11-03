from .texture import Texture
from .bvh import BVH
from .shader_program import ComputeShaderProgram
import moderngl
import numpy as np

class RayTracer:
    def __init__(self, camera, width, height):
        self.camera = camera
        self.width = width
        self.height = height
        self.framebuffer = Texture(width=width, height=height, channels_amount=3)
        
        self.camera.set_sky_colors(top=(16,150,222), bottom=(181,224,247))

    def trace_ray(self, ray, objects):
        closest_dist = float("inf")
        hit_any = False
        for obj in objects:
            hit, dist, point = obj.check_hit(ray.origin, ray.direction)
            if hit and dist < closest_dist:
                closest_dist = dist
                hit_any = True

        if hit_any:
            return (255, 0, 0)

        height = ray.direction.y
        return self.camera.get_sky_gradient(height)


    def render_frame(self, objects):
        hit_count = 0
        sky_count = 0
        for y in range(self.height):
            for x in range(self.width):
                u = x / (self.width -1)
                v = y / (self.height -1)
                ray = self.camera.raycast(u, v)
                color = self.trace_ray(ray, objects)
                self.framebuffer.set_pixel(x,y,color)
                if color == (255,0,0):
                    hit_count += 1
                else:
                    sky_count += 1
        print(f"[RayTracer] Frame rendered: {hit_count} HIT pixels (rojo), {sky_count} SKY pixels (gradiente)")  # Este método fue cambiado: ahora imprime el conteo de hits y sky pixels para depuración.

    def get_texture(self):
        return self.framebuffer.image_data

class RayTracerGPU:
    def __init__(self, ctx, camera, width, height, output_graphics):
       self.ctx = ctx
       self.width, self.height = width, height
       self.camera = camera
       self.width = width
       self.height = height
       self.compute_shader = ComputeShaderProgram(self.ctx, "shaders/raytracer.comp")
       self.output_graphics = output_graphics

       self.texture_unit = 0
       self.output_texture = Texture("u_texture", self.width, self.height, 4, None, (255,255,255,255))
       self.output_graphics.update_texture("u_texture", self.output_texture.image_data)
       self.output_graphics.bind_to_image("u_texture", self.texture_unit, read=False, write=True)

       self.compute_shader.set_uniform('cameraPosition', self.camera.position)
       self.compute_shader.set_uniform('inverseViewMatrix', self.camera.get_inverse_view_matrix())
       self.compute_shader.set_uniform('fieldOfView', self.camera.fov)

       # Para texturas en objetos
       self._current_texture = None
       self._texture_unit = 1  # Unidad de textura diferente para objetos
       self._ogl_texture = None  # Referencia para mantener viva la textura OpenGL


    def resize(self, width, height):
        self.width, self.height = width, height
        self.output_texture = Texture("u_texture", width, height, 4, None, (255,255,255,255))
        self.output_graphics.update_texture("u_texture", self.output_texture.image_data)

    def matrix_to_ssbo(self, matrix, binding = 0):
        # Reutilizar buffer si existe y tiene el tamaño correcto
        if not hasattr(self, f'_buffer_{binding}') or getattr(self, f'_buffer_{binding}') is None:
            setattr(self, f'_buffer_{binding}', self.ctx.buffer(matrix.tobytes()))
        else:
            existing_buffer = getattr(self, f'_buffer_{binding}')
            matrix_bytes = matrix.tobytes()
            if len(matrix_bytes) <= existing_buffer.size:
                existing_buffer.write(matrix_bytes)
            else:
                # Buffer too small, create new one
                setattr(self, f'_buffer_{binding}', self.ctx.buffer(matrix_bytes))
        getattr(self, f'_buffer_{binding}').bind_to_storage_buffer(binding=binding)

    def primitives_to_ssbo(self, primitives, binding = 3):
        # Solo reconstruir BVH si cambió la lista de primitivos
        if not hasattr(self, '_cached_primitives') or self._cached_primitives != primitives:
            self.bvh_nodes = BVH(primitives)
            self.bvh_ssbo = self.bvh_nodes.pack_to_bytes()
            self._cached_primitives = primitives.copy() if hasattr(primitives, 'copy') else primitives[:]
        else:
            # TODO: Solo actualizar si cambió
            pass

        # Reutilizar buffer BVH
        if not hasattr(self, '_bvh_buffer'):
            self._bvh_buffer = self.ctx.buffer(self.bvh_ssbo)
        else:
            if len(self.bvh_ssbo) <= self._bvh_buffer.size:
                self._bvh_buffer.write(self.bvh_ssbo)
            else:
                self._bvh_buffer = self.ctx.buffer(self.bvh_ssbo)

        self._bvh_buffer.bind_to_storage_buffer(binding=binding)

    def set_texture(self, texture):
        """Establece la textura actual para samplear en el raytracer"""
        self._current_texture = texture
        if texture and hasattr(texture, 'image_data') and texture.image_data is not None:
            # Convertir textura a formato OpenGL y bind a unidad de textura
            # Los datos están en uint8 (0-255), convertir a float (0-1) para ModernGL
            img_data = texture.image_data.data.astype(np.float32) / 255.0
            self._ogl_texture = self.ctx.texture(
                size=(texture.width, texture.height),
                components=3,
                data=img_data.tobytes(),
                dtype='f4'  # float 4-bytes por componente
            )
            self._ogl_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
            self._ogl_texture.repeat_x = True
            self._ogl_texture.repeat_y = True
            self._ogl_texture.use(location=self._texture_unit)
            self.compute_shader.set_uniform('u_hasTexture', 1)
            self.compute_shader.set_uniform('u_selectedTexture', self._texture_unit)
        else:
            self._ogl_texture = None
            self.compute_shader.set_uniform('u_hasTexture', 0)

    def run(self):
        # Update camera uniforms with current camera state
        self.compute_shader.set_uniform('cameraPosition', self.camera.position)
        self.compute_shader.set_uniform('inverseViewMatrix', self.camera.get_inverse_view_matrix())

        # Ensure texture is bound if it exists
        if self._ogl_texture is not None:
            self._ogl_texture.use(location=self._texture_unit)

        groups_x = (self.width + 15) // 16
        groups_y = (self.height + 15) // 16

        self.compute_shader.run(groups_x, groups_y, groups_z=1)

        self.ctx.clear(0.0,0.0,0.0,1.0)
        self.output_graphics.render({"u_texture": self.texture_unit})
