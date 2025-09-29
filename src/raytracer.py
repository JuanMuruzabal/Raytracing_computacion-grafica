from .texture import Texture

class RayTracer:
    def __init__(self, camera, width, height):
        self.camera = camera
        self.width = width
        self.height = height
        self.framebuffer = Texture(width=width, height=height, channels_amount=4)
        
        self.camera.set_sky_colors(top=(16,150,222,255), bottom=(181,224,247,255))

    def trace_ray(self, ray, objects):
        for obj, material in objects:  # desempaqueta el tuple
            if obj.check_hit(ray.origin, ray.direction):
                return (255,0,0,255)
        height = ray.direction.y
        return self.camera.get_sky_gradient(height)  # Esta línea fue cambiada: ahora desempaqueta (obj, material) para evitar errores y retorna RGBA.

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
                if color == (255,0,0,255):
                    hit_count += 1
                else:
                    sky_count += 1
        print(f"[RayTracer] Frame rendered: {hit_count} HIT pixels (rojo), {sky_count} SKY pixels (gradiente)")  # Este método fue cambiado: ahora imprime el conteo de hits y sky pixels para depuración.

    def get_texture(self):
        return self.framebuffer.image_data
