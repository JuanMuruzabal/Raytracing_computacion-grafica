import glm
import math
from .ray import Ray
from .graphics import Graphics, ComputeGraphics
from .raytracer import RayTracer, RayTracerGPU
from .physics import PhysicsWorld, PhysicsProperties, PhysicsObject
from .scene_manager import SceneManager
import numpy as np

class Scene:
    def __init__(self, ctx, camera):
        self.ctx = ctx
        self.objects = []
        self.camera = camera
        self.time = 0.0
        self.graphics = {}
        self.projection = self.camera.get_perspective_matrix()
        self.view = self.camera.get_view_matrix_rotated()


    def add_object(self, obj, material=None):
        self.objects.append(obj)
        # Create graphics for this object
        self.graphics[obj.name] = Graphics(self.ctx, obj, material)

    def remove_object(self, obj):
        if obj in self.objects:
            self.objects.remove(obj)
            if obj.name in self.graphics:
                del self.graphics[obj.name]

    def add_object_at_position(self, obj_class, position, material=None, hittable=True, **kwargs):
        """Create and add a new object at the given position"""
        # Ensure hittable is passed to the object constructor
        if 'hittable' not in kwargs:
            kwargs['hittable'] = hittable

        obj = obj_class(position=position, **kwargs)
        success = self.add_object(obj, material)
        return obj if success else False

    def get_selected_object(self):
        return getattr(self, 'selected_object', None)

    def set_selected_object(self, obj):
        self.selected_object = obj

        
    def start(self):
        print("Start!")

    def render(self):
        # Update projection and view matrices each frame to reflect camera changes
        self.projection = self.camera.get_perspective_matrix()
        self.view = self.camera.get_view_matrix_rotated()

        # Note: Animation code removed - will be handled by physics system
        self.time += 0.01

        for obj in self.objects:
            model = obj.get_model_matrix()
            mvp = self.projection * self.view * model
            self.graphics[obj.name].render({"Mvp": mvp})
        
                
    def on_mouse_click(self, u, v):
        current_ray = self.camera.raycast(u, v)
        max_bounces = 5
        bounce_count = 0

        while bounce_count < max_bounces:
            closest_hit = None
            closest_dist = float('inf')
            closest_normal = None

            for obj in self.objects:
                if hasattr(obj, 'hittable') and not obj.hittable:
                    continue  # Skip non-hittable objects like floor

                result = obj.check_hit(current_ray.origin, current_ray.direction)
                if isinstance(result, tuple) and len(result) >= 4:
                    hit, dist, point, normal = result
                else:
                    hit, dist, point = result
                    normal = None

                if hit and dist > 1e-6 and dist < closest_dist:  # Avoid self-intersection with small offset
                    closest_hit = (obj, dist, point)
                    closest_dist = dist
                    closest_normal = normal

            if closest_hit:
                obj, dist, point = closest_hit
                if closest_normal is not None:
                    print(f"Bounce {bounce_count}: Hit {obj.name} (dist: {dist:.2f}), normal: {closest_normal}")

                    # Compute reflected ray
                    reflected_direction = current_ray.reflect(closest_normal)
                    # Offset origin slightly to avoid immediate self-intersection
                    reflected_origin = point + glm.normalize(reflected_direction) * 1e-6
                    current_ray = Ray(reflected_origin, reflected_direction)
                    bounce_count += 1
                else:
                    print(f"Hit {obj.name} (dist: {dist:.2f}) but no normal available")
                    break
            else:
                if bounce_count > 0:
                    print(f"No more hits after {bounce_count} bounces")
                else:
                    print(f"No hit at ({u:.3f}, {v:.3f})")
                break

    def on_resize(self, width, height):
        if self.camera:
            self.camera.aspect_ratio = width / height

class RayScene(Scene):
    def __init__(self, ctx, camera, width, height):
        super().__init__(ctx, camera)
        self.raytracer = RayTracer(camera, width, height)

    def start(self):
        self.raytracer.render_frame(self.objects)
        if "Sprite" in self.graphics:
            self.graphics["Sprite"].update_texture("u_texture", self.raytracer.get_texture())

    def render(self):
        super().render()

    def on_resize(self, width, height):
        super().on_resize(width, height)
        self.raytracer = RayTracer(self.camera, width, height)
        self.start()
    # Este método fue cambiado: recrea el raytracer y la textura al redimensionar la ventana.

class RaySceneGPU(Scene):
    def __init__(self, ctx, camera, width, height, output_model, output_material, max_objects=100):
       self.ctx = ctx
       self.camera = camera
       self.width = width
       self.height = height
       self.max_objects = max_objects  # Nuevo: límite máximo de objetos (default 100)
       self.raytracer = None

       self.output_graphics = Graphics(ctx, output_model, output_material)
       self.raytracer = RayTracerGPU(ctx, camera, width, height, self.output_graphics)

       self._needs_buffer_update = False  # Flag para optimización: actualizar buffers solo cuando cambian objetos
       self._cached_primitives = None  # Cache para evitar reconstruir BVH innecesariamente

       # Physics system
       self.physics_world = PhysicsWorld()
       self.physics_objects = {}  # Map object name to PhysicsObject

       # Mode system
       self.current_mode = "editor"  # "editor", "scene", "paused"
       self.last_physics_update = 0.0
       self.physics_paused = False  # Separate pause state

       # Scene management system
       self.scene_manager = SceneManager()

       # Create default material for physics objects
       self._create_default_physics_material()

       super().__init__(self.ctx, self.camera)

    def _create_default_physics_material(self):
        """Create a default material for physics objects"""
        try:
            from .material import StandardMaterial
            from .texture import Texture
            from .shader_program import ShaderProgram

            # Create a basic shader program
            shader = ShaderProgram(self.ctx, 'shaders/basic.vert', 'shaders/basic.frag')

            # Create a basic albedo texture (gray)
            default_albedo = Texture("u_texture", 1, 1, 3, None, (128, 128, 128))

            # Create the material
            self._default_physics_material = StandardMaterial(shader, default_albedo, reflectivity=0.1)

        except Exception as e:
            print(f"Warning: Could not create default physics material: {e}")
            # Create a minimal fallback material
            try:
                from .material import Material
                from .shader_program import ShaderProgram
                from .texture import Texture

                shader = ShaderProgram(self.ctx, 'shaders/basic.vert', 'shaders/basic.frag')
                default_albedo = Texture("u_texture", 1, 1, 3, None, (128, 128, 128))
                self._default_physics_material = Material(shader, textures_data=[default_albedo])
            except Exception as e2:
                print(f"Error: Could not create fallback material either: {e2}")
                self._default_physics_material = None

    def add_object(self, model, material):
        if len(self.objects) >= self.max_objects:  # Validación: límite de objetos alcanzado
            return False

        self.objects.append(model)
        self.graphics[model.name] = ComputeGraphics(self.ctx, model, material)
        self._needs_buffer_update = True  # Marcar para actualizar GPU buffers
        return True

    def remove_object(self, model):
        if model in self.objects:
            self.objects.remove(model)
            if model.name in self.graphics:
                # Clean up GPU resources before removing
                graphics_obj = self.graphics[model.name]
                if hasattr(graphics_obj, 'cleanup'):
                    graphics_obj.cleanup()
                del self.graphics[model.name]
            # Forzar actualización de buffers cuando se elimina objeto
            self._needs_buffer_update = True
            return True
        return False

    def _update_matrix(self):
        self.primitives = []

        for i, (name, graphics) in enumerate(self.graphics.items()):
            graphics.create_primitive(self.primitives)
            graphics.create_transformation_matrix(self.models_f, i)
            graphics.create_inverse_transformation_matrix(self.inv_f, i)
            graphics.create_material_matrix(self.mats_f, i)

    def _matrix_to_ssbo(self):
        self.raytracer.matrix_to_ssbo(self.models_f, 0)
        self.raytracer.matrix_to_ssbo(self.inv_f, 1)
        self.raytracer.matrix_to_ssbo(self.mats_f, 2)
        self.raytracer.primitives_to_ssbo(self.primitives, 3)


    def start(self):
        print("Start!")
        self.primitives = []
        n = len(self.objects)
        self.models_f = np.zeros((n, 16), dtype='f4')
        self.inv_f = np.zeros((n, 16), dtype='f4')
        self.mats_f = np.zeros((n, 4), dtype='f4')

        self._update_matrix()
        self._matrix_to_ssbo()

    def update_gpu_buffers(self):
        """Update GPU buffers when objects list changes"""
        n = len(self.objects)
        self.models_f = np.zeros((n, 16), dtype='f4')
        self.inv_f = np.zeros((n, 16), dtype='f4')
        self.mats_f = np.zeros((n, 4), dtype='f4')

        self._update_matrix()
        self._matrix_to_ssbo()

    def render(self):
        # Note: Animation code removed - will be handled by physics system
        self.time += 0.01

        # Update physics if in scene mode
        delta_time = 0.016  # Approximate 60 FPS
        self.update_physics(delta_time)

        if (self.raytracer is not None):
            # Actualizar buffers solo si cambiaron los objetos
            if self._needs_buffer_update:
                self.update_gpu_buffers()
                self._needs_buffer_update = False
                # Reset primitive cache
                self._cached_primitives = None

            self._update_matrix()
            self._matrix_to_ssbo()
            self.raytracer.run()
                
    def on_resize(self, width, height):
        super().on_resize(width, height)
        self.width, self.height = width, height
        self.camera.aspect = width / height

    def add_physics_object(self, obj, physics_props=None):
        """Add an object with physics properties"""
        # Use the default physics material created during initialization
        if not self.add_object(obj, self._default_physics_material):
            return None

        # Then add to physics world
        physics_obj = self.physics_world.add_object(obj, physics_props)
        self.physics_objects[obj.name] = physics_obj
        return physics_obj

    def remove_physics_object(self, obj):
        """Remove an object with physics cleanup"""
        # Remove from physics world first
        if obj.name in self.physics_objects:
            self.physics_world.remove_object(self.physics_objects[obj.name])
            del self.physics_objects[obj.name]

        # Then remove from regular scene
        self.remove_object(obj)

    def set_mode(self, mode: str):
        """Switch between editor and scene modes"""
        if mode not in ["editor", "scene"]:
            print(f"Invalid mode: {mode}. Use 'editor' or 'scene'")
            return

        if mode == self.current_mode:
            return  # Already in this mode

        print(f"Switching from {self.current_mode} mode to {mode} mode")

        if mode == "scene":
            # Entering scene mode - save current state and start physics
            self.physics_world.save_scene_state()
            print("Scene state saved. Physics simulation starting...")
        else:  # mode == "editor"
            # Entering editor mode - restore original state
            self.physics_world.restore_scene_state()
            print("Returned to editor mode. Objects restored to original positions.")

        self.current_mode = mode

    def update_physics(self, delta_time: float):
        """Update physics simulation if in scene mode and not paused"""
        if self.current_mode == "scene" and not self.physics_paused:
            self.physics_world.update(delta_time)

    def get_mode(self) -> str:
        """Get current mode"""
        return self.current_mode

    def toggle_gravity(self):
        """Toggle gravity for all physics objects"""
        for physics_obj in self.physics_world.physics_objects:
            physics_obj.physics.gravity_enabled = not physics_obj.physics.gravity_enabled
        state = "enabled" if any(p.physics.gravity_enabled for p in self.physics_world.physics_objects) else "disabled"
        print(f"Gravity {state} for all objects")

    def toggle_collisions(self):
        """Toggle collisions for all physics objects"""
        for physics_obj in self.physics_world.physics_objects:
            physics_obj.physics.collision_enabled = not physics_obj.physics.collision_enabled
        state = "enabled" if any(p.physics.collision_enabled for p in self.physics_world.physics_objects) else "disabled"
        print(f"Collisions {state} for all objects")

    def save_scene(self, filepath: str = None) -> bool:
        """Save the current scene to a file"""
        # Capture current scene state
        scene_state = self.scene_manager.capture_scene_state(self)
        return self.scene_manager.save_scene(filepath)

    def load_scene(self, filepath: str) -> bool:
        """Load a scene from a file"""
        scene_state = self.scene_manager.load_scene(filepath)
        if scene_state:
            self.scene_manager.apply_scene_state(self, scene_state)
            # Update GPU buffers after loading
            if hasattr(self, 'update_gpu_buffers'):
                self.update_gpu_buffers()
            return True
        return False

    def new_scene(self, scene_name: str = "Untitled Scene"):
        """Create a new empty scene"""
        # Clear existing objects
        self.physics_world.physics_objects.clear()
        self.objects.clear()
        self.graphics.clear()

        # Create new scene state
        self.scene_manager.new_scene(scene_name)

        # Update GPU buffers
        if hasattr(self, 'update_gpu_buffers'):
            self.update_gpu_buffers()

        print(f"New scene created: {scene_name}")

    def list_scenes(self):
        """List all available scene files"""
        return self.scene_manager.list_scenes()

    def get_scene_info(self, filename: str):
        """Get information about a scene file"""
        return self.scene_manager.get_scene_info(filename)

    def play_physics(self):
        """Start or resume physics simulation"""
        if self.current_mode == "editor":
            # Switch to scene mode and start physics
            self.set_mode("scene")
        else:
            # Resume physics if paused
            self.physics_paused = False
            print("Physics simulation resumed")

    def pause_physics(self):
        """Pause physics simulation"""
        if self.current_mode == "scene":
            self.physics_paused = True
            print("Physics simulation paused")

    def reset_physics(self):
        """Reset physics simulation to initial state"""
        if self.current_mode == "scene":
            # Restore the saved scene state
            self.physics_world.restore_scene_state()
            self.physics_paused = False
            print("Physics simulation reset to initial state")

    def is_physics_running(self) -> bool:
        """Check if physics simulation is currently running"""
        return self.current_mode == "scene" and not self.physics_paused

    def is_physics_paused(self) -> bool:
        """Check if physics simulation is paused"""
        return self.current_mode == "scene" and self.physics_paused

    def set_gravity_strength(self, strength: float):
        """Set gravity strength (negative values for downward gravity)"""
        self.physics_world.gravity_system.gravity_strength = strength
        self.physics_world.gravity_system.gravity_vector = glm.vec3(0.0, strength, 0.0)
        print(f"Gravity strength set to: {strength} m/s²")

    def get_gravity_strength(self) -> float:
        """Get current gravity strength"""
        return self.physics_world.gravity_system.gravity_strength

    def set_global_bounciness(self, bounciness: float):
        """Set bounciness for all physics objects"""
        for physics_obj in self.physics_world.physics_objects:
            physics_obj.physics.bounciness = max(0.0, min(1.0, bounciness))
        print(f"Global bounciness set to: {bounciness}")

    def set_global_friction(self, friction: float):
        """Set friction for all physics objects"""
        for physics_obj in self.physics_world.physics_objects:
            physics_obj.physics.friction = max(0.0, min(1.0, friction))
        print(f"Global friction set to: {friction}")

    def set_global_angular_friction(self, angular_friction: float):
        """Set angular friction for all physics objects"""
        for physics_obj in self.physics_world.physics_objects:
            physics_obj.physics.angular_friction = max(0.0, min(1.0, angular_friction))
        print(f"Global angular friction set to: {angular_friction}")

    def apply_impulse_to_object(self, obj_name: str, impulse: glm.vec3):
        """Apply an impulse to a specific object"""
        for physics_obj in self.physics_world.physics_objects:
            if physics_obj.obj.name == obj_name:
                physics_obj.physics.velocity += impulse / physics_obj.physics.mass
                print(f"Applied impulse {impulse} to {obj_name}")
                return True
        print(f"Object {obj_name} not found")
        return False

    def set_object_properties(self, obj_name: str, mass: float = None, bounciness: float = None,
                            friction: float = None, angular_friction: float = None):
        """Set physics properties for a specific object"""
        for physics_obj in self.physics_world.physics_objects:
            if physics_obj.obj.name == obj_name:
                if mass is not None:
                    physics_obj.physics.mass = max(0.1, mass)
                if bounciness is not None:
                    physics_obj.physics.bounciness = max(0.0, min(1.0, bounciness))
                if friction is not None:
                    physics_obj.physics.friction = max(0.0, min(1.0, friction))
                if angular_friction is not None:
                    physics_obj.physics.angular_friction = max(0.0, min(1.0, angular_friction))
                print(f"Updated properties for {obj_name}")
                return True
        print(f"Object {obj_name} not found")
        return False

    def get_physics_stats(self) -> dict:
        """Get current physics statistics"""
        total_objects = len(self.physics_world.physics_objects)
        moving_objects = sum(1 for p in self.physics_world.physics_objects
                           if glm.length(p.physics.velocity) > 0.1)
        rotating_objects = sum(1 for p in self.physics_world.physics_objects
                             if glm.length(p.physics.angular_velocity) > 0.1)

        # Calculate average velocities for performance monitoring
        if total_objects > 0:
            avg_velocity = sum(glm.length(p.physics.velocity) for p in self.physics_world.physics_objects) / total_objects
            max_velocity = max(glm.length(p.physics.velocity) for p in self.physics_world.physics_objects)
        else:
            avg_velocity = 0.0
            max_velocity = 0.0

        return {
            "total_objects": total_objects,
            "moving_objects": moving_objects,
            "rotating_objects": rotating_objects,
            "average_velocity": avg_velocity,
            "max_velocity": max_velocity,
            "gravity_strength": self.get_gravity_strength(),
            "physics_running": self.is_physics_running(),
            "physics_paused": self.is_physics_paused(),
            "current_mode": self.current_mode
        }

    def optimize_physics(self):
        """Optimize physics performance by removing stationary objects from simulation"""
        optimized_count = 0
        for physics_obj in self.physics_world.physics_objects[:]:  # Copy list to avoid modification issues
            # Check if object is essentially stationary
            velocity_magnitude = glm.length(physics_obj.physics.velocity)
            angular_velocity_magnitude = glm.length(physics_obj.physics.angular_velocity)

            # If object hasn't moved significantly in a while, mark for optimization
            if (velocity_magnitude < 0.01 and
                angular_velocity_magnitude < 0.01 and
                physics_obj.obj.position.y > -2.5):  # Not fallen off the world

                # Zero out velocities to prevent jitter
                physics_obj.physics.velocity = glm.vec3(0.0, 0.0, 0.0)
                physics_obj.physics.angular_velocity = glm.vec3(0.0, 0.0, 0.0)
                optimized_count += 1

        if optimized_count > 0:
            print(f"Physics optimization: {optimized_count} stationary objects stabilized")

    def add_advanced_physics_features(self):
        """Add advanced physics features for enhanced realism"""
        # Add wind force simulation
        self.wind_force = glm.vec3(0.0, 0.0, 0.0)  # Can be modified externally
        self.wind_enabled = False

        # Add air resistance
        self.air_resistance = 0.01  # Coefficient for air drag

        # Add magnetic forces (for future expansion)
        self.magnetic_forces = []

    def apply_wind_force(self, delta_time: float):
        """Apply wind forces to objects"""
        if not self.wind_enabled or self.current_mode != "scene":
            return

        for physics_obj in self.physics_world.physics_objects:
            if physics_obj.physics.gravity_enabled:  # Only affect objects affected by gravity
                # Apply wind force (scaled by object mass for realism)
                wind_acceleration = self.wind_force / physics_obj.physics.mass
                physics_obj.physics.velocity += wind_acceleration * delta_time

    def apply_air_resistance(self, delta_time: float):
        """Apply air resistance/drag forces"""
        if self.current_mode != "scene":
            return

        for physics_obj in self.physics_world.physics_objects:
            velocity_magnitude = glm.length(physics_obj.physics.velocity)
            if velocity_magnitude > 0.01:  # Only apply if moving
                # Drag force opposes velocity direction
                drag_direction = -glm.normalize(physics_obj.physics.velocity)
                drag_magnitude = self.air_resistance * velocity_magnitude * velocity_magnitude
                drag_force = drag_direction * drag_magnitude

                # Apply drag (F = ma, so a = F/m)
                physics_obj.physics.velocity += (drag_force / physics_obj.physics.mass) * delta_time

    def set_wind_force(self, wind_vector: glm.vec3, enable: bool = True):
        """Set wind force vector and enable/disable wind"""
        self.wind_force = wind_vector
        self.wind_enabled = enable
        if enable:
            print(f"Wind force enabled: {wind_vector}")
        else:
            print("Wind force disabled")

    def create_realistic_scene(self, scene_type: str = "random"):
        """Create pre-configured realistic physics scenes"""
        # Clear existing objects
        self.new_scene(f"Realistic {scene_type.title()} Scene")

        if scene_type == "random":
            # Create random assortment of objects
            import random
            for i in range(8):
                x = random.uniform(-3, 3)
                z = random.uniform(-3, 3)
                y = random.uniform(2, 6)

                # Random physics properties
                mass = random.uniform(0.5, 2.0)
                bounciness = random.uniform(0.3, 0.9)
                friction = random.uniform(0.1, 0.5)

                # Create cube with random properties
                from .cube import Cube
                cube = Cube(position=glm.vec3(x, y, z))
                physics_props = PhysicsProperties(
                    mass=mass,
                    bounciness=bounciness,
                    friction=friction,
                    gravity_enabled=True,
                    collision_enabled=True
                )
                self.add_physics_object(cube, physics_props)

        elif scene_type == "stack":
            # Create a stack of cubes
            stack_height = 5
            for i in range(stack_height):
                y = -2.5 + i * 1.1  # Slight gap between cubes
                from .cube import Cube
                cube = Cube(position=glm.vec3(0, y, 0))
                physics_props = PhysicsProperties(
                    mass=1.0,
                    bounciness=0.4,
                    friction=0.3,
                    gravity_enabled=True,
                    collision_enabled=True
                )
                self.add_physics_object(cube, physics_props)

        elif scene_type == "domino":
            # Create a domino chain
            domino_count = 10
            for i in range(domino_count):
                x = i * 1.2 - 5  # Space them out
                from .cube import Cube
                cube = Cube(position=glm.vec3(x, -2.0, 0), scale=glm.vec3(0.3, 1.0, 0.8))
                physics_props = PhysicsProperties(
                    mass=0.5,
                    bounciness=0.2,
                    friction=0.6,  # Higher friction for stability
                    gravity_enabled=True,
                    collision_enabled=True
                )
                self.add_physics_object(cube, physics_props)

        print(f"Created realistic {scene_type} scene with {len(self.objects)} objects")

    def export_physics_data(self, filename: str = None) -> str:
        """Export physics simulation data for analysis"""
        if not filename:
            filename = f"physics_data_{int(__import__('time').time())}.csv"

        stats = self.get_physics_stats()

        # Create CSV header
        csv_data = "timestamp,total_objects,moving_objects,rotating_objects,avg_velocity,max_velocity,gravity,physics_running,mode\n"

        # Add current data
        import time
        timestamp = time.time()
        csv_data += ",".join([
            str(timestamp),
            str(stats["total_objects"]),
            str(stats["moving_objects"]),
            str(stats["rotating_objects"]),
            ".3f",
            ".3f",
            ".2f",
            str(stats["physics_running"]),
            stats["current_mode"]
        ]) + "\n"

        # Write to file
        with open(filename, 'w') as f:
            f.write(csv_data)

        print(f"Physics data exported to: {filename}")
        return filename

    def run_physics_benchmark(self, duration: float = 5.0) -> dict:
        """Run a physics performance benchmark"""
        print(f"Running physics benchmark for {duration} seconds...")

        # Setup benchmark scene
        self.create_realistic_scene("random")

        # Benchmark variables
        start_time = __import__('time').time()
        frame_count = 0
        total_objects = len(self.physics_world.physics_objects)

        # Start physics
        self.play_physics()

        # Run benchmark
        while (__import__('time').time() - start_time) < duration:
            # Simulate one frame
            self.update_physics(1.0/60.0)  # 60 FPS
            frame_count += 1

            # Periodic optimization
            if frame_count % 60 == 0:  # Every second
                self.optimize_physics()

        end_time = __import__('time').time()
        actual_duration = end_time - start_time

        # Calculate performance metrics
        fps = frame_count / actual_duration
        objects_per_second = (total_objects * frame_count) / actual_duration

        benchmark_results = {
            "duration": actual_duration,
            "frames": frame_count,
            "fps": fps,
            "total_objects": total_objects,
            "objects_per_second": objects_per_second,
            "average_frame_time": 1000.0 / fps,  # ms
        }

        print(".2f")
        print(".0f")
        print(".0f")
        return benchmark_results
