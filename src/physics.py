"""
Physics system for 3D simulation with gravity and collision detection.
"""

import glm
import math
import numpy as np
from typing import List, Optional, Tuple
import fcl


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
        # Sleeping parameters
        self.is_sleeping = False
        self.sleep_timer = 0.0
        self.sleep_linear_threshold = 0.05
        self.sleep_angular_threshold = 0.02
        self.time_to_sleep = 0.6

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
        # Track previous position for simple swept-AABB CCD
        self.previous_position = glm.vec3(obj.position)
        # AABB cache and transform signature to avoid recomputing every frame
        self._cached_aabb: Optional[AABB] = None
        self._last_transform_sig = None

        # FCL collision object
        self.fcl_geometry = fcl.Box(obj.scale.x, obj.scale.y, obj.scale.z)
        q = glm.quat(obj.rotation)
        R = glm.mat3_cast(q)
        self.fcl_transform = fcl.Transform(np.array(R), np.array(obj.position))
        self.fcl_object = fcl.CollisionObject(self.fcl_geometry, self.fcl_transform)

    def get_aabb(self) -> AABB:
        """Get the axis-aligned bounding box for this object"""
        # Use the object's own get_aabb method if available (for proper rotation handling)
        if hasattr(self.obj, 'get_aabb') and callable(getattr(self.obj, 'get_aabb')):
            return self.obj.get_aabb()
        else:
            # Fallback: Assuming objects are centered at origin with size 1x1x1
            # This can be improved based on actual object bounds
            half_size = glm.vec3(0.5, 0.5, 0.5) * self.obj.scale
            min_point = self.obj.position - half_size
            max_point = self.obj.position + half_size
            return AABB(min_point, max_point)

    def get_cached_aabb(self) -> AABB:
        """Return cached AABB, recomputing only when transform changed."""
        sig = (round(float(self.obj.position.x), 6), round(float(self.obj.position.y), 6), round(float(self.obj.position.z), 6),
               round(float(self.obj.rotation.x), 4), round(float(self.obj.rotation.y), 4), round(float(self.obj.rotation.z), 4),
               round(float(self.obj.scale.x), 6), round(float(self.obj.scale.y), 6), round(float(self.obj.scale.z), 6))
        if self._cached_aabb is None or self._last_transform_sig != sig:
            # Recompute by delegating to object's get_aabb if present
            if hasattr(self.obj, 'get_aabb') and callable(getattr(self.obj, 'get_aabb')):
                self._cached_aabb = self.obj.get_aabb()
            else:
                half_size = glm.vec3(0.5, 0.5, 0.5) * self.obj.scale
                min_point = self.obj.position - half_size
                max_point = self.obj.position + half_size
                self._cached_aabb = AABB(min_point, max_point)
            self._last_transform_sig = sig
        return self._cached_aabb

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

    def compute_inertia_tensor(self) -> glm.mat3:
        """
        Calcula el tensor de inercia 3D real basado en la geometría del objeto.
        Para un cubo: I = (m/12) * diag(h²+d², w²+d², w²+h²)
        """
        # Obtener dimensiones del objeto
        scale = self.obj.scale
        mass = self.physics.mass

        # Para una caja (aproximación para la mayoría de objetos)
        w, h, d = scale.x, scale.y, scale.z

        # Tensor de inercia para una caja sólida
        Ix = (mass / 12.0) * (h * h + d * d)
        Iy = (mass / 12.0) * (w * w + d * d)
        Iz = (mass / 12.0) * (w * w + h * h)

        # Crear matriz diagonal
        inertia = glm.mat3(
            Ix, 0.0, 0.0,
            0.0, Iy, 0.0,
            0.0, 0.0, Iz
        )

        return inertia

    def get_inverse_inertia_tensor_world(self) -> glm.mat3:
        """
        Obtiene el tensor de inercia inverso en espacio mundial.
        Necesario para rotaciones correctas.
        """
        # Obtener matriz de rotación del objeto
        if hasattr(self.obj, 'get_rotation_matrix'):
            R = self.obj.get_rotation_matrix()
        else:
            # Construir desde euler angles
            rx, ry, rz = self.obj.rotation
            R = glm.mat3(glm.rotate(glm.mat4(1.0), rz, glm.vec3(0, 0, 1)))
            R = glm.mat3(glm.rotate(glm.mat4(R), ry, glm.vec3(0, 1, 0)))
            R = glm.mat3(glm.rotate(glm.mat4(R), rx, glm.vec3(1, 0, 0)))

        # I_local
        I = self.compute_inertia_tensor()

        # I_world = R * I_local * R^T
        I_world = R * I * glm.transpose(R)

        # Invertir (para matrices diagonales pequeñas)
        I_inv = glm.inverse(I_world)

        return I_inv


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
    """Fluid and precise collision detection and response system"""

    def __init__(self):
        self.collision_tolerance = 0.01  # Higher tolerance to prevent micro-collisions

    @staticmethod
    def _union_aabb(a: AABB, b: AABB) -> AABB:
        """Return the AABB that encloses both a and b"""
        min_point = glm.vec3(min(a.min.x, b.min.x), min(a.min.y, b.min.y), min(a.min.z, b.min.z))
        max_point = glm.vec3(max(a.max.x, b.max.x), max(a.max.y, b.max.y), max(a.max.z, b.max.z))
        return AABB(min_point, max_point)

    def _get_obb(self, phys_obj: PhysicsObject):
        """Try to extract an OBB (center, axes[3], half_extents[3]) from the object.

        Fallbacks to AABB if model info is not available.
        """
        obj = phys_obj.obj
        # If object provides a model matrix and scale, use it as OBB basis
        if hasattr(obj, 'get_model_matrix') and hasattr(obj, 'scale'):
            model = obj.get_model_matrix()
            # center = model * vec4(0,0,0,1)
            center_v4 = model * glm.vec4(0, 0, 0, 1)
            center = glm.vec3(center_v4.x, center_v4.y, center_v4.z)

            # axis vectors (rotation+scale) - multiply by vec4 with w=0
            ax = model * glm.vec4(1, 0, 0, 0)
            ay = model * glm.vec4(0, 1, 0, 0)
            az = model * glm.vec4(0, 0, 1, 0)
            axis_x = glm.vec3(ax.x, ax.y, ax.z)
            axis_y = glm.vec3(ay.x, ay.y, ay.z)
            axis_z = glm.vec3(az.x, az.y, az.z)

            half_extents = glm.vec3(glm.length(axis_x), glm.length(axis_y), glm.length(axis_z))
            # normalize axes
            if glm.length(axis_x) > 1e-9:
                axis_x = axis_x / glm.length(axis_x)
            if glm.length(axis_y) > 1e-9:
                axis_y = axis_y / glm.length(axis_y)
            if glm.length(axis_z) > 1e-9:
                axis_z = axis_z / glm.length(axis_z)

            return center, (axis_x, axis_y, axis_z), half_extents

        # Fallback to AABB center and world axes
        aabb = phys_obj.get_cached_aabb()
        center = aabb.center
        half = aabb.size * 0.5
        return center, (glm.vec3(1, 0, 0), glm.vec3(0, 1, 0), glm.vec3(0, 0, 1)), half

    def obb_sat(self, obj1: PhysicsObject, obj2: PhysicsObject):
        """Full SAT implementation using 15 axes (3 face normals from each box + 9 edge cross products).
        Returns (normal, penetration, contact_points) or None."""
        c1, axes1, ext1 = self._get_obb(obj1)
        c2, axes2, ext2 = self._get_obb(obj2)

        # Vector between centers
        t = c2 - c1

        best_axis = None
        best_pen = math.inf
        contact_points = []

        # Test all 15 potential separating axes
        test_axes = []
        # Face axes from box 1 (3)
        test_axes.extend(axes1)
        # Face axes from box 2 (3)
        test_axes.extend(axes2)
        # Edge cross products (9)
        for a1 in axes1:
            for a2 in axes2:
                cross = glm.cross(a1, a2)
                if glm.length(cross) > 1e-6:  # Skip if parallel
                    test_axes.append(glm.normalize(cross))

        for axis in test_axes:
            # Project both OBBs onto axis
            proj1 = abs(ext1.x * glm.dot(axis, axes1[0])) + \
                   abs(ext1.y * glm.dot(axis, axes1[1])) + \
                   abs(ext1.z * glm.dot(axis, axes1[2]))
            proj2 = abs(ext2.x * glm.dot(axis, axes2[0])) + \
                   abs(ext2.y * glm.dot(axis, axes2[1])) + \
                   abs(ext2.z * glm.dot(axis, axes2[2]))

            dist = abs(glm.dot(t, axis))
            overlap = proj1 + proj2 - dist

            if overlap <= 0:
                return None

            # Keep track of minimum penetration axis
            if overlap < best_pen:
                best_pen = overlap
                best_axis = axis

        if best_axis is None:
            return None

        # Ensure normal points from obj1 to obj2
        direction = glm.dot(best_axis, t)
        normal = best_axis if direction >= 0 else -best_axis

        # Generate contact points
        # For each box, get the vertex most extreme in direction of collision normal
        def get_support_point(center, axes, extents, dir):
            result = glm.vec3(center)
            for i in range(3):
                sign = 1.0 if glm.dot(dir, axes[i]) >= 0.0 else -1.0
                result += axes[i] * (extents[i] * sign)
            return result

        # Get deepest points
        p1 = get_support_point(c1, axes1, ext1, normal)
        p2 = get_support_point(c2, axes2, ext2, -normal)

        # Get average contact point
        contact_point = (p1 + p2) * 0.5
        contact_points.append(contact_point)

        return normal, best_pen, contact_points

    def _swept_aabb_overlap(self, obj1: PhysicsObject, obj2: PhysicsObject) -> bool:
        """Conservative swept AABB overlap test using previous and current positions.

        This is a cheap CCD filter: if the swept (union of prev and curr AABB) boxes
        don't overlap, there is no collision during the step. It's conservative and
        avoids tunneling for translational motion.
        """
        aabb1 = obj1.get_cached_aabb()
        aabb2 = obj2.get_cached_aabb()

        prev_pos1 = getattr(obj1, 'previous_position', obj1.obj.position)
        prev_pos2 = getattr(obj2, 'previous_position', obj2.obj.position)

        # Create previous AABBs by translating current AABB by the previous->current delta
        delta1 = prev_pos1 - obj1.obj.position
        delta2 = prev_pos2 - obj2.obj.position

        prev_aabb1 = AABB(aabb1.min + delta1, aabb1.max + delta1)
        prev_aabb2 = AABB(aabb2.min + delta2, aabb2.max + delta2)

        swept1 = self._union_aabb(prev_aabb1, aabb1)
        swept2 = self._union_aabb(prev_aabb2, aabb2)

        return swept1.intersects(swept2)

    def swept_aabb_toi(self, obj_moving: PhysicsObject, obj_static: PhysicsObject, dt: float) -> Optional[float]:
        """Compute time of impact (TOI) in normalized [0,1] for two moving AABBs.

        We treat obj_static as static by using relative velocity v = v_moving - v_static.
        Returns normalized t in [0,1] if collision occurs within dt, otherwise None.
        """
        if dt <= 0.0:
            return None

        # Use current AABBs as the starting boxes for TOI computation
        a_moving = obj_moving.get_cached_aabb()
        a_static = obj_static.get_cached_aabb()

        # Treat the current boxes as at time 0 and use relative velocity over dt
        a_moving_prev = a_moving
        a_static_prev = a_static

        # Relative velocity (world units per second)
        v_rel = (obj_moving.physics.velocity - obj_static.physics.velocity)

        # We want times in seconds within [0, dt]
        t_enter = -math.inf
        t_exit = math.inf

        # Helper to compute axis entry/exit
        for axis in range(3):
            if axis == 0:
                a0_min = a_moving_prev.min.x
                a0_max = a_moving_prev.max.x
                b_min = a_static_prev.min.x
                b_max = a_static_prev.max.x
                v = v_rel.x
            elif axis == 1:
                a0_min = a_moving_prev.min.y
                a0_max = a_moving_prev.max.y
                b_min = a_static_prev.min.y
                b_max = a_static_prev.max.y
                v = v_rel.y
            else:
                a0_min = a_moving_prev.min.z
                a0_max = a_moving_prev.max.z
                b_min = a_static_prev.min.z
                b_max = a_static_prev.max.z
                v = v_rel.z

            if abs(v) < 1e-8:
                # No relative motion on this axis: if separated initially, no collision
                if a0_max < b_min or a0_min > b_max:
                    return None
                else:
                    axis_entry = -math.inf
                    axis_exit = math.inf
            else:
                inv_v = 1.0 / v
                axis_entry = (b_min - a0_max) * inv_v
                axis_exit = (b_max - a0_min) * inv_v
                if axis_entry > axis_exit:
                    axis_entry, axis_exit = axis_exit, axis_entry

            t_enter = max(t_enter, axis_entry)
            t_exit = min(t_exit, axis_exit)

            if t_enter > t_exit:
                return None

        # Now t_enter..t_exit is in seconds relative to start. Check overlap with [0, dt]
        if t_enter > dt or t_exit < 0.0:
            return None

        toi = max(0.0, t_enter) / dt
        return toi

    def get_contact_manifold(self, obj1: 'PhysicsObject', obj2: 'PhysicsObject',
                            normal: glm.vec3, penetration: float) -> List[glm.vec3]:
        """
        Genera múltiples puntos de contacto (hasta 4) para mayor estabilidad.
        Usa clipping de polígonos entre las caras de colisión.
        """
        c1, axes1, ext1 = self._get_obb(obj1)
        c2, axes2, ext2 = self._get_obb(obj2)

        contact_points = []

        # Determinar qué cara de cada OBB está colisionando
        # La cara es perpendicular al eje con menor penetración

        # Encontrar la cara de referencia (en obj1) y la cara incidente (en obj2)
        def get_face_vertices(center, axes, extents, axis_idx, sign):
            """Obtiene los 4 vértices de una cara del OBB"""
            face_normal = axes[axis_idx] * sign
            face_center = center + face_normal * extents[axis_idx]

            # Los otros dos ejes forman el plano de la cara
            tangent1_idx = (axis_idx + 1) % 3
            tangent2_idx = (axis_idx + 2) % 3

            tangent1 = axes[tangent1_idx]
            tangent2 = axes[tangent2_idx]
            ext1 = extents[tangent1_idx]
            ext2 = extents[tangent2_idx]

            # Los 4 vértices de la cara
            vertices = [
                face_center + tangent1 * ext1 + tangent2 * ext2,
                face_center + tangent1 * ext1 - tangent2 * ext2,
                face_center - tangent1 * ext1 - tangent2 * ext2,
                face_center - tangent1 * ext1 + tangent2 * ext2,
            ]
            return vertices, face_normal

        # Determinar el eje de colisión principal
        best_axis = 0
        best_dot = abs(glm.dot(normal, axes1[0]))
        for i in range(1, 3):
            d = abs(glm.dot(normal, axes1[i]))
            if d > best_dot:
                best_dot = d
                best_axis = i

        # Determinar el signo (dirección) de la cara
        sign = 1.0 if glm.dot(normal, axes1[best_axis]) > 0 else -1.0

        # Obtener vértices de la cara de referencia
        ref_vertices, ref_normal = get_face_vertices(c1, axes1, ext1, best_axis, sign)

        # Obtener cara incidente de obj2 (la más antiparalela al normal)
        best_axis2 = 0
        best_dot2 = glm.dot(-normal, axes2[0])
        for i in range(1, 3):
            d = glm.dot(-normal, axes2[i])
            if d > best_dot2:
                best_dot2 = d
                best_axis2 = i

        sign2 = 1.0 if glm.dot(-normal, axes2[best_axis2]) > 0 else -1.0
        inc_vertices, inc_normal = get_face_vertices(c2, axes2, ext2, best_axis2, sign2)

        # Clipear la cara incidente contra los planos laterales de la cara de referencia
        clipped = inc_vertices[:]

        tangent1_idx = (best_axis + 1) % 3
        tangent2_idx = (best_axis + 2) % 3

        tangent1 = axes1[tangent1_idx]
        tangent2 = axes1[tangent2_idx]

        # Clipear contra los 4 planos laterales
        side_planes = [
            (tangent1, ext1[tangent1_idx]),
            (-tangent1, ext1[tangent1_idx]),
            (tangent2, ext1[tangent2_idx]),
            (-tangent2, ext1[tangent2_idx]),
        ]

        face_center = c1 + ref_normal * ext1[best_axis]

        for plane_normal, plane_offset in side_planes:
            plane_point = face_center + plane_normal * plane_offset
            clipped = self._clip_polygon_by_plane(clipped, plane_normal, plane_point)
            if len(clipped) == 0:
                break

        # Mantener solo los puntos que están debajo del plano de referencia
        for vertex in clipped:
            distance = glm.dot(vertex - face_center, ref_normal)
            if distance <= 0.01:  # Tolerancia para considerar contacto
                contact_points.append(vertex)

        # Limitar a máximo 4 puntos (los más extremos)
        if len(contact_points) > 4:
            contact_points = self._reduce_contact_points(contact_points, 4)

        # Si no se encontraron puntos, usar el centro como fallback
        if len(contact_points) == 0:
            contact_points.append((c1 + c2) * 0.5)

        return contact_points

    def _clip_polygon_by_plane(self, vertices: List[glm.vec3],
                               plane_normal: glm.vec3,
                               plane_point: glm.vec3) -> List[glm.vec3]:
        """
        Clipea un polígono contra un plano, manteniendo solo los vértices
        en el lado positivo del plano.
        """
        if len(vertices) == 0:
            return []

        clipped = []

        for i in range(len(vertices)):
            v1 = vertices[i]
            v2 = vertices[(i + 1) % len(vertices)]

            # Distancias al plano
            d1 = glm.dot(v1 - plane_point, plane_normal)
            d2 = glm.dot(v2 - plane_point, plane_normal)

            # v1 está dentro
            if d1 >= -1e-6:
                clipped.append(v1)

            # Arista cruza el plano
            if (d1 * d2) < 0:
                # Interpolar para encontrar el punto de intersección
                t = d1 / (d1 - d2)
                intersection = v1 + (v2 - v1) * t
                clipped.append(intersection)

        return clipped

    def _reduce_contact_points(self, points: List[glm.vec3], max_points: int) -> List[glm.vec3]:
        """
        Reduce el número de puntos de contacto manteniendo los más extremos
        para mejor distribución de fuerzas.
        """
        if len(points) <= max_points:
            return points

        # Encontrar el centro
        center = glm.vec3(0, 0, 0)
        for p in points:
            center += p
        center /= len(points)

        # Encontrar los 4 puntos más lejanos del centro en diferentes direcciones
        selected = []

        # Punto más lejano
        max_dist = -1
        farthest = 0
        for i, p in enumerate(points):
            dist = glm.length(p - center)
            if dist > max_dist:
                max_dist = dist
                farthest = i

        selected.append(points[farthest])

        # Siguiente punto más lejano del primero
        if len(points) > 1:
            max_dist = -1
            next_idx = 0
            for i, p in enumerate(points):
                if i == farthest:
                    continue
                dist = glm.length(p - selected[0])
                if dist > max_dist:
                    max_dist = dist
                    next_idx = i
            selected.append(points[next_idx])

        # Dos puntos más que maximicen el área
        if len(points) > 2:
            for _ in range(min(2, max_points - len(selected))):
                max_area = -1
                best_idx = 0
                for i, p in enumerate(points):
                    if p in selected:
                        continue
                    # Calcular área aproximada
                    area = 0
                    for s in selected:
                        area += glm.length(p - s)
                    if area > max_area:
                        max_area = area
                        best_idx = i
                selected.append(points[best_idx])

        return selected

    def compute_friction_impulse(self, obj1: 'PhysicsObject', obj2: 'PhysicsObject',
                                 normal: glm.vec3, rel_vel: glm.vec3,
                                 normal_impulse: float) -> glm.vec3:
        """
        Calcula el impulso de fricción de forma más precisa usando dos direcciones tangenciales.
        Implementa el modelo de Coulomb con fricción anisotrópica.
        """
        # Calcular velocidad tangencial
        vel_normal = glm.dot(rel_vel, normal) * normal
        vel_tangent = rel_vel - vel_normal

        tangent_speed = glm.length(vel_tangent)
        if tangent_speed < 1e-6:
            return glm.vec3(0, 0, 0)

        tangent_dir = vel_tangent / tangent_speed

        # Coeficiente de fricción combinado
        mu = math.sqrt(obj1.physics.friction * obj2.physics.friction)

        # Masa efectiva en dirección tangencial
        inv_mass1 = 1.0 / obj1.physics.mass if obj1.physics.mass < 100000.0 else 0.0
        inv_mass2 = 1.0 / obj2.physics.mass if obj2.physics.mass < 100000.0 else 0.0

        # Impulso de fricción máximo (ley de Coulomb)
        max_friction = abs(normal_impulse * mu)

        # Impulso necesario para detener el movimiento tangencial
        friction_impulse_mag = tangent_speed / (inv_mass1 + inv_mass2)

        # Aplicar límite de Coulomb
        if friction_impulse_mag > max_friction:
            friction_impulse_mag = max_friction

        return -tangent_dir * friction_impulse_mag


class PhysicsWorld:
    """Main physics world that coordinates all physics systems"""

    def __init__(self, gravity_strength: float = -9.81, cell_size: float = 2.0):
        self.gravity_system = GravitySystem(gravity_strength)
        self.collision_system = CollisionSystem()
        self.physics_objects: List[PhysicsObject] = []
        self.fixed_timestep = 1.0 / 60.0  # 60 FPS physics
        self.accumulated_time = 0.0
        self.collision_manager = fcl.DynamicAABBTreeCollisionManager()
        self.solver_iterations = 8  # A good balance of performance and stability

    def add_object(self, obj, physics_props: PhysicsProperties = None) -> PhysicsObject:
        """Add an object to the physics world"""
        physics_obj = PhysicsObject(obj, physics_props)
        physics_obj.save_state()  # Save initial state
        self.physics_objects.append(physics_obj)
        self.collision_manager.registerObject(physics_obj.fcl_object)
        self.collision_manager.setup()
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
        """
        Fixed timestep physics update using a modern, stable approach.
        Follows the sequence: integrate velocities -> solve constraints -> integrate positions.
        """
        # 1. Integrate velocities (apply gravity and damping)
        self._integrate_velocities(delta_time)

        # 2. Update FCL collision objects transforms
        for obj in self.physics_objects:
            if not obj.physics.is_sleeping:
                obj.fcl_transform.setTranslation(np.array(obj.obj.position))
                q = glm.quat(obj.obj.rotation)
                R = glm.mat3_cast(q)
                obj.fcl_transform.setRotation(np.array(R))
                obj.fcl_object.setTransform(obj.fcl_transform)
        
        self.collision_manager.update()

        # 3. Broad-phase collision detection using FCL
        cdata = fcl.CollisionData()
        self.collision_manager.collide(cdata, fcl.defaultCollisionCallback)

        # 4. Narrow-phase and constraint solving
        self._solve_constraints(cdata, self.solver_iterations)

        # 5. Integrate positions
        self._integrate_positions(delta_time)

        # 5. Handle ground collision as a special case for stability
        self._handle_ground_collisions()

        # 6. Update sleeping states
        self._update_sleeping_states(delta_time)

    def _integrate_velocities(self, dt: float):
        """
        Integra velocidades (semi-implicit Euler).
        Separa la integración de velocidades de la integración de posiciones.
        """
        for physics_obj in self.physics_objects:
            if physics_obj.physics.is_sleeping:
                continue

            # Aplicar gravedad
            self.gravity_system.apply_gravity(physics_obj, dt)

            # Damping de velocidad lineal
            physics_obj.physics.velocity *= 0.995

            # Damping angular
            damping = 1.0 - physics_obj.physics.angular_friction
            physics_obj.physics.angular_velocity *= damping

            # Limitar velocidades máximas
            v_mag = glm.length(physics_obj.physics.velocity)
            if v_mag > 50.0:
                physics_obj.physics.velocity = (physics_obj.physics.velocity / v_mag) * 50.0

            av_mag = glm.length(physics_obj.physics.angular_velocity)
            if av_mag > 10.0:
                physics_obj.physics.angular_velocity = (physics_obj.physics.angular_velocity / av_mag) * 10.0

    def _integrate_positions(self, dt: float):
        """
        Integra posiciones y rotaciones basándose en las velocidades actuales.
        """
        for physics_obj in self.physics_objects:
            if physics_obj.physics.is_sleeping:
                continue

            # Guardar posición anterior para CCD
            physics_obj.previous_position = glm.vec3(physics_obj.obj.position)

            # Integrar posición
            physics_obj.obj.position += physics_obj.physics.velocity * dt

            # Integrar rotación (euler integration - puede mejorarse con quaternions)
            physics_obj.obj.rotation += physics_obj.physics.angular_velocity * dt

    def _solve_constraints(self, cdata: fcl.CollisionData, iterations: int):
        """
        Resuelve contactos iterativamente usando Sequential Impulse Solver.
        Incluye warm starting para mejor convergencia.
        """
        contacts = []
        
        geom_id_to_obj = {id(obj.fcl_geometry): obj for obj in self.physics_objects}

        for contact in cdata.result.contacts:
            obj1 = geom_id_to_obj.get(id(contact.o1))
            obj2 = geom_id_to_obj.get(id(contact.o2))

            if obj1 and obj2:
                if obj1.physics.is_sleeping and obj2.physics.is_sleeping:
                    continue

                normal = glm.vec3(contact.normal)
                point = glm.vec3(contact.pos)
                penetration = contact.penetration_depth

                # FIX: Ensure normal points from obj1 to obj2
                separation_vector = obj2.obj.position - obj1.obj.position
                if glm.dot(normal, separation_vector) < 0:
                    normal = -normal

                contacts.append({
                    'obj1': obj1,
                    'obj2': obj2,
                    'normal': normal,
                    'point': point,
                    'penetration': penetration,
                    'accumulated_impulse': 0.0,
                    'accumulated_friction': glm.vec3(0, 0, 0)
                })

        # Iteratively solve the contacts
        for _ in range(iterations):
            for contact in contacts:
                self._solve_single_contact(contact)

    def _solve_single_contact(self, contact: dict):
        """
        Resuelve un único contacto aplicando impulsos.
        """

        obj1 = contact['obj1']
        obj2 = contact['obj2']
        normal = contact['normal']
        point = contact['point']
        penetration = contact['penetration']

        inv_mass1 = 1.0 / obj1.physics.mass if obj1.physics.mass < 100000.0 else 0.0
        inv_mass2 = 1.0 / obj2.physics.mass if obj2.physics.mass < 100000.0 else 0.0

        # Custom cube-cube collision response: move both cubes apart
        # Detect cubes by class name (assuming Cube class exists)
        if obj1.obj.__class__.__name__ == "Cube" and obj2.obj.__class__.__name__ == "Cube":
            # Move both cubes along the collision normal by half the penetration
            move_vec = normal * (penetration * 0.5)
            obj1.obj.position -= move_vec
            obj2.obj.position += move_vec

        # Use the full inverse inertia tensor for correct rotational physics
        inv_I1 = obj1.get_inverse_inertia_tensor_world() if inv_mass1 > 0 else glm.mat3(0.0)
        inv_I2 = obj2.get_inverse_inertia_tensor_world() if inv_mass2 > 0 else glm.mat3(0.0)

        r1 = point - obj1.obj.position
        r2 = point - obj2.obj.position

        # Relative velocity at contact point
        v_rel = (obj2.physics.velocity + glm.cross(obj2.physics.angular_velocity, r2)) - \
                (obj1.physics.velocity + glm.cross(obj1.physics.angular_velocity, r1))
        
        vel_along_normal = glm.dot(v_rel, normal)

        # Do not resolve if objects are separating
        if vel_along_normal > 0:
            return

        e = min(obj1.physics.bounciness, obj2.physics.bounciness)

        # Effective mass for the collision
        r1_cross_n = glm.cross(r1, normal)
        r2_cross_n = glm.cross(r2, normal)
        
        k_normal = inv_mass1 + inv_mass2 + glm.dot(inv_I1 * r1_cross_n, r1_cross_n) + glm.dot(inv_I2 * r2_cross_n, r2_cross_n)
        
        if k_normal < 1e-8:
            return

        # Baumgarte stabilization for positional correction
        bias_factor = 0.2
        slop = 0.01
        bias = -(bias_factor / self.fixed_timestep) * max(0.0, penetration - slop)

        # Calculate impulse magnitude
        j_n = -(vel_along_normal * (1.0 + e) + bias) / k_normal
        
        # Accumulate and clamp impulse
        old_impulse = contact['accumulated_impulse']
        contact['accumulated_impulse'] = max(0.0, old_impulse + j_n)
        j_applied = contact['accumulated_impulse'] - old_impulse
        
        impulse = normal * j_applied

        # Apply impulse
        if inv_mass1 > 0:
            obj1.physics.velocity -= impulse * inv_mass1
            obj1.physics.angular_velocity -= inv_I1 * glm.cross(r1, impulse)
        if inv_mass2 > 0:
            obj2.physics.velocity += impulse * inv_mass2
            obj2.physics.angular_velocity += inv_I2 * glm.cross(r2, impulse)
        
        # --- Friction ---
        friction_impulse = self.collision_system.compute_friction_impulse(obj1, obj2, normal, v_rel, j_applied)
        if inv_mass1 > 0:
            obj1.physics.velocity -= friction_impulse * inv_mass1
            obj1.physics.angular_velocity -= inv_I1 * glm.cross(r1, friction_impulse)
        if inv_mass2 > 0:
            obj2.physics.velocity += friction_impulse * inv_mass2
            obj2.physics.angular_velocity += inv_I2 * glm.cross(r2, friction_impulse)

    def _handle_ground_collisions(self):
        """Handle collisions with ground-like objects.

        Instead of using a hardcoded ground plane, we detect immovable
        'ground' objects (very large mass or gravity disabled) and treat
        their top AABB surface as the ground. This ensures objects rest on
        the top face of the floor quad instead of penetrating and bouncing
        off the bottom face.
        """

        # Identify candidate ground objects: large mass or gravity disabled
        ground_candidates = []
        for po in self.physics_objects:
            if not po.physics.collision_enabled:
                continue
            # Treat extremely large mass (or infinite) as immovable ground
            mass = po.physics.mass
            is_immovable = (mass >= 1e5) or (mass == float('inf')) or (not po.physics.gravity_enabled and mass > 0)
            if is_immovable:
                ground_candidates.append(po)

        # If no explicit ground objects found, keep a simple fallback plane at y=-5
        use_fallback_plane = len(ground_candidates) == 0
        fallback_y = -5.0

        for physics_obj in self.physics_objects:
            # Skip non-collidable, sleeping or ground objects themselves
            if not physics_obj.physics.collision_enabled or physics_obj.physics.is_sleeping:
                continue
            if physics_obj in ground_candidates:
                continue

            aabb = physics_obj.get_cached_aabb()

            # First try against detected ground candidates
            resolved = False
            for ground in ground_candidates:
                gaabb = ground.get_cached_aabb()

                # Check XZ overlap (simple broad-phase in plane of contact)
                if (aabb.max.x < gaabb.min.x or aabb.min.x > gaabb.max.x or
                    aabb.max.z < gaabb.min.z or aabb.min.z > gaabb.max.z):
                    continue

                # Compute the ground top Y using the object's OBB projected onto world up
                try:
                    center_g, axes_g, ext_g = self.collision_system._get_obb(ground)
                    up = glm.vec3(0.0, 1.0, 0.0)
                    half_height_world = abs(ext_g.x * glm.dot(axes_g[0], up)) + \
                                       abs(ext_g.y * glm.dot(axes_g[1], up)) + \
                                       abs(ext_g.z * glm.dot(axes_g[2], up))
                    ground_top_y = center_g.y + half_height_world
                except Exception:
                    # Fallback to AABB max if OBB computation fails
                    ground_top_y = gaabb.max.y

                # If object penetrated into the ground (its lowest point below ground top)
                if aabb.min.y < ground_top_y - self.collision_system.collision_tolerance:
                    penetration = ground_top_y - aabb.min.y
                    # Move object up so its min.y equals ground_top_y
                    physics_obj.obj.position.y += penetration

                    # If moving downward, reflect velocity using bounciness
                    if physics_obj.physics.velocity.y < 0:
                        vel_y = physics_obj.physics.velocity.y
                        physics_obj.physics.velocity.y = -vel_y * min(1.0, max(0.0, physics_obj.physics.bounciness))

                        # Apply friction to horizontal movement
                        friction_factor = 1.0 - physics_obj.physics.friction
                        physics_obj.physics.velocity.x *= friction_factor
                        physics_obj.physics.velocity.z *= friction_factor

                        # Stop very small bounces to prevent jittering
                        if abs(physics_obj.physics.velocity.y) < 0.1:
                            physics_obj.physics.velocity.y = 0.0

                    # Wake any objects supported by this one
                    self._wake_supported_objects(physics_obj)
                    resolved = True
                    break

            # Fallback to flat plane if no ground candidate handled the object
            if not resolved and use_fallback_plane:
                ground_y = fallback_y
                if aabb.min.y <= ground_y:
                    penetration = ground_y - aabb.min.y
                    physics_obj.obj.position.y += penetration
                    if physics_obj.physics.velocity.y < 0:
                        vel_y = physics_obj.physics.velocity.y
                        physics_obj.physics.velocity.y = -vel_y * physics_obj.physics.bounciness
                        friction_factor = 1.0 - physics_obj.physics.friction
                        physics_obj.physics.velocity.x *= friction_factor
                        physics_obj.physics.velocity.z *= friction_factor
                        if abs(physics_obj.physics.velocity.y) < 0.1:
                            physics_obj.physics.velocity.y = 0.0

    def _update_sleeping_states(self, delta_time: float):
        """
        Updates the sleep state of all objects based on their motion.
        """
        for obj in self.physics_objects:
            props = obj.physics
            if props.is_sleeping:
                continue

            lin_vel_sq = glm.dot(props.velocity, props.velocity)
            ang_vel_sq = glm.dot(props.angular_velocity, props.angular_velocity)

            lin_thresh_sq = props.sleep_linear_threshold ** 2
            ang_thresh_sq = props.sleep_angular_threshold ** 2

            if lin_vel_sq < lin_thresh_sq and ang_vel_sq < ang_thresh_sq:
                props.sleep_timer += delta_time
                if props.sleep_timer >= props.time_to_sleep:
                    props.is_sleeping = True
                    props.velocity = glm.vec3(0.0)
                    props.angular_velocity = glm.vec3(0.0)
            else:
                props.sleep_timer = 0.0
                props.is_sleeping = False

    def _wake_supported_objects(self, base_obj: PhysicsObject):
        """Wake up any objects that are being supported by the given object."""
        # Simple implementation: check all objects above this one
        base_aabb = base_obj.get_cached_aabb()
        for other in self.physics_objects:
            if other != base_obj and other.physics.is_sleeping:
                other_aabb = other.get_cached_aabb()
                # If object is above and overlapping in XZ plane
                if (other_aabb.min.y >= base_aabb.max.y and
                    other_aabb.min.x < base_aabb.max.x and
                    other_aabb.max.x > base_aabb.min.x and
                    other_aabb.min.z < base_aabb.max.z and
                    other_aabb.max.z > base_aabb.min.z):
                    # Wake it up
                    other.physics.is_sleeping = False
                    other.physics.sleep_timer = 0.0
                    # Recursively wake up anything supported by this object
                    self._wake_supported_objects(other)

    def save_scene_state(self):
        """Save the current state of all objects"""
        for physics_obj in self.physics_objects:
            physics_obj.save_state()

    def restore_scene_state(self):
        """Restore all objects to their saved states"""
        for physics_obj in self.physics_objects:
            physics_obj.restore_state()
