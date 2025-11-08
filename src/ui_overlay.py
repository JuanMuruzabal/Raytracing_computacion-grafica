import moderngl
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from tkinter import filedialog, Tk
import os
from .texture import ImageData, Texture


class TextRenderer:
    def __init__(self, ctx):
        self.ctx = ctx
        self.texture_cache = {}
        
        # Shader para renderizar textos con textura
        vertex_shader = """
        #version 330
        in vec2 in_pos;
        in vec2 in_texcoord;
        out vec2 texcoord;
        void main() {
            gl_Position = vec4(in_pos, 0.0, 1.0);
            texcoord = in_texcoord;
        }
        """

        fragment_shader = """
        #version 330
        uniform sampler2D text_texture;
        uniform vec3 text_color;
        in vec2 texcoord;
        out vec4 out_color;
        void main() {
            float alpha = texture(text_texture, texcoord).r;
            out_color = vec4(text_color, alpha);
        }
        """

        self.program = self.ctx.program(vertex_shader=vertex_shader, fragment_shader=fragment_shader)

    def create_text_texture(self, text, font_size=32):
        """Crea una textura a partir de texto usando PIL"""
        cache_key = (text, font_size)
        if cache_key in self.texture_cache:
            return self.texture_cache[cache_key]
        
        # Crear imagen con PIL - usar fuente más grande
        try:
            # Intentar varias fuentes comunes
            for font_name in ["arial.ttf", "Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
                try:
                    font = ImageFont.truetype(font_name, font_size)
                    break
                except:
                    continue
            else:
                # Si ninguna funciona, usar default
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        # Calcular tamaño del texto
        dummy_img = Image.new('L', (1, 1))
        draw = ImageDraw.Draw(dummy_img)
        
        # Usar textbbox para obtener dimensiones precisas
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except:
            # Fallback para versiones antiguas de PIL
            text_width, text_height = draw.textsize(text, font=font)
        
        # Asegurar dimensiones mínimas
        text_width = max(text_width, 10)
        text_height = max(text_height, 10)
        
        # Crear imagen con el texto (con padding generoso)
        padding = 8
        img_width = text_width + padding * 2
        img_height = text_height + padding * 2
        
        img = Image.new('L', (img_width, img_height), color=0)
        draw = ImageDraw.Draw(img)
        
        # Dibujar texto centrado
        draw.text((padding, padding), text, fill=255, font=font)
        
        # Crear textura OpenGL
        texture = self.ctx.texture(img.size, 1, img.tobytes())
        texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
        
        self.texture_cache[cache_key] = (texture, text_width, text_height)
        return texture, text_width, text_height

    def render_text_at_position(self, text, x, y, color=(1, 1, 1), scale=1.0):
        """Renderiza texto en coordenadas NDC"""
        if not text:
            return
            
        # Usar fuente más grande para mejor calidad
        font_size = int(32 * scale)
        texture, text_width, text_height = self.create_text_texture(text, font_size)
        
        # Convertir tamaño de píxeles a NDC - ajustado para mejor visualización
        width_ndc = (text_width / 400.0) * scale
        height_ndc = (text_height / 400.0) * scale
        
        # Crear quad para el texto
        vertices = np.array([
            x, y, 0.0, 1.0,
            x + width_ndc, y, 1.0, 1.0,
            x + width_ndc, y + height_ndc, 1.0, 0.0,
            x, y + height_ndc, 0.0, 0.0
        ], dtype='f4')
        
        indices = np.array([0, 1, 2, 2, 3, 0], dtype='i4')
        
        vbo = self.ctx.buffer(vertices.tobytes())
        ibo = self.ctx.buffer(indices.tobytes())
        
        vao = self.ctx.vertex_array(
            self.program,
            [(vbo, '2f 2f', 'in_pos', 'in_texcoord')],
            ibo
        )
        
        # Configurar uniforms y renderizar
        texture.use(0)
        self.program['text_texture'].value = 0
        self.program['text_color'].value = color
        
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
        vao.render()


class Button:
    def __init__(self, text, x, y, width, height, color=(0.4, 0.4, 0.6, 1.0), hover_color=(0.6, 0.6, 0.8, 1.0)):
        self.text = text
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color
        self.hover_color = hover_color
        self.is_hovered = False
        self.callback = None

    def contains_point(self, px, py):
        """Verificar si el punto (px, py) está dentro de los límites del botón"""
        return (self.x <= px <= self.x + self.width and
                self.y <= py <= self.y + self.height)

    def set_callback(self, callback):
        self.callback = callback


class SidePanel:
    def __init__(self, ctx, total_width, total_height, panel_width_ratio=0.35, window=None):
        self.ctx = ctx
        self.total_width = total_width
        self.total_height = total_height
        self.panel_width_ratio = panel_width_ratio
        self.window = window
        self.text_renderer = TextRenderer(ctx)
        self.selected_tool = "camera"

        # Calcular factor de escala base
        self.base_scale = self._calculate_base_scale()

        # Inicializar posiciones para el sistema de columnas
        self.selector_y = 0.7  # Mover más arriba para dar espacio a las columnas
        self.texture_y = 0.4
        self.physics_y = 0.1
        
        # Definir posiciones de columnas
        self.col1_x = -0.90  # Primera columna (extrema izquierda)
        self.col2_x = -0.60  # Segunda columna
        self.col3_x = -0.40  # Tercera columna
        self.col4_x = -0.26  # Cuarta columna

        # Widget para seleccionar objetos
        selector_height = 0.15
        self.left_arrow = Button("<", -0.8, self.selector_y, 0.3, selector_height, color=(0.4, 0.4, 0.4, 1.0))
        self.right_arrow = Button(">", 0.5, self.selector_y, 0.3, selector_height, color=(0.4, 0.4, 0.4, 1.0))
        self.current_object_info = "None selected"

        # Estado de textura
        self.current_texture_path = None
        self.current_texture = None
        self._processed_texture = None
        self._gpu_texture_ready = False

        # Estado del control de redimensionamiento
        self.is_resizing = False
        self.resize_handle_width = 0.02
        self.resize_start_x = 0

        # IMPORTANTE: Inicializar lista de botones vacía primero
        self.buttons = []
        
        # Crear TODOS los botones
        self._create_all_buttons()

    def _calculate_base_scale(self):
        """Calcular factor de escala base basado en el tamaño de la ventana"""
        base_width = 800
        base_height = 600
        width_scale = self.total_width / base_width
        height_scale = self.total_height / base_height
        geometric_mean = (width_scale * height_scale) ** 0.5
        base_scale = 1.0 / geometric_mean
        return max(0.6, min(1.0, base_scale))

    def _get_scaled_button_width(self):
        """Calcular ancho de botón escalado para layout de cuatro columnas"""
        base_width = 0.17  # Ancho reducido para acomodar cuatro columnas
        base_ratio = 0.35
        panel_scale = self.panel_width_ratio / base_ratio
        return base_width * panel_scale * self.base_scale

    def _get_scaled_button_height(self):
        """Calcular alto de botón escalado para layout compacto"""
        base_height = 0.12  # Altura reducida para mostrar más botones
        base_ratio = 0.35
        panel_scale = self.panel_width_ratio / base_ratio
        return base_height * panel_scale * self.base_scale

    def _get_scaled_button_spacing(self):
        """Calcular espaciado entre botones escalado"""
        base_spacing = 0.03
        base_ratio = 0.35
        panel_scale = self.panel_width_ratio / base_ratio
        return base_spacing * panel_scale * self.base_scale

    def _get_scaled_text_scale(self, base_scale):
        """Calcular factor de escala de texto"""
        base_ratio = 0.35
        panel_scale = self.panel_width_ratio / base_ratio
        # Usar un factor intermedio para mejor legibilidad
        return base_scale * panel_scale * self.base_scale * 1.7

    def _create_all_buttons(self):
        """Crear todos los botones del panel organizados en columnas"""
        button_width = self._get_scaled_button_width() * 0.8  # Reducir ancho para 5 columnas
        button_height = self._get_scaled_button_height() * 0.6  # Reducir altura aún más
        button_spacing = self._get_scaled_button_spacing() * 0.8  # Reducir espaciado

        # Limpiar lista de botones
        self.buttons = []

        # Posiciones base para las columnas
        col1_x = -0.9  # Primera columna (extrema izquierda)
        col2_x = -0.5  # Segunda columna
        col3_x = -0.1  # Tercera columna
        col4_x = 0.3  # Cuarta columna
        col5_x = 0.7  # Quinta columna

        # Posición Y inicial para todas las columnas
        start_y = 0.5
        button_y = start_y

        # COLUMNA 1 - Herramientas básicas
        self.camera_button = Button("CAMARA", col1_x, button_y, button_width, button_height,
                                  color=(0.25, 0.35, 0.5, 1.0), hover_color=(0.35, 0.5, 0.7, 1.0))
        self.buttons.append(self.camera_button)
        button_y -= button_height + button_spacing

        self.select_button = Button("SELECCION", col1_x, button_y, button_width, button_height,
                                  color=(0.3, 0.5, 0.3, 1.0), hover_color=(0.4, 0.65, 0.4, 1.0))
        self.buttons.append(self.select_button)
        button_y -= button_height + button_spacing

        self.rotate_button = Button("ROTACION", col1_x, button_y, button_width, button_height,
                                  color=(0.4, 0.4, 0.6, 1.0), hover_color=(0.55, 0.55, 0.75, 1.0))
        self.buttons.append(self.rotate_button)
        button_y -= button_height + button_spacing

        # COLUMNA 2 - Acciones de objetos
        button_y = start_y  # Reiniciar Y para la segunda columna
        
        self.scale_button = Button("ESCALA", col2_x, button_y, button_width, button_height,
                                 color=(0.6, 0.4, 0.4, 1.0), hover_color=(0.75, 0.55, 0.55, 1.0))
        self.buttons.append(self.scale_button)
        button_y -= button_height + button_spacing

        self.add_cube_button = Button("ADD", col2_x, button_y, button_width, button_height,
                                    color=(0.5, 0.35, 0.25, 1.0), hover_color=(0.7, 0.5, 0.35, 1.0))
        self.buttons.append(self.add_cube_button)
        button_y -= button_height + button_spacing

        self.delete_button = Button("DELETE", col2_x, button_y, button_width, button_height,
                                  color=(0.6, 0.25, 0.25, 1.0), hover_color=(0.8, 0.35, 0.35, 1.0))
        self.buttons.append(self.delete_button)

        # COLUMNA 3 - Textura y física
        button_y = start_y  # Reiniciar Y para la tercera columna
        
        self.select_texture_button = Button("TEXTURA", col3_x, button_y, button_width, button_height,
                                          color=(0.3, 0.4, 0.5, 1.0), hover_color=(0.4, 0.55, 0.65, 1.0))
        self.buttons.append(self.select_texture_button)
        button_y -= button_height + button_spacing
        
        self.none_texture_button = Button("CLEAR TXT", col3_x, button_y, button_width, button_height,
                                        color=(0.4, 0.3, 0.3, 1.0), hover_color=(0.6, 0.4, 0.4, 1.0))
        self.buttons.append(self.none_texture_button)
        button_y -= button_height + button_spacing

        self.toggle_gravity_button = Button("GRAVEDAD", col3_x, button_y, button_width, button_height,
                                          color=(0.2, 0.5, 0.2, 1.0), hover_color=(0.3, 0.7, 0.3, 1.0))
        self.buttons.append(self.toggle_gravity_button)
        
        # COLUMNA 4 - Controles de física
        button_y = start_y  # Reiniciar Y para la cuarta columna
        
        self.toggle_collision_button = Button("COLISION", col4_x, button_y, button_width, button_height,
                                           color=(0.2, 0.2, 0.5, 1.0), hover_color=(0.3, 0.3, 0.7, 1.0))
        self.buttons.append(self.toggle_collision_button)
        button_y -= button_height + button_spacing
        
        self.mode_button = Button("MODE", col4_x, button_y, button_width, button_height,
                                color=(0.5, 0.3, 0.5, 1.0), hover_color=(0.7, 0.4, 0.7, 1.0))
        self.buttons.append(self.mode_button)
        button_y -= button_height + button_spacing

        self.save_button = Button("SAVE", col4_x, button_y, button_width, button_height,
                                color=(0.3, 0.5, 0.3, 1.0), hover_color=(0.4, 0.7, 0.4, 1.0))
        self.buttons.append(self.save_button)
        
        # COLUMNA 5 - Controles de simulación
        button_y = start_y  # Reiniciar Y para la quinta columna
        
        self.load_button = Button("LOAD", col5_x, button_y, button_width, button_height,
                                color=(0.3, 0.3, 0.5, 1.0), hover_color=(0.4, 0.4, 0.7, 1.0))
        self.buttons.append(self.load_button)
        button_y -= button_height + button_spacing

        self.play_button = Button("PLAY", col5_x, button_y, button_width, button_height,
                                color=(0.2, 0.6, 0.2, 1.0), hover_color=(0.3, 0.8, 0.3, 1.0))
        self.buttons.append(self.play_button)
        button_y -= button_height + button_spacing
        
        self.pause_button = Button("PAUSE", col5_x, button_y, button_width, button_height,
                                color=(0.6, 0.6, 0.2, 1.0), hover_color=(0.8, 0.8, 0.3, 1.0))
        self.buttons.append(self.pause_button)
        
        self.reset_button = Button("RESET", -0.9, self.physics_y - 7*(button_height + button_spacing), button_width, button_height,
                                color=(0.6, 0.2, 0.2, 1.0), hover_color=(0.8, 0.3, 0.3, 1.0))
        self.buttons.append(self.reset_button)

        # Controles de parámetros físicos distribuidos en columnas
        param_y = self.physics_y - 8.5*(button_height + button_spacing)
        param_button_width = button_width * 0.8  # Mismo ancho que los botones superiores

        # Gravedad en columna 1
        self.gravity_up_button = Button("GRAV+", col1_x, param_y, param_button_width, button_height,
                                      color=(0.3, 0.4, 0.6, 1.0), hover_color=(0.4, 0.5, 0.8, 1.0))
        self.buttons.append(self.gravity_up_button)
        
        self.gravity_down_button = Button("GRAV-", col2_x, param_y, param_button_width, button_height,
                                        color=(0.3, 0.4, 0.6, 1.0), hover_color=(0.4, 0.5, 0.8, 1.0))
        self.buttons.append(self.gravity_down_button)

        # Rebote en columna 3
        self.bounce_up_button = Button("BOUNCE+", col3_x, param_y, param_button_width, button_height,
                                     color=(0.4, 0.6, 0.3, 1.0), hover_color=(0.5, 0.8, 0.4, 1.0))
        self.buttons.append(self.bounce_up_button)
        
        self.bounce_down_button = Button("BOUNCE-", col4_x, param_y, param_button_width, button_height,
                                       color=(0.4, 0.6, 0.3, 1.0), hover_color=(0.5, 0.8, 0.4, 1.0))
        self.buttons.append(self.bounce_down_button)



        # Botones de escenas en columnas 1-3
        advanced_y = self.physics_y - 12*(button_height + button_spacing)
        scene_button_width = button_width * 0.8  # Mismo ancho que los botones superiores

        # Botones de rendimiento en columnas 1-2 de la siguiente fila
        perf_y = advanced_y - button_height - button_spacing
        self.optimize_button = Button("OPTIM", col1_x, perf_y, scene_button_width, button_height * 0.9,
                                    color=(0.5, 0.5, 0.3, 1.0), hover_color=(0.7, 0.7, 0.4, 1.0))
        self.buttons.append(self.optimize_button)

        self.benchmark_button = Button("BENCH", col2_x, perf_y, scene_button_width, button_height * 0.9,
                                     color=(0.3, 0.5, 0.5, 1.0), hover_color=(0.4, 0.7, 0.7, 1.0))
        self.buttons.append(self.benchmark_button)

        # Botones de domino y rebote a la misma altura que bench
        self.domino_scene_button = Button("DOMINO", col3_x, perf_y, scene_button_width, button_height * 0.9,
                                        color=(0.6, 0.4, 0.4, 1.0), hover_color=(0.8, 0.5, 0.5, 1.0))
        self.buttons.append(self.domino_scene_button)

        self.bounce_scene_button = Button("REBOTE", col4_x, perf_y, scene_button_width, button_height * 0.9,
                                       color=(0.5, 0.3, 0.6, 1.0), hover_color=(0.7, 0.4, 0.8, 1.0))
        self.buttons.append(self.bounce_scene_button)

        # Botones ambientales en columnas 4-5
        env_y = advanced_y

        # Botón avanzado y exportar en columnas 3-4 de la misma fila




        # Calcular el scroll máximo necesario
        # El botón más bajo está en perf_y, necesitamos que sea visible
        # El panel va de -1.0 a 1.0 en Y, entonces si perf_y < -0.9, necesitamos scroll
        lowest_button_y = perf_y
        if lowest_button_y < -0.9:
            # Aumentar el scroll máximo para asegurar que todos los botones sean accesibles
            self.max_scroll = abs(lowest_button_y + 0.9) * 1.5
        else:
            self.max_scroll = 0.0
        
        # Asegurar un mínimo de scroll si hay muchos botones
        if len(self.buttons) > 10:
            self.max_scroll = max(self.max_scroll, 2.0)

        # Actualizar colores según herramienta seleccionada
        self._update_button_colors()

        print(f"Total de botones creados: {len(self.buttons)}")
        print(f"Scroll máximo necesario: {self.max_scroll:.2f}")

    def _update_button_colors(self):
        """Actualizar colores de botones según herramienta seleccionada"""
        # Resaltar herramienta seleccionada
        if self.selected_tool == "camera":
            self.camera_button.color = (0.25, 0.4, 0.6, 1.0)
            self.camera_button.hover_color = (0.35, 0.55, 0.8, 1.0)
        elif self.selected_tool == "select":
            self.select_button.color = (0.3, 0.55, 0.3, 1.0)
            self.select_button.hover_color = (0.4, 0.7, 0.4, 1.0)
        elif self.selected_tool == "rotate":
            self.rotate_button.color = (0.4, 0.4, 0.7, 1.0)
            self.rotate_button.hover_color = (0.55, 0.55, 0.85, 1.0)
        elif self.selected_tool == "scale":
            self.scale_button.color = (0.7, 0.4, 0.4, 1.0)
            self.scale_button.hover_color = (0.85, 0.55, 0.55, 1.0)
        elif self.selected_tool == "add_cube":
            self.add_cube_button.color = (0.6, 0.4, 0.25, 1.0)
            self.add_cube_button.hover_color = (0.8, 0.55, 0.35, 1.0)

    def set_selected_tool(self, tool):
        """Establecer la herramienta de edición actualmente seleccionada"""
        self.selected_tool = tool
        self._update_button_colors()

    def set_panel_width_ratio(self, ratio):
        """Cambiar dinámicamente el ancho del panel lateral"""
        old_ratio = self.panel_width_ratio
        self.panel_width_ratio = max(0.2, min(0.5, ratio))

        if old_ratio != self.panel_width_ratio:
            self._create_all_buttons()

        if hasattr(self, 'window') and self.window:
            self.window.on_resize(self.window.width, self.window.height)

    def update_object_info(self):
        """Actualizar la información de objetos seleccionados"""
        if self.window and hasattr(self.window, 'selected_objects') and self.window.selected_objects:
            num_selected = len(self.window.selected_objects)
            if num_selected == 1:
                obj_name = getattr(self.window.selected_objects[0], 'name', 'unnamed')
                self.current_object_info = f"1: {obj_name}"
            else:
                self.current_object_info = f"{num_selected} objs"
        else:
            self.current_object_info = "None"

    def handle_click(self, x, y):
        """Manejar click en coordenadas del panel"""
        # Ya no necesitamos ajustar Y por scroll
        adjusted_y = y
        
        for button in self.buttons:
            if button.contains_point(x, adjusted_y):
                if button == self.camera_button:
                    return "camera"
                elif button == self.select_button:
                    return "select"
                elif button == self.rotate_button:
                    return "rotate"
                elif button == self.scale_button:
                    return "scale"
                elif button == self.add_cube_button:
                    return "add_cube"
                elif button == self.delete_button:
                    return "delete"
                elif button == self.select_texture_button:
                    self._select_texture_file()
                    return None
                elif button == self.none_texture_button:
                    self._set_texture_none()
                    return None
                elif button == self.toggle_gravity_button:
                    if self.window and hasattr(self.window, 'scene') and hasattr(self.window.scene, 'toggle_gravity'):
                        self.window.scene.toggle_gravity()
                    return None
                elif button == self.toggle_collision_button:
                    if self.window and hasattr(self.window, 'scene') and hasattr(self.window.scene, 'toggle_collisions'):
                        self.window.scene.toggle_collisions()
                    return None
                elif button == self.mode_button:
                    if self.window and hasattr(self.window, 'scene') and hasattr(self.window.scene, 'set_mode'):
                        current_mode = self.window.scene.get_mode() if hasattr(self.window.scene, 'get_mode') else "editor"
                        new_mode = "scene" if current_mode == "editor" else "editor"
                        self.window.scene.set_mode(new_mode)
                    return None
                elif button == self.save_button:
                    if self.window and hasattr(self.window, 'scene') and hasattr(self.window.scene, 'save_scene'):
                        self.window.scene.save_scene()
                    return None
                elif button == self.load_button:
                    if self.window and hasattr(self.window, 'scene') and hasattr(self.window.scene, 'load_scene'):
                        scenes = self.window.scene.list_scenes() if hasattr(self.window.scene, 'list_scenes') else []
                        if scenes:
                            self.window.scene.load_scene(f"scenes/{scenes[0]}")
                    return None
                elif button == self.play_button:
                    if self.window and hasattr(self.window, 'scene') and hasattr(self.window.scene, 'play_physics'):
                        self.window.scene.play_physics()
                    return None
                elif button == self.pause_button:
                    if self.window and hasattr(self.window, 'scene') and hasattr(self.window.scene, 'pause_physics'):
                        self.window.scene.pause_physics()
                    return None
                elif button == self.reset_button:
                    if self.window and hasattr(self.window, 'scene') and hasattr(self.window.scene, 'reset_physics'):
                        self.window.scene.reset_physics()
                    return None
                elif button == self.gravity_up_button:
                    if self.window and hasattr(self.window, 'scene') and hasattr(self.window.scene, 'set_gravity_strength'):
                        current_gravity = self.window.scene.get_gravity_strength() if hasattr(self.window.scene, 'get_gravity_strength') else -9.8
                        self.window.scene.set_gravity_strength(current_gravity - 1.0)
                    return None
                elif button == self.gravity_down_button:
                    if self.window and hasattr(self.window, 'scene') and hasattr(self.window.scene, 'set_gravity_strength'):
                        current_gravity = self.window.scene.get_gravity_strength() if hasattr(self.window.scene, 'get_gravity_strength') else -9.8
                        self.window.scene.set_gravity_strength(current_gravity + 1.0)
                    return None
                elif button == self.bounce_up_button:
                    if self.window and hasattr(self.window, 'scene') and hasattr(self.window.scene, 'set_global_bounciness'):
                        # Aumentar rebote progresivamente de 0.1 a 0.9
                        current_bounce = 0.1  # Valor inicial
                        # Buscar el rebote actual de los cubos de rebote
                        for physics_obj in self.window.scene.physics_world.physics_objects:
                            if "Cube" in physics_obj.obj.name and ("LeftCube" in physics_obj.obj.name or "RightCube" in physics_obj.obj.name):
                                current_bounce = physics_obj.physics.bounciness
                                break
                        # Aumentar en incrementos de 0.1 hasta 0.9
                        new_bounce = min(0.9, current_bounce + 0.1)
                        self.window.scene.set_global_bounciness(new_bounce)
                    return None
                elif button == self.bounce_down_button:
                    if self.window and hasattr(self.window, 'scene') and hasattr(self.window.scene, 'set_global_bounciness'):
                        self.window.scene.set_global_bounciness(0.1)
                    return None



                elif button == self.domino_scene_button:
                    if self.window and hasattr(self.window, 'scene') and hasattr(self.window.scene, 'create_realistic_scene'):
                        self.window.scene.create_realistic_scene("domino")
                    return None


                elif button == self.optimize_button:
                    if self.window and hasattr(self.window, 'scene') and hasattr(self.window.scene, 'optimize_physics'):
                        self.window.scene.optimize_physics()
                    return None
                elif button == self.benchmark_button:
                    if self.window and hasattr(self.window, 'scene') and hasattr(self.window.scene, 'run_physics_benchmark'):
                        benchmark_result = self.window.scene.run_physics_benchmark(5.0)
                        if benchmark_result:
                            print(f"Benchmark: {benchmark_result.get('fps', 0):.1f} FPS")
                    return None
                elif button == self.bounce_scene_button:
                    if self.window and hasattr(self.window, 'scene') and hasattr(self.window.scene, 'create_bounce_scene'):
                        self.window.scene.create_bounce_scene()
                    return None



        # Manejar flechas del selector
        if self.left_arrow.contains_point(x, y):
            if self.window and hasattr(self.window, '_cycle_cube_selection'):
                self.window._cycle_cube_selection(-1)
                self.update_object_info()
            return None
        elif self.right_arrow.contains_point(x, y):
            if self.window and hasattr(self.window, '_cycle_cube_selection'):
                self.window._cycle_cube_selection(1)
                self.update_object_info()
            return None

        return None

    def handle_mouse_press(self, x, y, button):
        """Manejar presión del mouse"""
        panel_left_edge_ndc = -1.0 + 2.0 * (1.0 - self.panel_width_ratio)
        handle_left = panel_left_edge_ndc - self.resize_handle_width
        handle_right = panel_left_edge_ndc + self.resize_handle_width

        if button == 1 and handle_left <= x <= handle_right:
            self.is_resizing = True
            self.resize_start_x = x
            return True

        return False

    def handle_mouse_release(self, x, y, button):
        """Manejar liberación del mouse"""
        if button == 1 and self.is_resizing:
            self.is_resizing = False
            return True
        return False

    def handle_mouse_motion(self, x, y, dx, dy):
        """Manejar movimiento del mouse"""
        if self.is_resizing:
            new_ratio = (x + 1.0) / 2.0
            self.set_panel_width_ratio(new_ratio)
            return True
        return False

    def handle_scroll(self, x, y, scroll_amount):
        """Manejar scroll del mouse - deshabilitado ya que usamos layout en columnas"""
        return False

    def is_mouse_over_resize_handle(self, x, y):
        """Verificar si el mouse está sobre el handle"""
        panel_left_edge_ndc = -1.0 + 2.0 * (1.0 - self.panel_width_ratio)
        handle_left = panel_left_edge_ndc - self.resize_handle_width
        handle_right = panel_left_edge_ndc + self.resize_handle_width
        return handle_left <= x <= handle_right

    def render(self):
        """Renderizar el panel completo"""
        panel_width_pixels = int(self.total_width * self.panel_width_ratio)
        scene_width_pixels = self.total_width - panel_width_pixels

        # Viewport del panel
        self.ctx.viewport = (scene_width_pixels, 0, panel_width_pixels, self.total_height)

        self._render_panel_background()
        self._render_title()
        self._render_buttons()
        self.update_object_info()
        self._render_object_selector()
        self._render_texture_selector()
        self._render_resize_handle()

        # Restaurar viewport
        self.ctx.viewport = (0, 0, self.total_width, self.total_height)

    def _render_panel_background(self):
        """Renderizar fondo del panel"""
        vertices = np.array([
            -1.0, -1.0, 0.15, 0.15, 0.2, 1.0,
             1.0, -1.0, 0.15, 0.15, 0.2, 1.0,
             1.0,  1.0, 0.2, 0.2, 0.25, 1.0,
            -1.0,  1.0, 0.2, 0.2, 0.25, 1.0
        ], dtype='f4')

        indices = np.array([0, 1, 2, 2, 3, 0], dtype='i4')

        vertex_shader = """
        #version 330
        in vec2 in_pos;
        in vec4 in_color;
        out vec4 color;
        void main() {
            gl_Position = vec4(in_pos, 0.0, 1.0);
            color = in_color;
        }
        """

        fragment_shader = """
        #version 330
        in vec4 color;
        out vec4 out_color;
        void main() {
            out_color = color;
        }
        """

        program = self.ctx.program(vertex_shader=vertex_shader, fragment_shader=fragment_shader)
        vbo = self.ctx.buffer(vertices.tobytes())
        ibo = self.ctx.buffer(indices.tobytes())

        vao = self.ctx.vertex_array(
            program,
            [(vbo, '2f 4f', 'in_pos', 'in_color')],
            ibo
        )

        self.ctx.disable(moderngl.DEPTH_TEST)
        vao.render()
        self.ctx.enable(moderngl.DEPTH_TEST)

    def _render_title(self):
        """Renderizar título del panel"""
        self.ctx.disable(moderngl.DEPTH_TEST)
        title_scale = self._get_scaled_text_scale(1.0)
        self.text_renderer.render_text_at_position(
            "PANEL", -0.85, 0.88, color=(0.9, 0.9, 1.0), scale=title_scale
        )
        self.ctx.enable(moderngl.DEPTH_TEST)

    def _render_buttons(self):
        """Renderizar todos los botones en el panel"""
        button_program = self.ctx.program(
            vertex_shader="""
            #version 330
            in vec2 in_pos;
            in vec4 in_color;
            out vec4 color;
            void main() {
                gl_Position = vec4(in_pos, 0.0, 1.0);
                color = in_color;
            }
            """,
            fragment_shader="""
            #version 330
            in vec4 color;
            out vec4 out_color;
            void main() {
                out_color = color;
            }
            """
        )

        self.ctx.disable(moderngl.DEPTH_TEST)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

        for button in self.buttons:
            # Solo renderizar si el botón está visible en el viewport
            if button.y + button.height < -1.0 or button.y > 1.0:
                continue

            # Fondo del botón
            vertices = np.array([
                button.x, button.y, *button.color,
                button.x + button.width, button.y, *button.color,
                button.x + button.width, button.y + button.height, *button.color,
                button.x, button.y + button.height, *button.color
            ], dtype='f4')
            
            indices = np.array([0, 1, 2, 2, 3, 0], dtype='i4')

            vbo = self.ctx.buffer(vertices.tobytes())
            ibo = self.ctx.buffer(indices.tobytes())

            vao = self.ctx.vertex_array(
                button_program,
                [(vbo, '2f 4f', 'in_pos', 'in_color')],
                ibo
            )

            vao.render()

            # Borde superior brillante
            border_color = (min(button.color[0] + 0.15, 1.0), 
                          min(button.color[1] + 0.15, 1.0), 
                          min(button.color[2] + 0.15, 1.0), 1.0)
            
            border_vertices = np.array([
                button.x, button.y + button.height, *border_color,
                button.x + button.width, button.y + button.height, *border_color
            ], dtype='f4')
            
            border_vbo = self.ctx.buffer(border_vertices.tobytes())
            border_vao = self.ctx.vertex_array(
                button_program,
                [(border_vbo, '2f 4f', 'in_pos', 'in_color')]
            )
            
            self.ctx.line_width = 2.0
            border_vao.render(moderngl.LINES)

            # Texto del botón con scroll aplicado
            text_x = button.x + 0.05
            # Renderizar texto del botón
            text_y = button.y + button.height / 2 - 0.035
            button_text_scale = self._get_scaled_text_scale(0.85)

            self.text_renderer.render_text_at_position(
                button.text, text_x, text_y,
                color=(1.0, 1.0, 1.0), scale=button_text_scale
            )

        self.ctx.enable(moderngl.DEPTH_TEST)

    def _render_object_selector(self):
        """Renderizar selector de objetos"""
        button_program = self.ctx.program(
            vertex_shader="""
            #version 330
            in vec2 in_pos;
            in vec4 in_color;
            out vec4 color;
            void main() {
                gl_Position = vec4(in_pos, 0.0, 1.0);
                color = in_color;
            }
            """,
            fragment_shader="""
            #version 330
            in vec4 color;
            out vec4 out_color;
            void main() {
                out_color = color;
            }
            """
        )

        self.ctx.disable(moderngl.DEPTH_TEST)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

        # Título
        selector_title_scale = self._get_scaled_text_scale(0.8)
        self.text_renderer.render_text_at_position(
            "", -0.85, self.selector_y + 0.2,
            color=(0.8, 0.8, 0.9), scale=selector_title_scale
        )

        # Flecha izquierda
        vertices = np.array([
            self.left_arrow.x, self.left_arrow.y, *self.left_arrow.color,
            self.left_arrow.x + self.left_arrow.width, self.left_arrow.y, *self.left_arrow.color,
            self.left_arrow.x + self.left_arrow.width, self.left_arrow.y + self.left_arrow.height, *self.left_arrow.color,
            self.left_arrow.x, self.left_arrow.y + self.left_arrow.height, *self.left_arrow.color
        ], dtype='f4')
        indices = np.array([0, 1, 2, 2, 3, 0], dtype='i4')
        vbo = self.ctx.buffer(vertices.tobytes())
        ibo = self.ctx.buffer(indices.tobytes())
        vao = self.ctx.vertex_array(button_program, [(vbo, '2f 4f', 'in_pos', 'in_color')], ibo)
        vao.render()

        # Flecha derecha
        vertices = np.array([
            self.right_arrow.x, self.right_arrow.y, *self.right_arrow.color,
            self.right_arrow.x + self.right_arrow.width, self.right_arrow.y, *self.right_arrow.color,
            self.right_arrow.x + self.right_arrow.width, self.right_arrow.y + self.right_arrow.height, *self.right_arrow.color,
            self.right_arrow.x, self.right_arrow.y + self.right_arrow.height, *self.right_arrow.color
        ], dtype='f4')
        vbo = self.ctx.buffer(vertices.tobytes())
        vao = self.ctx.vertex_array(button_program, [(vbo, '2f 4f', 'in_pos', 'in_color')], ibo)
        vao.render()

        # Textos de flechas
        arrow_text_scale = self._get_scaled_text_scale(1.2)
        self.text_renderer.render_text_at_position(
            "<", self.left_arrow.x + 0.1, self.left_arrow.y + 0.02,
            color=(1.0, 1.0, 1.0), scale=arrow_text_scale
        )

        self.text_renderer.render_text_at_position(
            ">", self.right_arrow.x + 0.1, self.right_arrow.y + 0.02,
            color=(1.0, 1.0, 1.0), scale=arrow_text_scale
        )

        # Info del objeto
        object_info_scale = self._get_scaled_text_scale(0.75)
        self.text_renderer.render_text_at_position(
            self.current_object_info, -0.45, self.selector_y + 0.05,
            color=(0.4, 1.0, 0.4), scale=object_info_scale
        )

        self.ctx.enable(moderngl.DEPTH_TEST)

    def _render_texture_selector(self):
        """Renderizar selector de texturas"""
        self.ctx.disable(moderngl.DEPTH_TEST)
        
        # Título
        texture_title_scale = self._get_scaled_text_scale(0.7)
        self.text_renderer.render_text_at_position(
            "TEXTURA:", -0.85, self.texture_y + 0.2,
            color=(0.8, 0.8, 0.9), scale=texture_title_scale
        )

        # Nombre de textura actual
        current_texture_name = os.path.basename(self.current_texture_path) if self.current_texture_path else "Ninguna"
        if len(current_texture_name) > 15:
            current_texture_name = current_texture_name[:12] + "..."
        
        texture_info_scale = self._get_scaled_text_scale(0.65)
        self.text_renderer.render_text_at_position(
            current_texture_name, -0.85, self.texture_y - 0.35,
            color=(0.4, 0.8, 1.0) if self.current_texture_path else (0.8, 0.4, 0.4), 
            scale=texture_info_scale
        )

        self.ctx.enable(moderngl.DEPTH_TEST)

    def _render_resize_handle(self):
        """Renderizar handle de redimensionamiento"""
        panel_left_edge_ndc = -1.0 + 2.0 * (1.0 - self.panel_width_ratio)

        self.ctx.viewport = (0, 0, self.total_width, self.total_height)

        handle_program = self.ctx.program(
            vertex_shader="""#version 330
            in vec2 in_pos;
            in vec4 in_color;
            out vec4 color;
            void main() {
                gl_Position = vec4(in_pos, 0.0, 1.0);
                color = in_color;
            }""",
            fragment_shader="""#version 330
            in vec4 color;
            out vec4 out_color;
            void main() {
                out_color = color;
            }"""
        )

        self.ctx.disable(moderngl.DEPTH_TEST)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

        # Línea vertical
        handle_width = 0.005
        handle_color = (0.7, 0.8, 1.0, 0.7)

        vertices = np.array([
            panel_left_edge_ndc - handle_width/2, -1.0, *handle_color,
            panel_left_edge_ndc + handle_width/2, -1.0, *handle_color,
            panel_left_edge_ndc + handle_width/2,  1.0, *handle_color,
            panel_left_edge_ndc - handle_width/2,  1.0, *handle_color
        ], dtype='f4')

        indices = np.array([0, 1, 2, 2, 3, 0], dtype='i4')

        vbo = self.ctx.buffer(vertices.tobytes())
        ibo = self.ctx.buffer(indices.tobytes())
        vao = self.ctx.vertex_array(handle_program, [(vbo, '2f 4f', 'in_pos', 'in_color')], ibo)
        vao.render()

        self.ctx.enable(moderngl.DEPTH_TEST)

    def on_resize(self, width, height):
        """Actualizar dimensiones al redimensionar ventana"""
        self.total_width = width
        self.total_height = height
        self.base_scale = self._calculate_base_scale()
        self._create_all_buttons()

    def _select_texture_file(self):
        """Abrir diálogo para seleccionar textura"""
        try:
            root = Tk()
            root.withdraw()

            file_path = filedialog.askopenfilename(
                title="Seleccionar imagen",
                filetypes=[("Imagenes", "*.png *.jpg *.jpeg *.bmp"), ("Todos", "*.*")]
            )

            root.destroy()

            if file_path and os.path.isfile(file_path):
                texture_obj = self._load_image_as_texture(file_path)
                if texture_obj:
                    self.current_texture_path = file_path
                    self.current_texture = texture_obj
                    self._gpu_texture_ready = False
                    print(f"Textura: {os.path.basename(file_path)}")

        except Exception as e:
            print(f"Error: {e}")

    def _load_image_as_texture(self, image_path):
        """Cargar imagen como textura"""
        try:
            img = Image.open(image_path).convert('RGB')
            width, height = img.size

            max_size = 512
            if width > max_size or height > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                width, height = img.size

            if width == 0 or height == 0:
                raise ValueError("Imagen inválida")

            img_array = np.array(img, dtype=np.uint8)
            image_data = ImageData(width, height, 3)
            image_data.data = img_array

            texture_name = f"tex_{os.path.basename(image_path)}"
            texture_obj = Texture(texture_name, width, height, 3, image_data)

            return texture_obj

        except Exception as e:
            print(f"Error: {e}")
            return None

    def _set_texture_none(self):
        """Remover textura seleccionada"""
        if self.current_texture_path is not None:
            self._gpu_texture_ready = False
        self.current_texture_path = None
        self.current_texture = None
        print("Textura removida")

    def get_current_texture(self):
        """Retornar textura actual"""
        return self.current_texture



    def get_scene_viewport(self):
        """Retornar viewport para escena 3D"""
        panel_width_pixels = int(self.total_width * self.panel_width_ratio)
        scene_width_pixels = self.total_width - panel_width_pixels
        return (0, 0, scene_width_pixels, self.total_height)


class SimpleGUI:
    def __init__(self, ctx, width, height, window=None):
        self.ctx = ctx
        self.width = width
        self.height = height
        self.window = window
        self.current_mode = "camera"
        self.side_panel = SidePanel(ctx, width, height, panel_width_ratio=0.35, window=window)
        self.scene_viewport = self.side_panel.get_scene_viewport()

    def render(self):
        self.side_panel.render()

    def get_scene_viewport(self):
        return self.scene_viewport

    def on_resize(self, width, height):
        self.width = width
        self.height = height
        self.side_panel.on_resize(width, height)
        self.scene_viewport = self.side_panel.get_scene_viewport()

    def set_panel_width_ratio(self, ratio):
        self.side_panel.set_panel_width_ratio(ratio)
        self.scene_viewport = self.side_panel.get_scene_viewport()

    def handle_mouse_press(self, x, y, button):
        return self.side_panel.handle_mouse_press(x, y, button)

    def handle_mouse_release(self, x, y, button):
        return self.side_panel.handle_mouse_release(x, y, button)

    def handle_mouse_motion(self, x, y, dx, dy):
        return self.side_panel.handle_mouse_motion(x, y, dx, dy)

    def handle_scroll(self, x, y, scroll_amount):
        """Manejar scroll del mouse"""
        return self.side_panel.handle_scroll(x, y, scroll_amount)

    def is_mouse_over_resize_handle(self, x, y):
        return self.side_panel.is_mouse_over_resize_handle(x, y)

    def is_mouse_over_resize_handle(self, x, y):
        return self.side_panel.is_mouse_over_resize_handle(x, y)
