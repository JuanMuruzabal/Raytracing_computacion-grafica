import pyglet
import moderngl
import glm
import math
import numpy as np
import time
from .ui_overlay import SimpleGUI

class Window(pyglet.window.Window):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ctx = moderngl.create_context()
        self.scene = None
        self.set_minimum_size(400, 300)
        self.keys = set()
        self.selected_objects = []  # Lista para selección múltiple
        self.is_dragging_selection = False  # Para selección por arrastre
        self.selection_start_x = 0
        self.selection_start_y = 0
        self.is_dragging_object = False
        self.is_moving_camera = False
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.edit_mode = "camera"  # "camera" or "object"
        self.current_tool = "camera"  # tool del panel: "camera", "select", "add_cube", "delete"
        self.current_cube_index = -1  # índice del cubo seleccionado (-1 = ninguno seleccionado)
        self.showing_menu = False
        self.gui = SimpleGUI(self.ctx, kwargs.get('width', 800), kwargs.get('height', 600), self)
        # Debugging for selection rectangle (throttled prints)
        self._debug_selection = True
        self._last_debug_print = 0.0

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

                # Aplicar textura a TODOS los objetos que tienen reflectividad negativa (flag de textura)
                if current_texture:
                    # Buscar objetos con flag de textura (reflectivity < 0) y marcarlos
                    textured_objects = 0
                    for obj in self.scene.objects:
                        if hasattr(obj, 'material') and hasattr(obj.material, 'reflectivity'):
                            if obj.material.reflectivity < 0:  # Ya tiene flag de textura
                                obj._has_texture = True
                                textured_objects += 1
                    if textured_objects > 0:
                        print(f"Textura aplicada a {textured_objects} objetos (todos los que tienen flag de textura)")
                elif not current_texture:
                    # Remover textura: cambiar reflectividad a positiva para objetos que tenían textura
                    for obj in self.scene.objects:
                        if hasattr(obj, '_has_texture') and obj._has_texture:
                            if hasattr(obj, 'material') and hasattr(obj.material, 'reflectivity'):
                                obj.material.reflectivity = abs(obj.material.reflectivity)  # Hacer positiva
                            obj._has_texture = False
                    print("Textura removida de todos los objetos")

                # Actualizar buffers GPU después de cambiar materiales
                if hasattr(self.scene, 'update_gpu_buffers'):
                    self.scene.update_gpu_buffers()

                self.gui.side_panel._gpu_texture_ready = True

        # Render 3D scene
        if self.scene:
            self.scene.render()

        # Render selection rectangle if dragging
        if self.is_dragging_selection:
            self._render_selection_rectangle()

        # Render UI panel (this handles its own viewport)
        if self.gui:
            self.gui.render()



        # No need to render selection spheres - using direct OBB hit detection

    def on_resize(self, width, height):
        super().on_resize(width, height)
        if self.scene and self.gui:
            # Get current panel width ratio from GUI
            panel_width_ratio = self.gui.side_panel.panel_width_ratio
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
            if self.current_tool == "delete" and self.selected_objects:
                for obj in self.selected_objects[:]:  # Copia para evitar problemas de modificación durante iteración
                    self.scene.remove_object(obj)
                self.selected_objects = []
                self.current_cube_index = -1
                print(f"{len(self.selected_objects)} objects deleted successfully")
                if hasattr(self.scene, 'update_gpu_buffers'):
                    self.scene.update_gpu_buffers()
        elif symbol == pyglet.window.key.NUM_1:
            self._add_cube_at_camera()
        elif symbol == pyglet.window.key.NUM_2:
            self._add_sphere_at_camera()
        elif symbol == pyglet.window.key.R:
            # Cambiar a modo rotación
            self.current_tool = "rotate"
            self.gui.side_panel.set_selected_tool("rotate")
            print("Rotate mode activated - use WASD to rotate selected objects")
        elif symbol == pyglet.window.key.T:
            # Cambiar a modo escala
            self.current_tool = "scale"
            self.gui.side_panel.set_selected_tool("scale")
            print("Scale mode activated - use WASD to scale selected objects")
        elif symbol == pyglet.window.key.LEFT:
            # Reducir ancho del panel (solo si no hay modificadores)
            if modifiers == 0 and self.gui:
                current_ratio = self.gui.side_panel.panel_width_ratio
                new_ratio = max(0.2, current_ratio - 0.05)  # Reducir en incrementos de 5%
                self.gui.set_panel_width_ratio(new_ratio)
                print(f"Panel width decreased to {new_ratio:.2f} ({new_ratio*100:.0f}%)")
        elif symbol == pyglet.window.key.RIGHT:
            # Aumentar ancho del panel (solo si no hay modificadores)
            if modifiers == 0 and self.gui:
                current_ratio = self.gui.side_panel.panel_width_ratio
                new_ratio = min(0.5, current_ratio + 0.05)  # Aumentar en incrementos de 5%
                self.gui.set_panel_width_ratio(new_ratio)
                print(f"Panel width increased to {new_ratio:.2f} ({new_ratio*100:.0f}%)")

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
                self.selected_objects = []
                self.current_cube_index = -1
                print("Camera mode activated - all objects deselected")
            elif tool == "select":
                # Select mode: activado, usar tecla C para cyclear objetos
                print("Select mode activated - use C key to cycle through objects")
            elif tool == "rotate":
                # Rotate mode: usar WASD para rotar objetos seleccionados
                print("Rotate mode activated - use WASD to rotate selected objects")
            elif tool == "scale":
                # Scale mode: usar WASD para escalar objetos seleccionados
                print("Scale mode activated - use WASD to scale selected objects")
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
        if self.scene is None or not self.gui:
            return

        # Convert screen coordinates to NDC for GUI handling
        x_ndc = (x / self.width) * 2 - 1
        y_ndc = (y / self.height) * 2 - 1

        # First, let the GUI handle mouse events (for resizing, etc.)
        if self.gui.handle_mouse_press(x_ndc, y_ndc, button):
            return  # GUI handled the event

        if button == pyglet.window.mouse.LEFT:
            # Check if click is in panel area (right side)
            panel_width_ratio = self.gui.side_panel.panel_width_ratio
            panel_width_pixels = int(self.width * panel_width_ratio)
            scene_width_pixels = self.width - panel_width_pixels

            if x >= scene_width_pixels:
                # Click in panel - convert to panel coordinates and handle button clicks
                panel_x_ndc = ((x - scene_width_pixels) / panel_width_pixels) * 2 - 1
                panel_y_ndc = (y / self.height) * 2 - 1
                self._handle_panel_click(panel_x_ndc, panel_y_ndc)
            else:
                # Click in scene area - handle selection
                if self.current_tool == "select":
                    self.is_dragging_selection = True
                    self.selection_start_x = x
                    self.selection_start_y = y
                    # Initialize current mouse tracking so the rectangle starts exactly at the click
                    self._current_mouse_x = x
                    self._current_mouse_y = y
                    print("Starting selection drag")

        elif button == pyglet.window.mouse.RIGHT:
            self.is_moving_camera = True
            self.set_mouse_visible(False)
            self.set_exclusive_mouse(True)

    def on_mouse_release(self, x, y, button, modifiers):
        # Convert screen coordinates to NDC for GUI handling
        x_ndc = (x / self.width) * 2 - 1
        y_ndc = (y / self.height) * 2 - 1

        # Let the GUI handle mouse release events first
        if self.gui and self.gui.handle_mouse_release(x_ndc, y_ndc, button):
            return  # GUI handled the event

        if button == pyglet.window.mouse.LEFT:
            if self.is_dragging_selection:
                # Finalizar selección por arrastre
                self.is_dragging_selection = False
                self._finish_selection_drag(x, y)
            elif hasattr(self, 'is_dragging_object') and self.is_dragging_object:
                self.is_dragging_object = False
                self.selected_object = None
                self.set_mouse_visible(True)
                self.set_exclusive_mouse(False)
        elif button == pyglet.window.mouse.RIGHT:
            self.is_moving_camera = False
            self.set_mouse_visible(True)
            self.set_exclusive_mouse(False)

    def on_mouse_motion(self, x, y, dx, dy):
        # Convert screen coordinates to NDC for GUI handling
        x_ndc = (x / self.width) * 2 - 1
        y_ndc = (y / self.height) * 2 - 1

        # Let the GUI handle mouse motion events first (for resizing)
        if self.gui and self.gui.handle_mouse_motion(x_ndc, y_ndc, dx, dy):
            return  # GUI handled the event

        # Track current mouse position for selection rectangle rendering
        if self.is_dragging_selection:
            self._current_mouse_x = x
            self._current_mouse_y = y

        # Camera rotation with right mouse button
        if hasattr(self, 'is_moving_camera') and self.is_moving_camera and self.scene and self.scene.camera:
            sensitivity = 0.002
            cam = self.scene.camera
            cam.rotate(-dx * sensitivity, -dy * sensitivity)

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        """Handle mouse drag (pyglet sends this while a button is held). Update
        drag selection coordinates and support camera rotation on right-button drag.
        """
        # Convert screen coordinates to NDC for GUI handling
        x_ndc = (x / self.width) * 2 - 1
        y_ndc = (y / self.height) * 2 - 1

        # Let GUI handle drag-like motion if it wants to (resizing, etc.)
        if self.gui and self.gui.handle_mouse_motion(x_ndc, y_ndc, dx, dy):
            return

        # Update current mouse position for selection rectangle while left-button dragging
        if self.is_dragging_selection and (buttons & pyglet.window.mouse.LEFT):
            self._current_mouse_x = x
            self._current_mouse_y = y

        # Camera rotation when right button is held (mirror on_mouse_motion behavior)
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
        rotate_speed = 0.05
        scale_speed = 0.1

        if self.scene and self.scene.camera:
            cam = self.scene.camera

            # Handle different tool modes
            if self.current_tool == "rotate" and self.selected_objects:
                # Rotate mode: apply rotation to selected objects
                for obj in self.selected_objects:
                    if self._is_object_movable(obj):
                        # Initialize rotation if not exists
                        if not hasattr(obj, 'rotation'):
                            obj.rotation = glm.vec3(0, 0, 0)

                        # Apply rotation based on keys
                        if pyglet.window.key.W in self.keys:
                            obj.rotation.x += rotate_speed  # Pitch up
                        if pyglet.window.key.S in self.keys:
                            obj.rotation.x -= rotate_speed  # Pitch down
                        if pyglet.window.key.A in self.keys:
                            obj.rotation.y += rotate_speed  # Yaw left
                        if pyglet.window.key.D in self.keys:
                            obj.rotation.y -= rotate_speed  # Yaw right
                        if pyglet.window.key.Q in self.keys:
                            obj.rotation.z += rotate_speed  # Roll counterclockwise
                        if pyglet.window.key.E in self.keys:
                            obj.rotation.z -= rotate_speed  # Roll clockwise

            elif self.current_tool == "scale" and self.selected_objects:
                # Scale mode: apply scaling to selected objects
                for obj in self.selected_objects:
                    if self._is_object_movable(obj):
                        # Initialize scale if not exists
                        if not hasattr(obj, 'scale'):
                            obj.scale = glm.vec3(1, 1, 1)

                        # Apply scaling based on keys
                        if pyglet.window.key.W in self.keys:
                            obj.scale.y += scale_speed  # Scale up in Y
                        if pyglet.window.key.S in self.keys:
                            obj.scale.y = max(0.1, obj.scale.y - scale_speed)  # Scale down in Y (min 0.1)
                        if pyglet.window.key.A in self.keys:
                            obj.scale.x = max(0.1, obj.scale.x - scale_speed)  # Scale down in X (min 0.1)
                        if pyglet.window.key.D in self.keys:
                            obj.scale.x += scale_speed  # Scale up in X
                        if pyglet.window.key.Q in self.keys:
                            obj.scale.z = max(0.1, obj.scale.z - scale_speed)  # Scale down in Z (min 0.1)
                        if pyglet.window.key.E in self.keys:
                            obj.scale.z += scale_speed  # Scale up in Z

            else:
                # Default movement mode (camera or object movement)
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

                if self.selected_objects and self.current_tool not in ["rotate", "scale"]:
                    # If objects are selected and not in rotate/scale mode, move all selected objects
                    for obj in self.selected_objects:
                        if self._is_object_movable(obj):
                            obj.position += direction * move_speed
                else:
                    # If no object selected or in camera mode, move the camera
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
        if self.selected_objects and self.scene:
            for obj in self.selected_objects[:]:  # Copia para evitar problemas de modificación durante iteración
                self.scene.remove_object(obj)
            self.selected_objects = []
            print(f"Deleted {len(self.selected_objects)} objects")

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
            # Reset GPU texture ready flag so texture gets applied to new objects
            self.gui.side_panel._gpu_texture_ready = False

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
        """Cycle through available cubes with multiple selection support"""
        if not self.scene or not self.scene.objects:
            return

        # Get all cubes
        cubes = [obj for obj in self.scene.objects if self._is_object_movable(obj)]

        if not cubes:
            print("No cubes available to select")
            self.selected_objects = []
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

        # For multiple selection, toggle the current cube in/out of selection
        current_cube = cubes[self.current_cube_index]
        if current_cube in self.selected_objects:
            self.selected_objects.remove(current_cube)
            print(f"Removed from selection: {current_cube.name} ({len(self.selected_objects)} objects selected)")
        else:
            self.selected_objects.append(current_cube)
            print(f"Added to selection: {current_cube.name} ({len(self.selected_objects)} objects selected)")

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

    def _render_selection_rectangle(self):
        """Render the selection rectangle during drag operation"""
        if not self.is_dragging_selection:
            return

        # Get current mouse position (we need to track it during motion)
        current_mouse_x = getattr(self, '_current_mouse_x', self.selection_start_x)
        current_mouse_y = getattr(self, '_current_mouse_y', self.selection_start_y)

        # Calculate rectangle bounds
        min_x = min(self.selection_start_x, current_mouse_x)
        max_x = max(self.selection_start_x, current_mouse_x)
        min_y = min(self.selection_start_y, current_mouse_y)
        max_y = max(self.selection_start_y, current_mouse_y)

        # Prefer drawing the rectangle in the scene viewport (left area) so it aligns
        # with where the user clicked (and accounts for the UI side panel).
        scene_viewport = None
        if hasattr(self, 'gui') and self.gui:
            try:
                scene_viewport = self.gui.get_scene_viewport()
            except Exception:
                scene_viewport = None

        # If we have a valid scene viewport, clamp the rectangle and convert
        # coordinates to NDC relative to that viewport. Otherwise fall back to
        # full-window coordinates.
        if scene_viewport:
            scene_x, scene_y, scene_width, scene_height = scene_viewport

            # Clamp the rectangle to the scene viewport so the overlay doesn't draw over the side panel
            min_x = max(min_x, scene_x)
            max_x = min(max_x, scene_x + scene_width)
            min_y = max(min_y, scene_y)
            max_y = min(max_y, scene_y + scene_height)

            # Convert to viewport-local NDC (-1..1)
            left = ((min_x - scene_x) / float(scene_width)) * 2.0 - 1.0
            right = ((max_x - scene_x) / float(scene_width)) * 2.0 - 1.0
            bottom = ((min_y - scene_y) / float(scene_height)) * 2.0 - 1.0
            top = ((max_y - scene_y) / float(scene_height)) * 2.0 - 1.0
        else:
            # Full-window fallback
            left = (min_x / float(self.width)) * 2.0 - 1.0
            right = (max_x / float(self.width)) * 2.0 - 1.0
            bottom = (min_y / float(self.height)) * 2.0 - 1.0
            top = (max_y / float(self.height)) * 2.0 - 1.0

        # Create rectangle vertices (counter-clockwise)
        vertices = np.array([
            left, bottom, 0.0,
            right, bottom, 0.0,
            right, top, 0.0,
            left, top, 0.0
        ], dtype='f4')

        # Indices for line loop
        indices = np.array([0, 1, 2, 3, 0], dtype='i4')

        # Create shader program for selection rectangle
        vertex_shader = """
        #version 330
        in vec3 in_pos;
        void main() {
            gl_Position = vec4(in_pos, 1.0);
        }
        """

        fragment_shader = """
        #version 330
        out vec4 out_color;
        void main() {
            out_color = vec4(0.0, 1.0, 0.0, 0.8);  // Semi-transparent green
        }
        """

        program = self.ctx.program(vertex_shader=vertex_shader, fragment_shader=fragment_shader)

        # Create buffers
        vbo = self.ctx.buffer(vertices.tobytes())
        ibo = self.ctx.buffer(indices.tobytes())

        # Create vertex array
        vao = self.ctx.vertex_array(program, [(vbo, '3f', 'in_pos')], ibo)

        # Set viewport to scene viewport (if available) so the NDC mapping is correct
        if scene_viewport:
            self.ctx.viewport = (int(scene_x), int(scene_y), int(scene_width), int(scene_height))
        else:
            self.ctx.viewport = (0, 0, self.width, self.height)

        # Lightweight throttled debug printing to help verify coordinates during drag
        if getattr(self, '_debug_selection', False):
            now = time.time()
            if now - getattr(self, '_last_debug_print', 0.0) > 0.2:  # print at most 5x/sec
                self._last_debug_print = now
                try:
                    print(f"[sel-debug] scene_viewport={scene_viewport} start=({self.selection_start_x},{self.selection_start_y}) current=({current_mouse_x},{current_mouse_y}) clamped=({min_x},{min_y})-({max_x},{max_y}) ndc=({left:.3f},{bottom:.3f})-({right:.3f},{top:.3f})")
                except Exception:
                    # Don't raise from debug prints
                    pass

        # Disable depth test for overlay
        self.ctx.disable(moderngl.DEPTH_TEST)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

        # Render the rectangle outline
        self.ctx.line_width = 2.0
        vao.render(moderngl.LINE_STRIP)

        # Clean up
        vao.release()
        ibo.release()
        vbo.release()
        program.release()

        # Re-enable depth test
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.disable(moderngl.BLEND)

    def _finish_selection_drag(self, end_x, end_y):
        """Finalizar selección por arrastre y seleccionar objetos dentro del rectángulo"""
        if not self.scene or not self.scene.camera:
            return

        # Calcular el rectángulo de selección
        min_x = min(self.selection_start_x, end_x)
        max_x = max(self.selection_start_x, end_x)
        min_y = min(self.selection_start_y, end_y)
        max_y = max(self.selection_start_y, end_y)

        # Si el rectángulo es muy pequeño, considerar como click simple
        if abs(max_x - min_x) < 5 and abs(max_y - min_y) < 5:
            print("Selection rectangle too small, treated as click")
            return

        # Limpiar selección anterior antes de nueva selección
        self.selected_objects = []
        self.current_cube_index = -1

        # Obtener viewport de la escena
        scene_viewport = self.gui.get_scene_viewport()
        scene_x, scene_y, scene_width, scene_height = scene_viewport

        # Matriz de proyección y vista para proyectar puntos 3D a 2D
        projection = self.scene.camera.get_perspective_matrix()
        view = self.scene.camera.get_view_matrix_rotated()
        vp_matrix = projection * view

        selected_count = 0

        # Verificar cada objeto movable
        for obj in self.scene.objects:
            if not self._is_object_movable(obj):
                continue

            # Compute object's clip-space position using full model matrix.
            # Using model * vec4(0,0,0,1) is more robust than trusting obj.position alone
            # (some objects may have non-zero local transforms).
            try:
                model_mat = obj.get_model_matrix()
            except Exception:
                # Fallback to using position if get_model_matrix is not available
                model_mat = glm.translate(glm.mat4(1.0), obj.position)

            obj_pos_4d = projection * view * model_mat * glm.vec4(0.0, 0.0, 0.0, 1.0)

            if obj_pos_4d.w > 0:  # Objeto está frente a la cámara
                # Normalizar a NDC (-1 a 1)
                screen_x_ndc = obj_pos_4d.x / obj_pos_4d.w
                screen_y_ndc = obj_pos_4d.y / obj_pos_4d.w

                # Convertir NDC a coordenadas de pantalla
                screen_x = scene_x + (screen_x_ndc + 1.0) * 0.5 * scene_width
                screen_y = scene_y + (screen_y_ndc + 1.0) * 0.5 * scene_height

                # Verificar si el objeto está dentro del rectángulo de selección
                # Instead of selecting based only on the object's origin, project
                # the object's model-space bounding box (unit cube corners) and
                # test if its screen-space bounding box intersects the
                # selection rectangle. This better matches what the user sees
                # when objects are scaled/rotated.
                try:
                    # Local unit-cube corners at +/-1 (matches Cube vertices)
                    corners = [glm.vec4(x, y, z, 1.0) for x in (-1.0, 1.0) for y in (-1.0, 1.0) for z in (-1.0, 1.0)]

                    screen_xs = []
                    screen_ys = []
                    any_in_front = False

                    mvp = projection * view * model_mat
                    for c in corners:
                        clip = mvp * c
                        if clip.w == 0:
                            continue
                        ndc_x = clip.x / clip.w
                        ndc_y = clip.y / clip.w
                        # track if any corner is in front of camera
                        if clip.w > 0:
                            any_in_front = True

                        sx = scene_x + (ndc_x + 1.0) * 0.5 * scene_width
                        sy = scene_y + (ndc_y + 1.0) * 0.5 * scene_height
                        screen_xs.append(sx)
                        screen_ys.append(sy)

                    if not screen_xs or not screen_ys:
                        inside = False
                        bbox = (0,0,0,0)
                    else:
                        sx_min = min(screen_xs)
                        sx_max = max(screen_xs)
                        sy_min = min(screen_ys)
                        sy_max = max(screen_ys)
                        bbox = (sx_min, sy_min, sx_max, sy_max)

                        # Test bbox intersection with selection rectangle
                        horiz_overlap = not (sx_max < min_x or sx_min > max_x)
                        vert_overlap = not (sy_max < min_y or sy_min > max_y)
                        inside = horiz_overlap and vert_overlap and any_in_front

                    if self._debug_selection:
                        try:
                            print(f"[sel-finish] {obj.name} bbox=({bbox[0]:.1f},{bbox[1]:.1f})-({bbox[2]:.1f},{bbox[3]:.1f}) inside={inside}")
                        except Exception:
                            pass

                    if inside:
                        if obj not in self.selected_objects:
                            self.selected_objects.append(obj)
                            selected_count += 1
                except Exception as e:
                    # If anything goes wrong with bbox test, fall back to center test
                    if self._debug_selection:
                        print(f"[sel-finish] bbox test error for {obj.name}: {e}")
                    inside = (min_x <= screen_x <= max_x and min_y <= screen_y <= max_y)
                    if inside:
                        if obj not in self.selected_objects:
                            self.selected_objects.append(obj)
                            selected_count += 1

        if selected_count > 0:
            print(f"Selected {selected_count} objects via drag selection ({len(self.selected_objects)} total selected)")
        else:
            print("No objects selected in drag area")



    def run(self):
        pyglet.app.run()
