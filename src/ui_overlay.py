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
        
        # Crear imagen con PIL
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        # Calcular tamaño del texto
        dummy_img = Image.new('L', (1, 1))
        draw = ImageDraw.Draw(dummy_img)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Crear imagen con el texto
        img = Image.new('L', (text_width + 10, text_height + 10), color=0)
        draw = ImageDraw.Draw(img)
        draw.text((5, 5), text, fill=255, font=font)
        
        # Crear textura OpenGL
        texture = self.ctx.texture(img.size, 1, img.tobytes())
        texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
        
        self.texture_cache[cache_key] = (texture, text_width, text_height)
        return texture, text_width, text_height

    def render_text_at_position(self, text, x, y, color=(1, 1, 1), scale=1.0):
        """Renderiza texto en coordenadas NDC"""
        if not text:
            return
            
        font_size = int(64 * scale)
        texture, text_width, text_height = self.create_text_texture(text, font_size)
        
        # Convertir tamaño de píxeles a NDC con mejor proporción
        width_ndc = (text_width / 400.0) * scale
        height_ndc = (text_height / 400.0) * scale
        
        # Crear quad para el texto (invertir coordenadas Y de textura)
        vertices = np.array([
            x, y, 0.0, 1.0,  # bottom-left, tex top-left
            x + width_ndc, y, 1.0, 1.0,  # bottom-right, tex top-right
            x + width_ndc, y + height_ndc, 1.0, 0.0,  # top-right, tex bottom-right
            x, y + height_ndc, 0.0, 0.0  # top-left, tex bottom-left
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
    def __init__(self, ctx, total_width, total_height, panel_width_ratio=0.25, window=None):
        self.ctx = ctx
        self.total_width = total_width
        self.total_height = total_height
        self.panel_width_ratio = panel_width_ratio  # Porcentaje del ancho para panel lateral (25%)
        self.window = window  # Nuevo: referencia a ventana para controlar escena
        self.text_renderer = TextRenderer(ctx)  # Handler para renderizar textos

        # Configurar botones interactivos con espaciado uniforme
        button_width = 1.6
        button_height = 0.2
        button_spacing = 0.05

        self.buttons = []
        self.selected_tool = "select"  # Herramienta seleccionada por defecto

        # Crear botones
        button_y = 0.7
        self.camera_button = Button("CAMARA", -0.9, button_y, button_width, button_height,
                                  color=(0.25, 0.35, 0.5, 1.0), hover_color=(0.35, 0.5, 0.7, 1.0))
        button_y -= button_height + button_spacing

        self.select_button = Button("SELECT", -0.9, button_y, button_width, button_height,
                                  color=(0.3, 0.5, 0.3, 1.0), hover_color=(0.4, 0.65, 0.4, 1.0))
        button_y -= button_height + button_spacing

        self.add_cube_button = Button("AÑADIR CUBO", -0.9, button_y, button_width, button_height,
                                    color=(0.5, 0.35, 0.25, 1.0), hover_color=(0.7, 0.5, 0.35, 1.0))
        button_y -= button_height + button_spacing

        self.delete_button = Button("ELIMINAR", -0.9, button_y, button_width, button_height,
                                  color=(0.6, 0.25, 0.25, 1.0), hover_color=(0.8, 0.35, 0.35, 1.0))

        self.buttons = [self.camera_button, self.select_button, self.add_cube_button, self.delete_button]

        # Widget para seleccionar objetos (movido más arriba)
        self.selector_y = -0.25
        selector_height = 0.15
        self.left_arrow = Button("<", -0.8, self.selector_y, 0.3, selector_height, color=(0.4, 0.4, 0.4, 1.0))
        self.right_arrow = Button(">", 0.5, self.selector_y, 0.3, selector_height, color=(0.4, 0.4, 0.4, 1.0))
        self.current_object_name = "None"

        # Selección de texturas para nuevos objetos
        self.texture_y = self.selector_y - 0.35  # Más separación debajo del selector
        self.select_texture_button = Button("SELECCIONAR TEXTURA", -0.9, self.texture_y, button_width, button_height,
                                          color=(0.3, 0.4, 0.5, 1.0), hover_color=(0.4, 0.55, 0.65, 1.0))
        self.none_texture_button = Button("NINGUNA", -0.9, self.texture_y - button_height - button_spacing, button_width, button_height,
                                        color=(0.4, 0.3, 0.3, 1.0), hover_color=(0.6, 0.4, 0.4, 1.0))

        # Estado de textura seleccionada (con caché para performance)
        self.current_texture_path = None  # Ruta del archivo de textura actual
        self.current_texture = None  # Objeto Texture cargado
        self._processed_texture = None  # Textura ya procesada y lista para GPU (caché)
        self._gpu_texture_ready = False  # Flag que indica si textura GPU está actualizada

        self.buttons.extend([self.select_texture_button, self.none_texture_button])

        self._update_button_colors()

    def _update_button_colors(self):
        """Actualizar colores de botones según herramienta seleccionada"""
        # Resetear todos los botones a color gris base
        for button in self.buttons:
            button.color = (0.3, 0.3, 0.3, 1.0)
            button.hover_color = (0.45, 0.45, 0.45, 1.0)

        # Resaltar herramienta seleccionada con colores vibrantes
        if self.selected_tool == "camera":
            self.camera_button.color = (0.25, 0.4, 0.6, 1.0)
            self.camera_button.hover_color = (0.35, 0.55, 0.8, 1.0)
        elif self.selected_tool == "select":
            self.select_button.color = (0.3, 0.55, 0.3, 1.0)
            self.select_button.hover_color = (0.4, 0.7, 0.4, 1.0)
        elif self.selected_tool == "add_cube":
            self.add_cube_button.color = (0.6, 0.4, 0.25, 1.0)
            self.add_cube_button.hover_color = (0.8, 0.55, 0.35, 1.0)

    def set_selected_tool(self, tool):
        """Establecer la herramienta de edición actualmente seleccionada"""
        self.selected_tool = tool
        self._update_button_colors()

    def update_object_name(self):
        """Actualizar el nombre del objeto actualmente mostrado"""
        if self.window and self.window.selected_object:
            self.current_object_name = getattr(self.window.selected_object, 'name', 'unnamed')
        else:
            self.current_object_name = "None"

    def handle_click(self, x, y):
        """Manejar click en coordenadas del panel, retorna la herramienta seleccionada"""
        for button in self.buttons:
            if button.contains_point(x, y):
                if button == self.camera_button:
                    return "camera"
                elif button == self.select_button:
                    return "select"
                elif button == self.add_cube_button:
                    return "add_cube"
                elif button == self.delete_button:
                    return "delete"

        # Manejar flechas del selector de objetos
        if self.left_arrow.contains_point(x, y):
            if self.window:
                self.window._cycle_cube_selection(-1)  # Seleccionar objeto anterior
                self.update_object_name()
                return None
        elif self.right_arrow.contains_point(x, y):
            if self.window:
                self.window._cycle_cube_selection(1)  # Seleccionar objeto siguiente
                self.update_object_name()
                return None

        # Manejar selección de texturas
        if self.select_texture_button.contains_point(x, y):
            # Abrir diálogo para seleccionar archivo
            self._select_texture_file()
            return None
        elif self.none_texture_button.contains_point(x, y):
            # Remover textura seleccionada (usar ninguna)
            self._set_texture_none()
            return None

        return None

    def render(self):
        # Calcular las dimensiones del panel lateral
        panel_width_pixels = int(self.total_width * self.panel_width_ratio)
        scene_width_pixels = self.total_width - panel_width_pixels

        # Configurar viewport para el panel lateral (parte derecha)
        self.ctx.viewport = (scene_width_pixels, 0, panel_width_pixels, self.total_height)

        # Renderizar fondo del panel
        self._render_panel_background()

        # Renderizar título
        self._render_title()

        # Renderizar botones
        self._render_buttons()

        # Actualizar y renderizar selector de objetos
        self.update_object_name()
        self._render_object_selector()

        # Renderizar selector de texturas
        self._render_texture_selector()

        # Restaurar viewport completo para la escena 3D
        self.ctx.viewport = (0, 0, self.total_width, self.total_height)

    def _render_panel_background(self):
        """Renderizar fondo del panel lateral con gradiente"""
        vertices = np.array([
            -1.0, -1.0, 0.15, 0.15, 0.2, 1.0,  # Bottom darker
             1.0, -1.0, 0.15, 0.15, 0.2, 1.0,
             1.0,  1.0, 0.2, 0.2, 0.25, 1.0,   # Top lighter
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
        self.text_renderer.render_text_at_position(
            "", -0.85, 0.88, color=(0.9, 0.9, 1.0), scale=1.0
        )
        self.ctx.enable(moderngl.DEPTH_TEST)

    def _render_buttons(self):
        """Renderizar botones clicables con efecto de bordes redondeados"""
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
            # Render button background con borde
            # Fondo principal
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

            # Render border (línea más clara en la parte superior)
            border_color = (min(button.color[0] + 0.1, 1.0), 
                          min(button.color[1] + 0.1, 1.0), 
                          min(button.color[2] + 0.1, 1.0), 1.0)
            
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

            # Render button text centrado
            text_x = button.x + 0.05
            text_y = button.y + button.height / 2 - 0.04
            
            self.text_renderer.render_text_at_position(
                button.text, text_x, text_y,
                color=(1.0, 1.0, 1.0), scale=0.9
            )

        self.ctx.enable(moderngl.DEPTH_TEST)

    def _render_object_selector(self):
        """Renderizar el widget selector de objetos"""
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

        # Título del selector
        self.text_renderer.render_text_at_position(
            "", -0.85, self.selector_y + 0.25,
            color=(0.8, 0.8, 0.9), scale=0.8
        )

        # Render left arrow button
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

        # Render right arrow button
        vertices = np.array([
            self.right_arrow.x, self.right_arrow.y, *self.right_arrow.color,
            self.right_arrow.x + self.right_arrow.width, self.right_arrow.y, *self.right_arrow.color,
            self.right_arrow.x + self.right_arrow.width, self.right_arrow.y + self.right_arrow.height, *self.right_arrow.color,
            self.right_arrow.x, self.right_arrow.y + self.right_arrow.height, *self.right_arrow.color
        ], dtype='f4')
        vbo = self.ctx.buffer(vertices.tobytes())
        vao = self.ctx.vertex_array(button_program, [(vbo, '2f 4f', 'in_pos', 'in_color')], ibo)
        vao.render()

        # Render arrow texts
        self.text_renderer.render_text_at_position(
            "<", self.left_arrow.x + 0.08, self.left_arrow.y + 0.03,
            color=(1.0, 1.0, 1.0), scale=1.0
        )

        self.text_renderer.render_text_at_position(
            ">", self.right_arrow.x + 0.08, self.right_arrow.y + 0.03,
            color=(1.0, 1.0, 1.0), scale=1.0
        )

        # Render object name centrado
        self.text_renderer.render_text_at_position(
            self.current_object_name, -0.5, self.selector_y + 0.04,
            color=(0.4, 1.0, 0.4), scale=0.9
        )

        self.ctx.enable(moderngl.DEPTH_TEST)

    def _render_texture_selector(self):
        """Renderizar el widget selector de texturas"""
        button_program = self.ctx.program(
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

        # Título de la sección de texturas
        self.text_renderer.render_text_at_position(
            "TEXTURA PARA NUEVOS OBJETOS:", -0.85, self.texture_y + 0.25,
            color=(0.8, 0.8, 0.9), scale=0.7
        )

        # Render button "SELECCIONAR TEXTURA"
        vertices = np.array([
            self.select_texture_button.x, self.select_texture_button.y, *self.select_texture_button.color,
            self.select_texture_button.x + self.select_texture_button.width, self.select_texture_button.y, *self.select_texture_button.color,
            self.select_texture_button.x + self.select_texture_button.width, self.select_texture_button.y + self.select_texture_button.height, *self.select_texture_button.color,
            self.select_texture_button.x, self.select_texture_button.y + self.select_texture_button.height, *self.select_texture_button.color
        ], dtype='f4')
        indices = np.array([0, 1, 2, 2, 3, 0], dtype='i4')
        vbo = self.ctx.buffer(vertices.tobytes())
        ibo = self.ctx.buffer(indices.tobytes())
        vao = self.ctx.vertex_array(button_program, [(vbo, '2f 4f', 'in_pos', 'in_color')], ibo)
        vao.render()

        # Render button "NINGUNA"
        vertices = np.array([
            self.none_texture_button.x, self.none_texture_button.y, *self.none_texture_button.color,
            self.none_texture_button.x + self.none_texture_button.width, self.none_texture_button.y, *self.none_texture_button.color,
            self.none_texture_button.x + self.none_texture_button.width, self.none_texture_button.y + self.none_texture_button.height, *self.none_texture_button.color,
            self.none_texture_button.x, self.none_texture_button.y + self.none_texture_button.height, *self.none_texture_button.color
        ], dtype='f4')
        vbo = self.ctx.buffer(vertices.tobytes())
        vao = self.ctx.vertex_array(button_program, [(vbo, '2f 4f', 'in_pos', 'in_color')], ibo)
        vao.render()

        # Mostrar textura actual seleccionada
        current_texture_name = os.path.basename(self.current_texture_path) if self.current_texture_path else "Ninguna"
        self.text_renderer.render_text_at_position(
            f"Textura: {current_texture_name}", -0.5, self.texture_y - 0.05,
            color=(0.4, 0.8, 1.0) if self.current_texture_path else (0.8, 0.4, 0.4), scale=0.75
        )

        self.ctx.enable(moderngl.DEPTH_TEST)

    def on_resize(self, width, height):
        self.total_width = width
        self.total_height = height

    def _select_texture_file(self):
        """Abrir diálogo para seleccionar archivo de imagen y cargar como textura"""
        try:
            # Crear ventana Tkinter oculta para el diálogo
            root = Tk()
            root.withdraw()  # Ocultar la ventana principal de Tkinter

            # Abrir diálogo de selección de archivo
            file_path = filedialog.askopenfilename(
                title="Seleccionar imagen para textura",
                filetypes=[("Archivos de imagen", "*.png *.jpg *.jpeg *.bmp"), ("Todos los archivos", "*.*")]
            )

            root.destroy()  # Cerrar ventana Tkinter

            if file_path and os.path.isfile(file_path):
                # Cargar imagen y crear textura
                texture_obj = self._load_image_as_texture(file_path)
                if texture_obj:
                    self.current_texture_path = file_path
                    self.current_texture = texture_obj
                    # Marcar que la textura GPU necesita actualización
                    self._gpu_texture_ready = False
                    # Mostrar nombre del archivo en consola
                    filename = os.path.basename(file_path)
                    print(f"Textura cargada: {filename}")
                else:
                    print("Error: No se pudo cargar la imagen como textura")
            else:
                print("Selección de textura cancelada")

        except ImportError:
            print("Error: tkinter no disponible para diálogo de archivo")
        except Exception as e:
            print(f"Error al seleccionar textura: {e}")

    def _load_image_as_texture(self, image_path):
        """Cargar imagen desde archivo y crear objeto Texture con optimizaciones de performance"""
        try:
            # Cargar imagen con PIL
            img = Image.open(image_path).convert('RGB')

            # Obtener dimensiones y aplicar downsampling para performance
            width, height = img.size

            # Límite máximo de tamaño (512x512) para no consumir mucha memoria
            max_texture_size = 512
            if width > max_texture_size or height > max_texture_size:
                # Redimensionar manteniendo aspect ratio
                img.thumbnail((max_texture_size, max_texture_size), Image.Resampling.LANCZOS)
                width, height = img.size
                print(f"Textura redimensionada a {width}x{height} para optimización")

            # Validar que la imagen no esté corrupta
            if width == 0 or height == 0:
                raise ValueError("Imagen inválida o corrupta")

            # Convertir a array de numpy (uint8 - optimizado)
            img_array = np.array(img, dtype=np.uint8)

            # Crear objeto ImageData
            image_data = ImageData(width, height, 3)
            image_data.data = img_array  # Mantener como uint8 original aquí

            # Crear objeto Texture optimizado
            texture_name = f"texture_{os.path.basename(image_path)}"
            texture_obj = Texture(texture_name, width, height, 3, image_data)

            print(f"Textura optimizada: {width}x{height} píxeles")
            return texture_obj

        except Exception as e:
            print(f"Error al cargar textura {image_path}: {e}")
            return None

    def _set_texture_none(self):
        """Remover textura seleccionada, usar material por defecto"""
        # Marcar que la textura cambió (de alguna a ninguna)
        if self.current_texture_path is not None:
            self._gpu_texture_ready = False
        self.current_texture_path = None
        self.current_texture = None
        print("Textura removida - se usarán materiales por defecto")

    def get_current_texture(self):
        """Retornar la textura actualmente seleccionada para nuevos objetos"""
        return self.current_texture

    def get_scene_viewport(self):
        """Retornar rectángulo del viewport para escena 3D (parte izquierda de pantalla)"""
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
        self.side_panel = SidePanel(ctx, width, height, panel_width_ratio=0.25, window=window)
        self.scene_viewport = self.side_panel.get_scene_viewport()

    def render(self):
        self.side_panel.render()

    def get_scene_viewport(self):
        """Retornar viewport para escena 3D (parte izquierda)"""
        return self.scene_viewport

    def on_resize(self, width, height):
        self.width = width
        self.height = height
        self.side_panel.on_resize(width, height)
        self.scene_viewport = self.side_panel.get_scene_viewport()
