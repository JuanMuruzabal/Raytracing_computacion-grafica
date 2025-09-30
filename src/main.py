from .window import Window
from .texture import Texture, ImageData  # Esta línea fue cambiada: se agregó ImageData para crear texturas personalizadas.
from .material import Material
from .shader_program import ShaderProgram
from .camera import Camera
from .cube import Cube
from .quad import Quad
from .scene import Scene, RayScene       # Esta línea fue cambiada: se agregó RayScene para usar raytracing.
import numpy as np
import os
import glm

def main():
    window = Window(width=800, height=600, caption="Motor Gráfico")

    shader_program = ShaderProgram(window.ctx, 'shaders/basic.vert', 'shaders/basic.frag')
    shader_program_skybox = ShaderProgram(window.ctx, 'shaders/sprite.vert', 'shaders/sprite.frag')

    WIDTH, HEIGHT = window.width, window.height  # Esta línea fue agregada: para usar el tamaño real de la ventana.

    # Crea la textura del quad con el tamaño correcto
    skybox_texture = Texture(
        width=WIDTH,
        height=HEIGHT,
        channels_amount=4,
        image_Data=ImageData(WIDTH, HEIGHT, 4, color=(120, 175, 195, 255))
    )  # Estas líneas fueron cambiadas: ahora la textura tiene el mismo tamaño que el framebuffer del raytracer.

    material = Material(shader_program)
    material_sprite = Material(shader_program_skybox, textures_data = [skybox_texture])

    cube1 = Cube((-2, 0, 0), (0, 45, 0), (1, 1, 1), "Cube1")
    cube2 = Cube((2, 0, 0), (0, -45, 0), (1, 0.5, 1), "Cube2")
    quad = Quad((0, 0, 0), (0, 0, 0), (6, 5, 1), "Sprite", hittable=False)
    # Esta línea fue cambiada: se agregó hittable=False para que el quad no bloquee todos los rayos.

    camera = Camera((0, 0, 6), (0, 0, 0), (0, 1, 0), 45, window.width / window.height, 0.1, 100)
    scene = RayScene(window, camera, window.width, window.height)  # Usa window, no window.ctx
    scene.add_object(quad, material_sprite)
    scene.add_object(cube1, material)
    scene.add_object(cube2, material)

    
    window.set_scene(scene)
    # Esta línea fue cambiada: se usa set_scene para inicializar la escena y llamar a start().
    
    window.run()
    

if __name__ == "__main__":
    main()





