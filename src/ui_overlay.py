import moderngl
import numpy as np
from .model import Model
from .shader_program import ShaderProgram


class TextRenderer:
    def __init__(self, ctx):
        self.ctx = ctx

        # Simple UI shader for 2D text elements (sin UV)
        vertex_shader = """
        #version 330
        in vec2 in_pos;
        in vec3 in_color;
        out vec3 color;
        void main() {
            gl_Position = vec4(in_pos, 0.0, 1.0);
            color = in_color;
        }
        """

        fragment_shader = """
        #version 330
        in vec3 color;
        out vec4 out_color;
        void main() {
            // Simple solid color for text (no texture needed)
            out_color = vec4(color, 1.0);
        }
        """

        self.program = self.ctx.program(vertex_shader=vertex_shader, fragment_shader=fragment_shader)

    def render_text_at_position(self, text, x, y, color=(1, 1, 1), scale=1.0):
        """Render simple text at position (simplified - just colored rectangles for each letter)"""
        # This is a very basic implementation - in a real engine you'd use a proper font atlas
        char_width = 0.015 * scale
        line_height = 0.03 * scale

        for i, char in enumerate(text):
            if char == ' ':
                continue

            # Convert position to NDC (-1 to 1)
            ndc_x = (x + i * char_width - 0.5) * 2 - 1
            ndc_y = (y * 2) - 1

            # Create a small rectangle for each character (sin UV - solo position + color)
            vertices = np.array([
                ndc_x, ndc_y,                               color[0], color[1], color[2],  # bottom left
                ndc_x + char_width, ndc_y,                 color[0], color[1], color[2],  # bottom right
                ndc_x + char_width, ndc_y + char_width,    color[0], color[1], color[2],  # top right
                ndc_x, ndc_y + char_width,                  color[0], color[1], color[2]   # top left
            ], dtype='f4')

            indices = np.array([0, 1, 2, 2, 3, 0], dtype='i4')

            vbo = self.ctx.buffer(vertices.tobytes())
            ibo = self.ctx.buffer(indices.tobytes())

            vao = self.ctx.vertex_array(
                self.program,
                [(vbo, '2f 3f', 'in_pos', 'in_color')],
                ibo
            )

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
        """Check if point (px, py) is inside button bounds"""
        return (self.x <= px <= self.x + self.width and
                self.y <= py <= self.y + self.height)

    def set_callback(self, callback):
        self.callback = callback


class SidePanel:
    def __init__(self, ctx, total_width, total_height, panel_width_ratio=0.25):
        self.ctx = ctx
        self.total_width = total_width
        self.total_height = total_height
        self.panel_width_ratio = panel_width_ratio
        self.text_renderer = TextRenderer(ctx)

        # Button positions in NDC coordinates (-1 to 1)
        button_width = 1.6  # Almost full panel width
        button_height = 0.15
        button_spacing = 0.02

        self.buttons = []
        self.selected_tool = "select"  # "camera", "select", "add_cube"

        # Create buttons
        button_y = 0.8
        self.camera_button = Button("CAMERA MODE", -0.9, button_y, button_width, button_height,
                                  color=(0.3, 0.5, 0.7, 1.0), hover_color=(0.5, 0.7, 0.9, 1.0))
        button_y -= button_height + button_spacing

        self.select_button = Button("SELECT OBJECTS", -0.9, button_y, button_width, button_height,
                                  color=(0.4, 0.6, 0.4, 1.0), hover_color=(0.6, 0.8, 0.6, 1.0))
        button_y -= button_height + button_spacing

        self.add_cube_button = Button("ADD CUBE", -0.9, button_y, button_width, button_height,
                                    color=(0.6, 0.4, 0.4, 1.0), hover_color=(0.8, 0.6, 0.6, 1.0))
        button_y -= button_height + button_spacing

        self.delete_button = Button("DELETE OBJECT", -0.9, button_y, button_width, button_height,
                                  color=(0.7, 0.3, 0.3, 1.0), hover_color=(0.9, 0.5, 0.5, 1.0))

        self.buttons = [self.camera_button, self.select_button, self.add_cube_button, self.delete_button]

        # Set initial selection
        self._update_button_colors()

    def _update_button_colors(self):
        """Update button colors based on selected tool"""
        for button in self.buttons:
            button.color = (0.4, 0.4, 0.4, 1.0)  # Default gray
            button.hover_color = (0.6, 0.6, 0.6, 1.0)

        # Highlight selected tool
        if self.selected_tool == "camera":
            self.camera_button.color = (0.3, 0.5, 0.7, 1.0)
            self.camera_button.hover_color = (0.5, 0.7, 0.9, 1.0)
        elif self.selected_tool == "select":
            self.select_button.color = (0.4, 0.6, 0.4, 1.0)
            self.select_button.hover_color = (0.6, 0.8, 0.6, 1.0)
        elif self.selected_tool == "add_cube":
            self.add_cube_button.color = (0.6, 0.4, 0.4, 1.0)
            self.add_cube_button.hover_color = (0.8, 0.6, 0.6, 1.0)

    def set_selected_tool(self, tool):
        """Set the currently selected editing tool"""
        self.selected_tool = tool
        self._update_button_colors()

    def handle_click(self, x, y):
        """Handle click in panel coordinates, return the tool that was clicked"""
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
        return None

    def render(self):
        # Calcular las dimensiones del panel lateral
        panel_width_pixels = int(self.total_width * self.panel_width_ratio)
        scene_width_pixels = self.total_width - panel_width_pixels

        # Configurar viewport para el panel lateral (parte derecha)
        self.ctx.viewport = (scene_width_pixels, 0, panel_width_pixels, self.total_height)

        # Renderizar fondo del panel
        self._render_panel_background()

        # Renderizar botones
        self._render_buttons()

        # Restaurar viewport completo para la escena 3D
        self.ctx.viewport = (0, 0, self.total_width, self.total_height)

    def _render_panel_background(self):
        """Render background for the side panel"""
        # Panel ocupa toda el área del viewport actual
        vertices = np.array([
            -1.0, -1.0, 0.2, 0.2, 0.3, 0.9,  # Dark gray background
             1.0, -1.0, 0.2, 0.2, 0.3, 0.9,
             1.0,  1.0, 0.2, 0.2, 0.3, 0.9,
            -1.0,  1.0, 0.2, 0.2, 0.3, 0.9
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

    def _render_buttons(self):
        """Render clickable buttons"""
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
            # Render button background
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

            # Render button text (coordinates relative to panel viewport 0-1)
            # Convert button NDC coordinates to 0-1 panel coordinates
            panel_x = (button.x + 1.0) / 2.0  # Convert from NDC (-1,1) to (0,1)
            panel_y = (button.y + 1.0) / 2.0 + button.height/2  # Center vertically
            self.text_renderer.render_text_at_position(
                button.text, panel_x + 0.02, panel_y,
                color=(1, 1, 1), scale=0.4
            )

        self.ctx.enable(moderngl.DEPTH_TEST)

    def on_resize(self, width, height):
        self.total_width = width
        self.total_height = height

    def get_scene_viewport(self):
        """Return the viewport rect for the 3D scene (left part of screen)"""
        panel_width_pixels = int(self.total_width * self.panel_width_ratio)
        scene_width_pixels = self.total_width - panel_width_pixels
        return (0, 0, scene_width_pixels, self.total_height)


class SimpleGUI:
    def __init__(self, ctx, width, height):
        self.ctx = ctx
        self.width = width
        self.height = height
        self.current_mode = "camera"  # "camera" or "object"
        self.side_panel = SidePanel(ctx, width, height, panel_width_ratio=0.25)
        self.scene_viewport = self.side_panel.get_scene_viewport()

    def render(self):
        self.side_panel.render()

    def get_scene_viewport(self):
        """Return viewport for 3D scene (left part)"""
        return self.scene_viewport

    def on_resize(self, width, height):
        self.width = width
        self.height = height
        self.side_panel.on_resize(width, height)
        self.scene_viewport = self.side_panel.get_scene_viewport()
