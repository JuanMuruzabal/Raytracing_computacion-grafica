import pyglet
import moderngl
import glm
import math
import numpy as np
from .ui_overlay import SimpleGUI

class Window(pyglet.window.Window):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ctx = moderngl.create_context()
        self.scene = None
        self.set_minimum_size(400, 300)
        self.keys = set()
        self.selected_object = None
        self.is_dragging_object = False
        self.is_moving_camera = False
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.edit_mode = "camera"  # "camera" or "object"
        self.current_tool = "camera"  # tool del panel: "camera", "select", "add_cube", "delete"
        self.current_cube_index = -1  # índice del cubo seleccionado (-1 = ninguno seleccionado)
        self.showing_menu = False
        self.gui = SimpleGUI(self.ctx, kwargs.get('width', 800), kwargs.get('height', 600), self)
        pyglet.clock.schedule_interval(self.update, 1/60.0)

        # No sphere materials needed - using direct OBB

    def on_draw(self):
        # Clear full window
        self.clear()
        self.ctx.clear(0.1, 0.1, 0.1)

        # Set viewport for 3D scene (left side)
        if self.gui:
            scene_viewport = self.gui.get_scene_viewport()
            self.ctx.viewport = scene_viewport

        # Enable depth test for 3D scene
        self.ctx.enable(moderngl.DEPTH_TEST)

        # Verificar si hay cambios en la textura para actualizar raytracer
        if hasattr(self.gui, 'side_panel') and self.gui.side_panel._gpu_texture_ready == False:
            if self.scene and hasattr(self.scene, 'raytracer'):
                current_texture = self.gui.side_panel.get_current_texture()
                self.scene.raytracer.set_texture(current_texture)
                self.gui.side_panel._gpu_texture_ready = True

        # Render 3D scene
        if self.scene:
            self.scene.render()

        # Render UI panel (this handles its own viewport)
        if self.gui:
            self.gui.render()

        # No need to render selection spheres - using direct OBB hit detection

    def on_resize(self, width, height):
        super().on_resize(width, height)
        if self.scene:
            # Calculate scene viewport dimensions (accounting for side panel on right)
            panel_width_ratio = 0.25
            scene_width = int(width * (1 - panel_width_ratio))
            scene_height = height
            self.scene.on_resize(scene_width, scene_height)

    def on_key_press(self, symbol, modifiers):
        self.keys.add(symbol)

        # Handle hotkeys
        if symbol == pyglet.window.key.DELETE:
            self._delete_selected_object()
        elif symbol == pyglet.window.key.C and self.current_tool == "select":
            self._cycle_cube_selection()
        elif symbol == pyglet.window.key.ENTER or symbol == pyglet.window.key.RETURN:
            if self.current_tool == "delete" and self.selected_object:
                self.scene.remove_object(self.selected_object)
                self.selected_object = None
                self.current_cube_index = -1
                print("Object deleted successfully")
                if hasattr(self.scene, 'update_gpu_buffers'):
                    self.scene.update_gpu_buffers()
        elif symbol == pyglet.window.key.NUM_1:
            self._add_cube_at_camera()
        elif symbol == pyglet.window.key.NUM_2:
            self._add_sphere_at_camera()

    def _handle_panel_click(self, panel_x_ndc, panel_y_ndc):
        """Handle clicks in the panel area"""
        if not self.gui or not hasattr(self.gui, 'side_panel'):
            return

        tool = self.gui.side_panel.handle_click(panel_x_ndc, panel_y_ndc)
        if tool:
            print(f"Panel tool selected: {tool}")
            self.current_tool = tool
            self.gui.side_panel.set_selected_tool(tool)

            if tool == "camera":
                # Camera mode: deseleccionar todos los cubos para permitir movimiento de cámara
                self.selected_object = None
                self.current_cube_index = -1
                print("Camera mode activated - all objects deselected")
            elif tool == "select":
                # Select mode: activado, usar tecla C para cyclear objetos
                print("Select mode activated - use C key to cycle through objects")
            elif tool == "add_cube":
                if self.scene and hasattr(self.scene, 'add_object_at_position'):
                    success = self._add_cube_at_screen_center()
                    if success:
                        # Calcular y mostrar objetos restantes después de agregar
                        remaining = self.scene.max_objects - len(self.scene.objects) if hasattr(self.scene, 'max_objects') else "unlimited"
                        print(f"Cube added at screen center ({remaining} objects remaining)")
                    else:
                        # Mensaje cuando se alcanzó el límite máximo
                        print("Maximum objects limit reached, cannot add more cubes (0 remaining)")
                else:
                    self._add_cube_at_screen_center()
                    print("Cube added at screen center")
            elif tool == "delete":
                # Delete mode: esperar por ENTER con objeto seleccionado
                print("Delete mode activated - select object and press ENTER to delete")

    def _add_cube_at_click(self, screen_x, screen_y):
        """Add a cube at the clicked position in 3D space"""
        if not self.scene or not self.scene.camera:
            return

        # Convert screen coordinates to ray
        scene_viewport = self.gui.get_scene_viewport()
        scene_x, scene_y, scene_width, scene_height = scene_viewport

        # Get normalized coordinates in scene viewport
        u = (screen_x - scene_x) / scene_width
        v = (screen_y - scene_y) / scene_height

        # Cast ray into scene
        ray = self.scene.camera.raycast(u, v)

        # Find intersection with ground plane (y = -3, like the floor quad)
        ground_y = -3.0

        # Protect against division by zero when ray is parallel to ground
        if abs(ray.direction.y) < 0.001:
            # Ray is nearly horizontal, place cube at a fixed distance in front of camera
            intersection_point = ray.origin + ray.direction * 2.0 + glm.vec3(0, -2.0, 0)
        else:
            t = (ground_y - ray.origin.y) / ray.direction.y

            if t > 0:
                # Calculate intersection point
                intersection_point = ray.origin + t * ray.direction
            else:
                # Ray is pointing upwards, place cube at fixed distance
                intersection_point = ray.origin + ray.direction * 2.0 + glm.vec3(0, -2.0, 0)

        # Create cube at intersection point
        cube_name = f"Cube_{len(self.scene.objects)}"
        cube = self.scene.add_object_at_position(
            self._get_cube_class(),
            intersection_point,
            self._get_default_material(),
            name=cube_name,
            scale=(1, 1, 1)
        )

        # Update GPU buffers if needed (though now handled by flag)
        if hasattr(self.scene, 'update_gpu_buffers'):
            self.scene.update_gpu_buffers()

        return cube

    def on_key_release(self, symbol, modifiers):
        if symbol in self.keys:
            self.keys.remove(symbol)

    def on_mouse_press(self, x, y, button, modifiers):
        if self.scene is None:
            return

        if button == pyglet.window.mouse.LEFT:
            # Check if click is in panel area (right side)
            panel_width_pixels = int(self.width * 0.25)
            scene_width_pixels = self.width - panel_width_pixels

            if x >= scene_width_pixels:
                # Click in panel - convert to panel coordinates and handle button clicks
                panel_x_ndc = ((x - scene_width_pixels) / panel_width_pixels) * 2 - 1
                panel_y_ndc = (y / self.height) * 2 - 1
                self._handle_panel_click(panel_x_ndc, panel_y_ndc)

        elif button == pyglet.window.mouse.RIGHT:
            self.is_moving_camera = True
            self.set_mouse_visible(False)
            self.set_exclusive_mouse(True)

    def on_mouse_release(self, x, y, button, modifiers):
        if button == pyglet.window.mouse.LEFT:
            if hasattr(self, 'is_dragging_object') and self.is_dragging_object:
                self.is_dragging_object = False
                self.selected_object = None
                self.set_mouse_visible(True)
                self.set_exclusive_mouse(False)
        elif button == pyglet.window.mouse.RIGHT:
            self.is_moving_camera = False
            self.set_mouse_visible(True)
            self.set_exclusive_mouse(False)

    def on_mouse_motion(self, x, y, dx, dy):
        # Camera rotation with right mouse button
        if hasattr(self, 'is_moving_camera') and self.is_moving_camera and self.scene and self.scene.camera:
            sensitivity = 0.002
            cam = self.scene.camera
            cam.rotate(-dx * sensitivity, -dy * sensitivity)

    def _handle_menu_choice(self, choice):
        if choice == 'cube':
            self._add_cube_at_camera()
            print(f"Cube added at {self.scene.camera.position + self.scene.camera.forward * 3.0}")
        elif choice == 'sphere':
            self._add_sphere_at_camera()
            print(f"Sphere added at {self.scene.camera.position + self.scene.camera.forward * 3.0}")

    def update(self, dt):
        move_speed = 0.1
        if self.scene and self.scene.camera:
            cam = self.scene.camera
            direction = glm.vec3(0)
            if pyglet.window.key.W in self.keys:
                direction += cam.forward
            if pyglet.window.key.S in self.keys:
                direction -= cam.forward
            if pyglet.window.key.A in self.keys:
                direction -= cam.right
            if pyglet.window.key.D in self.keys:
                direction += cam.right
            if pyglet.window.key.Q in self.keys:
                direction += glm.vec3(0, -1, 0)  # Down
            if pyglet.window.key.E in self.keys:
                direction += glm.vec3(0, 1, 0)   # Up

            # Simple movement logic
            if direction == glm.vec3(0):
                return  # No movement input

            if self.selected_object and self._is_object_movable(self.selected_object):
                # If object is selected, move the object
                self.selected_object.position += direction * move_speed
            else:
                # If no object selected, move the camera
                cam.position += direction * move_speed

            # Force GPU scene re-render
            if hasattr(self.scene, 'raytracer') and self.scene.raytracer:
                try:
                    self.scene.raytracer.run()
                except:
                    pass  # Ignore render errors



    def _add_cube_at_camera(self):
        if not self.scene or not self.scene.camera:
            return

        # Calculate position in front of camera
        cam = self.scene.camera
        spawn_distance = 3.0
        spawn_pos = cam.position + cam.forward * spawn_distance

        # Create cube with default properties
        cube_name = f"Cube_{len(self.scene.objects)}"
        cube = self.scene.add_object_at_position(
            self._get_cube_class(),
            spawn_pos,
            self._get_default_material(),
            name=cube_name,
            scale=(1, 1, 1)
        )

        # Update GPU buffers if needed
        if hasattr(self.scene, 'update_gpu_buffers'):
            self.scene.update_gpu_buffers()

    def _add_sphere_at_camera(self):
        if not self.scene or not self.scene.camera:
            return

        # Calculate position in front of camera
        cam = self.scene.camera
        spawn_distance = 3.0
        spawn_pos = cam.position + cam.forward * spawn_distance

        # Create sphere with default properties
        sphere_name = f"Sphere_{len(self.scene.objects)}"
        sphere = self.scene.add_object_at_position(
            self._get_sphere_class(),
            spawn_pos,
            self._get_default_material(),
            name=sphere_name,
            radius=1.0
        )

        # Update GPU buffers if needed
        if hasattr(self.scene, 'update_gpu_buffers'):
            self.scene.update_gpu_buffers()

    def _delete_selected_object(self):
        if self.selected_object and self.scene:
            self.scene.remove_object(self.selected_object)
            self.selected_object = None

    def _get_cube_class(self):
        from .cube import Cube
        return Cube

    def _get_sphere_class(self):
        from .sphere_model import Sphere
        return Sphere

    def _is_object_movable(self, obj):
        """Check if an object can be moved (only cubes, not floor or sprites)"""
        if not obj or not hasattr(obj, 'name'):
            return False

        # Can move objects whose names start with "Cube"
        return obj.name.startswith("Cube")

    def _get_default_material(self):
        """Crear material por defecto o marcar para usar textura"""
        # Verificar si hay textura seleccionada en el panel
        if hasattr(self.gui, 'side_panel') and self.gui.side_panel.get_current_texture():
            # Crear material especial que indica uso de textura
            # Usar reflectividad negativa como flag para textura
            try:
                from .material import StandardMaterial
                shader = self._create_basic_shader()
                if shader:
                    material = StandardMaterial(shader, None, reflectivity=-0.5)  # Flag negativo para textura
                    return material
            except:
                pass
            return None
        else:
            # Usar material por defecto sin textura
            if hasattr(self, '_default_material'):
                return self._default_material

            # Try to get a shader from existing materials in the scene
            shader = None
            if self.scene and len(self.scene.objects) > 0:
                # Try to get shader from an existing object
                for obj_name, graphics in self.scene.graphics.items():
                    if hasattr(graphics, 'material') and graphics.material and hasattr(graphics.material, 'shader_program'):
                        shader = graphics.material.shader_program
                        break

            if shader is None:
                # Fallback: try to create a basic shader
                try:
                    shader = self._create_basic_shader()
                except:
                    # If all else fails, return None and let the system handle it
                    return None

            # Create a simple white material
            try:
                from .material import StandardMaterial
                from .texture import Texture

                albedo = Texture("u_texture", 1, 1, 3, None, (255, 255, 255))
                self._default_material = StandardMaterial(shader, albedo, reflectivity=0.1)
                return self._default_material
            except:
                return None

    def _add_cube_at_screen_center(self):
        """Add a cube at the center of the screen view"""
        if not self.gui:
            return

        # Get the screen center coordinates of the scene viewport
        scene_viewport = self.gui.get_scene_viewport()
        center_x = scene_viewport[0] + scene_viewport[2] / 2
        center_y = scene_viewport[1] + scene_viewport[3] / 2

        # Use the existing method with center coordinates
        return self._add_cube_at_click(center_x, center_y)

    def _cycle_cube_selection(self, direction=1):
        """Cycle through available cubes"""
        if not self.scene or not self.scene.objects:
            return

        # Get all cubes
        cubes = [obj for obj in self.scene.objects if self._is_object_movable(obj)]

        if not cubes:
            print("No cubes available to select")
            self.selected_object = None
            self.current_cube_index = -1
            return

        # Handle -1 index (no selection)
        if self.current_cube_index == -1 and direction == -1:
            self.current_cube_index = len(cubes) - 1  # Wrap to last
        elif self.current_cube_index == -1 and direction == 1:
            self.current_cube_index = 0
        else:
            # Cycle
            self.current_cube_index = (self.current_cube_index + direction) % len(cubes)

        self.selected_object = cubes[self.current_cube_index]

        print(f"Cube selected: {self.selected_object.name if hasattr(self.selected_object, 'name') else 'unnamed'} ({self.current_cube_index + 1}/{len(cubes)})")

    def _create_basic_shader(self):
        """Create a basic shader as fallback"""
        from .shader_program import ShaderProgram
        return ShaderProgram(self.ctx, 'shaders/basic.vert', 'shaders/basic.frag')

    def set_scene(self, scene):
        self.scene = scene
        scene.start()


    def _update_raytracer_texture(self):
        """Actualiza la textura del raytracer cuando cambia la selección en la UI"""
        if hasattr(self, 'gui') and self.gui and hasattr(self.gui, 'side_panel') and hasattr(self.scene, 'raytracer'):
            current_texture = self.gui.side_panel.get_current_texture()
            self.scene.raytracer.set_texture(current_texture)

    def run(self):
        pyglet.app.run()
