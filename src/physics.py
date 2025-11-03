"""
Physics system for 3D simulation with gravity and collision detection.
"""

import glm
import math
import numpy as np
from typing import List, Optional, Tuple


class PhysicsProperties:
    """Physics properties for individual objects"""

    def __init__(self,
                 mass: float = 1.0,
                 gravity_enabled: bool = True,
                 collision_enabled: bool = True,
                 bounciness: float = 0.8,
                 friction: float = 0.3,
                 angular_friction: float = 0.1,
                 velocity: glm.vec3 = None,
                 angular_velocity: glm.vec3 = None):
        self.mass = mass
        self.gravity_enabled = gravity_enabled
        self.collision_enabled = collision_enabled
        self.bounciness = bounciness  # 0.0 = no bounce, 1.0 = perfect bounce
        self.friction = friction  # 0.0 = no friction, 1.0 = max friction
        self.angular_friction = angular_friction  # Angular damping
        self.velocity = velocity or glm.vec3(0.0, 0.0, 0.0)
        self.angular_velocity = angular_velocity or glm.vec3(0.0, 0.0, 0.0)

        # Calculate moment of inertia for a cube (simplified)
        # I = (1/6) * mass * (width² + height² + depth²)
        # Assuming unit cube, I ≈ (1/6) * mass * 3 = 0.5 * mass
        self.moment_of_inertia = 0.5 * mass

    def copy(self):
        """Create a copy of these physics properties"""
        return PhysicsProperties(
            mass=self.mass,
            gravity_enabled=self.gravity_enabled,
            collision_enabled=self.collision_enabled,
            bounciness=self.bounciness,
            friction=self.friction,
            velocity=glm.vec3(self.velocity),
            angular_velocity=glm.vec3(self.angular_velocity)
        )


class AABB:
    """Axis-Aligned Bounding Box for collision detection"""

    def __init__(self, min_point: glm.vec3, max_point: glm.vec3):
        self.min = min_point
        self.max = max_point

    @property
    def center(self) -> glm.vec3:
        return (self.min + self.max) * 0.5

    @property
    def size(self) -> glm.vec3:
        return self.max - self.min

    def intersects(self, other: 'AABB') -> bool:
        """Check if this AABB intersects with another"""
        return (self.min.x <= other.max.x and self.max.x >= other.min.x and
                self.min.y <= other.max.y and self.max.y >= other.min.y and
                self.min.z <= other.max.z and self.max.z >= other.min.z)

    def contains_point(self, point: glm.vec3) -> bool:
        """Check if a point is inside this AABB"""
        return (self.min.x <= point.x <= self.max.x and
                self.min.y <= point.y <= self.max.y and
                self.min.z <= point.z <= self.max.z)


class PhysicsObject:
    """Wrapper for objects with physics properties"""

    def __init__(self, obj, physics_props: PhysicsProperties = None):
        self.obj = obj  # The actual 3D object (cube, sphere, etc.)
        self.physics = physics_props or PhysicsProperties()
        self.original_position = glm.vec3(obj.position)  # Store original position
        self.original_rotation = glm.vec3(obj.rotation)  # Store original rotation
        self.original_scale = glm.vec3(obj.scale)  # Store original scale

    def get_aabb(self) -> AABB:
        """Get the axis-aligned bounding box for this object"""
        # Assuming objects are centered at origin with size 1x1x1
        # This can be improved based on actual object bounds
        half_size = glm.vec3(0.5, 0.5, 0.5) * self.obj.scale
        min_point = self.obj.position - half_size
        max_point = self.obj.position + half_size
        return AABB(min_point, max_point)

    def save_state(self):
        """Save current state as original state"""
        self.original_position = glm.vec3(self.obj.position)
        self.original_rotation = glm.vec3(self.obj.rotation)
        self.original_scale = glm.vec3(self.obj.scale)

    def restore_state(self):
        """Restore object to original state"""
        self.obj.position = glm.vec3(self.original_position)
        self.obj.rotation = glm.vec3(self.original_rotation)
        self.obj.scale = glm.vec3(self.original_scale)
        # Reset physics state
        self.physics.velocity = glm.vec3(0.0, 0.0, 0.0)
        self.physics.angular_velocity = glm.vec3(0.0, 0.0, 0.0)


class GravitySystem:
    """Handles gravitational forces"""

    def __init__(self, gravity_strength: float = -9.81):
        self.gravity_strength = gravity_strength  # m/s²
        self.gravity_vector = glm.vec3(0.0, gravity_strength, 0.0)

    def apply_gravity(self, physics_obj: PhysicsObject, delta_time: float):
        """Apply gravitational force to a physics object"""
        if physics_obj.physics.gravity_enabled:
            # F = ma, but since mass cancels out in acceleration, we just add gravity
            physics_obj.physics.velocity += self.gravity_vector * delta_time


class CollisionSystem:
    """Handles collision detection and response"""

    def __init__(self):
        self.collision_pairs = []  # Cache for collision pairs

    def check_collision(self, obj1: PhysicsObject, obj2: PhysicsObject) -> Optional[Tuple[glm.vec3, glm.vec3, float]]:
        """
        Check collision between two physics objects
        Returns: (collision_normal, collision_point, penetration_depth) or None if no collision
        """
        if not (obj1.physics.collision_enabled and obj2.physics.collision_enabled):
            return None

        aabb1 = obj1.get_aabb()
        aabb2 = obj2.get_aabb()

        if not aabb1.intersects(aabb2):
            return None

        # Calculate penetration depth and collision normal
        overlap_x = min(aabb1.max.x, aabb2.max.x) - max(aabb1.min.x, aabb2.min.x)
        overlap_y = min(aabb1.max.y, aabb2.max.y) - max(aabb1.min.y, aabb2.min.y)
        overlap_z = min(aabb1.max.z, aabb2.max.z) - max(aabb1.min.z, aabb2.min.z)

        # Find the axis with minimum penetration
        min_overlap = min(overlap_x, overlap_y, overlap_z)

        if min_overlap == overlap_x:
            # Collision along X axis
            if aabb1.center.x < aabb2.center.x:
                collision_normal = glm.vec3(-1.0, 0.0, 0.0)  # obj1 is left of obj2
            else:
                collision_normal = glm.vec3(1.0, 0.0, 0.0)   # obj1 is right of obj2
        elif min_overlap == overlap_y:
            # Collision along Y axis
            if aabb1.center.y < aabb2.center.y:
                collision_normal = glm.vec3(0.0, -1.0, 0.0)  # obj1 is below obj2
            else:
                collision_normal = glm.vec3(0.0, 1.0, 0.0)   # obj1 is above obj2
        else:
            # Collision along Z axis
            if aabb1.center.z < aabb2.center.z:
                collision_normal = glm.vec3(0.0, 0.0, -1.0)  # obj1 is behind obj2
            else:
                collision_normal = glm.vec3(0.0, 0.0, 1.0)   # obj1 is in front of obj2

        # Collision point is the center of the overlapping region
        collision_point = (aabb1.center + aabb2.center) * 0.5

        return collision_normal, collision_point, min_overlap

    def resolve_collision(self, obj1: PhysicsObject, obj2: PhysicsObject,
                         collision_normal: glm.vec3, collision_point: glm.vec3, penetration_depth: float):
        """Resolve collision between two objects"""
        # Separate objects to prevent overlap using actual penetration depth
        separation_distance = penetration_depth + 0.01  # Add small buffer to prevent sticking
        obj1.obj.position -= collision_normal * separation_distance * 0.5
        obj2.obj.position += collision_normal * separation_distance * 0.5

        # Calculate relative velocity
        relative_velocity = obj2.physics.velocity - obj1.physics.velocity
        velocity_along_normal = glm.dot(relative_velocity, collision_normal)

        # Don't resolve if velocities are separating
        if velocity_along_normal > 0:
            return

        # Calculate restitution (bounciness)
        restitution = min(obj1.physics.bounciness, obj2.physics.bounciness)

        # Calculate impulse scalar
        impulse_scalar = -(1 + restitution) * velocity_along_normal
        impulse_scalar /= (1 / obj1.physics.mass + 1 / obj2.physics.mass)

        # Apply impulse
        impulse = impulse_scalar * collision_normal
        obj1.physics.velocity -= impulse / obj1.physics.mass
        obj2.physics.velocity += impulse / obj2.physics.mass

        # Apply friction
        friction = min(obj1.physics.friction, obj2.physics.friction)
        tangent = relative_velocity - (glm.dot(relative_velocity, collision_normal) * collision_normal)
        if glm.length(tangent) > 0.001:  # Avoid division by zero
            tangent = glm.normalize(tangent)
            friction_impulse = -glm.dot(relative_velocity, tangent) * friction * tangent
            obj1.physics.velocity -= friction_impulse / obj1.physics.mass
            obj2.physics.velocity += friction_impulse / obj2.physics.mass


class PhysicsWorld:
    """Main physics world that coordinates all physics systems"""

    def __init__(self, gravity_strength: float = -9.81):
        self.gravity_system = GravitySystem(gravity_strength)
        self.collision_system = CollisionSystem()
        self.physics_objects: List[PhysicsObject] = []
        self.fixed_timestep = 1.0 / 60.0  # 60 FPS physics
        self.accumulated_time = 0.0

    def add_object(self, obj, physics_props: PhysicsProperties = None) -> PhysicsObject:
        """Add an object to the physics world"""
        physics_obj = PhysicsObject(obj, physics_props)
        physics_obj.save_state()  # Save initial state
        self.physics_objects.append(physics_obj)
        return physics_obj

    def remove_object(self, physics_obj: PhysicsObject):
        """Remove an object from the physics world"""
        if physics_obj in self.physics_objects:
            self.physics_objects.remove(physics_obj)

    def update(self, delta_time: float):
        """Update physics simulation"""
        self.accumulated_time += delta_time

        # Fixed timestep updates
        while self.accumulated_time >= self.fixed_timestep:
            self._fixed_update(self.fixed_timestep)
            self.accumulated_time -= self.fixed_timestep

    def _fixed_update(self, delta_time: float):
        """Fixed timestep physics update"""
        # Apply gravity to all objects
        for physics_obj in self.physics_objects:
            self.gravity_system.apply_gravity(physics_obj, delta_time)

        # Apply angular damping
        for physics_obj in self.physics_objects:
            # Apply angular friction/damping
            damping_factor = 1.0 - physics_obj.physics.angular_friction
            physics_obj.physics.angular_velocity *= damping_factor

            # Stop very small rotations
            if glm.length(physics_obj.physics.angular_velocity) < 0.01:
                physics_obj.physics.angular_velocity = glm.vec3(0.0, 0.0, 0.0)

        # Integrate velocities to update positions
        for physics_obj in self.physics_objects:
            physics_obj.obj.position += physics_obj.physics.velocity * delta_time
            physics_obj.obj.rotation += physics_obj.physics.angular_velocity * delta_time

        # Check and resolve collisions
        self._handle_collisions()

        # Apply ground collision (simple ground plane at y = -3)
        self._handle_ground_collisions()

    def _handle_collisions(self):
        """Handle collisions between all physics objects"""
        for i, obj1 in enumerate(self.physics_objects):
            for j, obj2 in enumerate(self.physics_objects[i+1:], i+1):
                collision = self.collision_system.check_collision(obj1, obj2)
                if collision:
                    normal, point, penetration = collision
                    self.collision_system.resolve_collision(obj1, obj2, normal, point, penetration)

    def _handle_ground_collisions(self):
        """Handle collisions with ground plane"""
        ground_y = -3.0
        ground_normal = glm.vec3(0.0, 1.0, 0.0)

        for physics_obj in self.physics_objects:
            if not physics_obj.physics.collision_enabled:
                continue

            # Check if object is below ground
            aabb = physics_obj.get_aabb()
            if aabb.min.y <= ground_y:
                # Object is touching or below ground
                penetration = ground_y - aabb.min.y

                # Move object up to ground level
                physics_obj.obj.position.y += penetration

                # Bounce off ground
                if physics_obj.physics.velocity.y < 0:  # Moving downward
                    physics_obj.physics.velocity.y *= -physics_obj.physics.bounciness

                    # Apply friction to horizontal movement
                    friction_factor = 1.0 - physics_obj.physics.friction * 0.1
                    physics_obj.physics.velocity.x *= friction_factor
                    physics_obj.physics.velocity.z *= friction_factor

                    # Stop very small bounces
                    if abs(physics_obj.physics.velocity.y) < 0.1:
                        physics_obj.physics.velocity.y = 0.0

    def save_scene_state(self):
        """Save the current state of all objects"""
        for physics_obj in self.physics_objects:
            physics_obj.save_state()

    def restore_scene_state(self):
        """Restore all objects to their saved states"""
        for physics_obj in self.physics_objects:
            physics_obj.restore_state()
