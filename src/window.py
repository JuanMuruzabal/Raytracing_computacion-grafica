import pyglet
import moderngl
import glm

class Window(pyglet.window.Window):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ctx = moderngl.create_context()
        self.scene = None
        self.set_minimum_size(400, 300)
        self.keys = set()
        self.selected_object = None
        self.is_dragging = False
        pyglet.clock.schedule_interval(self.update, 1/60.0)

    def on_draw(self):
        self.clear()
        self.ctx.clear(0.1, 0.1, 0.1)
        self.ctx.enable(moderngl.DEPTH_TEST)
        if self.scene:
            self.scene.render()

    def on_resize(self, width, height):
        super().on_resize(width, height)
        if self.scene:
            self.scene.on_resize(width, height)

    def on_key_press(self, symbol, modifiers):
        self.keys.add(symbol)

    def on_key_release(self, symbol, modifiers):
        if symbol in self.keys:
            self.keys.remove(symbol)

    def on_mouse_press(self, x, y, button, modifiers):
        if self.scene is None:
            return
        
        u = x / self.width
        v = y / self.height
        self.scene.on_mouse_click(u,v)
        
        
        if button == pyglet.window.mouse.LEFT:
            obj = self.pick_object(x, y)
            if obj:
                self.selected_object = obj
                self.is_dragging = True

    def on_mouse_release(self, x, y, button, modifiers):
        if button == pyglet.window.mouse.LEFT:
            self.is_dragging = False
            self.selected_object = None

    def update(self, dt):
        move_speed = 0.1
        if self.scene and self.scene.camera:
            cam = self.scene.camera
            direction = glm.vec3(0)
            if pyglet.window.key.W in self.keys:
                direction += glm.vec3(0, 0, -1)
            if pyglet.window.key.S in self.keys:
                direction += glm.vec3(0, 0, 1)
            if pyglet.window.key.A in self.keys:
                direction += glm.vec3(-1, 0, 0)
            if pyglet.window.key.D in self.keys:
                direction += glm.vec3(1, 0, 0)
            if self.is_dragging and self.selected_object:
                # Mover objeto seleccionado
                self.selected_object.position += direction * move_speed
            else:
                # Mover cámara
                cam.position += direction * move_speed
                cam.update_view()

    def pick_object(self, x, y):
        # Raycasting simple: selecciona el objeto más cercano al centro de la pantalla
        if not self.scene or not self.scene.objects:
            return None
        # Convertir coordenadas de pantalla a mundo (simplificado)
        # Aquí simplemente seleccionamos el objeto más cercano al centro
        min_dist = float('inf')
        picked = None
        for obj in self.scene.objects:
            pos = obj.position
            dist = glm.length(pos - glm.vec3(0, 0, 0))
            if dist < min_dist:
                min_dist = dist
                picked = obj
        return picked

    def run(self):
        pyglet.app.run()
