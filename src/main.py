from .window import Window
from .texture import Texture
from .material import Material
from .shader_program import ShaderProgram
from .camera import Camera
from .cube import Cube
from .quad import Quad
from .scene import Scene
import numpy as np
import os
import glm

def main():
    window = Window(width=800, height=600, caption="Motor Gráfico")

    shader_program = ShaderProgram(window.ctx, 'shaders/basic.vert', 'shaders/basic.frag')
    shader_program_skybox = ShaderProgram(window.ctx, 'shaders/sprite.vert', 'shaders/sprite.frag')

    skybox_texture = Texture(image_data = np.array([120, 175, 195, 255], dtype='u1'))

    material = Material(shader_program)
    material_sprite = Material(shader_program_skybox, textures_data = [skybox_texture])

    cube1 = Cube((-2, 0, 0), (0, 45, 0), (1, 1, 1), "Cube1")
    cube2 = Cube((2, 0, 0), (0, -45, 0), (1, 0.5, 1), "Cube2")
    quad = Quad((0, 0, 0), (0, 0, 0), (6, 5, 1), "Sprite")

    camera = Camera((0, 0, 6), (0, 0, 0), (0, 1, 0), 45, window.width / window.height, 0.1, 100)
    scene = Scene(window.ctx, camera)
    scene.add_object(quad, material_sprite)
    scene.add_object(cube1, material)
    scene.add_object(cube2, material)
    
    window.scene = scene

    window.push_handlers(scene)
    
    window.run()


if __name__ == "__main__":
    main()

    



 