import sys
from .window import Window

import pyglet

from .texture import Texture

from .material import Material, StandardMaterial

from .shader_program import ShaderProgram

from .scene import Scene, RayScene, RaySceneGPU

from .camera import Camera

from .cube import Cube

from .quad import Quad

from .sphere_model import Sphere

def main():
    # Permitir especificar tamaño de ventana desde línea de comandos
    # Uso: python -m src.main [width] [height]
    if len(sys.argv) >= 3:
        try:
            WIDTH = int(sys.argv[1])
            HEIGHT = int(sys.argv[2])
            print(f"Usando tamaño personalizado: {WIDTH}x{HEIGHT}")
        except ValueError:
            print("Error: Los argumentos deben ser números enteros")
            WIDTH, HEIGHT = 1400, 900
    else:
        # Las instrucciones están en el menú de la ventana, no necesitamos console output
        WIDTH, HEIGHT = 1400, 900  # Ventana más grande para mejor experiencia de usuario


    SCENE_TYPE = "gpu"  # Opciones: "normal", "cpu", "gpu"


    scene_configs = {

        "normal": {

            "needs_sprite": False,

            "sprite_channels_amount": 3,

            "sprite_default_color": (255, 255, 255)

        },

        "cpu": {

            "needs_sprite": True,

            "sprite_channels_amount": 3,

            "sprite_default_color": (255, 255, 255)

        },

        "gpu": {

            "needs_sprite": True,

            "sprite_channels_amount": 4,

            "sprite_default_color": (255, 255, 255, 255)

        }

    }


    config = scene_configs[SCENE_TYPE]


    window = Window(width=WIDTH, height=HEIGHT, caption=f"3D Editor - Scene | Controls - {SCENE_TYPE.upper()}")


    shader = ShaderProgram(window.ctx, 'shaders/basic.vert', 'shaders/basic.frag')

    shader_sprite = ShaderProgram(window.ctx, 'shaders/sprite.vert', 'shaders/sprite.frag')


    albedo_red = Texture("u_texture", WIDTH, HEIGHT, 3, None, (200, 10, 190))

    albedo_blue = Texture("u_texture", WIDTH, HEIGHT, 3, None, (0, 0, 255))

    albedo_floor = Texture("u_texture", WIDTH, HEIGHT, 3, None, (80, 80, 80))

    sprite_texture = Texture(width=WIDTH, height=HEIGHT, channels_amount= config["sprite_channels_amount"], color= config["sprite_default_color"])


    material_plastic = StandardMaterial(shader, albedo_red, reflectivity=0.1)

    material_glass = StandardMaterial(shader, albedo_blue, reflectivity=0.2)

    material_floor = StandardMaterial(shader, albedo_floor, reflectivity=0.1)

    material_sprite = Material(shader_sprite, textures_data=[sprite_texture])


    cube1 = Cube((2, 0, 5), (0, 0, 0), (1, 1, 1), name="Cube1")
    cube2 = Cube((-2, 0, 5), (0, 0, 0), (1, 1, 1), name="Cube2")
    quad = Quad((0, -10, 0), (-90, 0, 0), (20, 20, 2), name="Floor", animated=False, hittable=True)
    sprite = Quad((0, 0, 0), (0, 0, 0), (10, 15, 1), name="Sprite", animated=False, hittable=False)


    camera = Camera((0, 0, 7), (0, 0, 0), (0, 1, 0), 45, WIDTH / HEIGHT, 0.01, 100.0)

    camera.set_sky_colors(top=(16, 150, 222), bottom=(181, 224, 247))


    if SCENE_TYPE == "normal":

        scene = Scene(window.ctx, camera)

        scene.add_object(cube1, material_plastic)

        scene.add_object(cube2, material_glass)


    elif SCENE_TYPE == "cpu":

        scene = RayScene(window.ctx, camera, WIDTH, HEIGHT)

        scene.add_object(sprite, material_sprite)

        scene.add_object(cube1, material_plastic)

        scene.add_object(cube2, material_glass)

        scene.add_object(quad, material_floor)


    elif SCENE_TYPE == "gpu":

        scene = RaySceneGPU(window.ctx, camera, WIDTH, HEIGHT, sprite, material_sprite)

        # Add physics-enabled cubes
        from .physics import PhysicsProperties
        physics_props = PhysicsProperties(gravity_enabled=True, collision_enabled=True)

        cube1_physics = scene.add_physics_object(cube1, physics_props)
        cube2_physics = scene.add_physics_object(cube2, physics_props)

        # Add floor as physics object (immovable)
        floor_physics_props = PhysicsProperties(
            mass=1000000.0,  # Immovable
            gravity_enabled=False,
            collision_enabled=True,
            bounciness=0.1,
            friction=0.3
        )
        floor_obj = scene.add_physics_object(quad, floor_physics_props)


    window.set_scene(scene)

    # Schedule automatic LOAD button simulation after 2 seconds
    def auto_load_scene(dt):
        # Simulate LOAD button click: get first available scene and load it
        if hasattr(window, 'scene') and hasattr(window.scene, 'list_scenes') and hasattr(window.scene, 'load_scene'):
            scenes = window.scene.list_scenes()
            if scenes:
                loaded = window.scene.load_scene(f"scenes/{scenes[0]}")
                if loaded:
                    print("Auto-loaded saved scene after 2 seconds (simulating LOAD button)")
                else:
                    print("Failed to auto-load saved scene")
            else:
                print("No saved scenes found for auto-load")

    pyglet.clock.schedule_once(auto_load_scene, 2.0)

    window.run()

if __name__ == "__main__":
    main()
