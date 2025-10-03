from .texture import Texture

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
