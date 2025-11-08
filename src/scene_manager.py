"""
Scene state management system for saving and loading physics scenes.
"""

import json
import os
import glm
from typing import Dict, List, Any, Optional
from .physics import PhysicsProperties


class SceneState:
    """Represents the complete state of a scene"""

    def __init__(self):
        self.objects: List[Dict[str, Any]] = []
        self.physics_settings: Dict[str, Any] = {
            "gravity_enabled": True,
            "collision_enabled": True,
            "gravity_strength": -9.81
        }
        self.metadata: Dict[str, Any] = {
            "version": "1.0",
            "scene_name": "Untitled Scene",
            "description": ""
        }

    def add_object(self, obj_name: str, obj_type: str, position: List[float],
                  rotation: List[float], scale: List[float],
                  physics_props: PhysicsProperties):
        """Add an object to the scene state"""
        obj_data = {
            "name": obj_name,
            "type": obj_type,
            "position": position,
            "rotation": rotation,
            "scale": scale,
            "physics": {
                "mass": physics_props.mass,
                "gravity_enabled": physics_props.gravity_enabled,
                "collision_enabled": physics_props.collision_enabled,
                "bounciness": physics_props.bounciness,
                "friction": physics_props.friction,
                "angular_friction": physics_props.angular_friction,
                "is_domino": physics_props.is_domino
            }
        }
        self.objects.append(obj_data)

    def clear_objects(self):
        """Remove all objects from the scene state"""
        self.objects.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Convert scene state to dictionary for JSON serialization"""
        return {
            "metadata": self.metadata,
            "physics_settings": self.physics_settings,
            "objects": self.objects
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SceneState':
        """Create scene state from dictionary"""
        state = cls()
        state.metadata = data.get("metadata", state.metadata)
        state.physics_settings = data.get("physics_settings", state.physics_settings)
        state.objects = data.get("objects", [])
        return state


class SceneManager:
    """Manages saving and loading of scene states"""

    def __init__(self, scenes_dir: str = "scenes"):
        self.scenes_dir = scenes_dir
        self.current_scene: Optional[SceneState] = None
        self.scene_file: Optional[str] = None

        # Create scenes directory if it doesn't exist
        if not os.path.exists(scenes_dir):
            os.makedirs(scenes_dir)

    def new_scene(self, scene_name: str = "Untitled Scene") -> SceneState:
        """Create a new empty scene"""
        self.current_scene = SceneState()
        self.current_scene.metadata["scene_name"] = scene_name
        self.scene_file = None
        return self.current_scene

    def save_scene(self, filepath: Optional[str] = None) -> bool:
        """Save the current scene to a file"""
        if not self.current_scene:
            print("No scene to save")
            return False

        if not filepath:
            if self.scene_file:
                filepath = self.scene_file
            else:
                # Generate default filename
                scene_name = self.current_scene.metadata["scene_name"].replace(" ", "_").lower()
                filepath = f"{self.scenes_dir}/{scene_name}.json"

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.current_scene.to_dict(), f, indent=2, ensure_ascii=False)

            self.scene_file = filepath
            print(f"Scene saved to: {filepath}")
            return True

        except Exception as e:
            print(f"Error saving scene: {e}")
            return False

    def load_scene(self, filepath: str) -> Optional[SceneState]:
        """Load a scene from a file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.current_scene = SceneState.from_dict(data)
            self.scene_file = filepath
            print(f"Scene loaded from: {filepath}")
            return self.current_scene

        except FileNotFoundError:
            print(f"Scene file not found: {filepath}")
            return None
        except json.JSONDecodeError as e:
            print(f"Invalid scene file format: {e}")
            return None
        except Exception as e:
            print(f"Error loading scene: {e}")
            return None

    def capture_scene_state(self, scene) -> SceneState:
        """Capture the current state of a running scene"""
        if not self.current_scene:
            self.current_scene = SceneState()

        self.current_scene.clear_objects()

        # Capture all physics objects
        for physics_obj in scene.physics_world.physics_objects:
            obj = physics_obj.obj
            position = [obj.position.x, obj.position.y, obj.position.z]
            rotation = [obj.rotation.x, obj.rotation.y, obj.rotation.z]
            scale = [obj.scale.x, obj.scale.y, obj.scale.z]

            # Determine object type (simplified - could be enhanced)
            obj_type = "cube"  # Default assumption

            self.current_scene.add_object(
                obj.name, obj_type, position, rotation, scale, physics_obj.physics
            )

        # Update physics settings
        self.current_scene.physics_settings["gravity_enabled"] = any(
            p.physics.gravity_enabled for p in scene.physics_world.physics_objects
        )
        self.current_scene.physics_settings["collision_enabled"] = any(
            p.physics.collision_enabled for p in scene.physics_world.physics_objects
        )

        return self.current_scene

    def apply_scene_state(self, scene, scene_state: SceneState):
        """Apply a scene state to a running scene"""
        # Clear existing objects
        scene.physics_world.physics_objects.clear()
        scene.objects.clear()
        scene.graphics.clear()

        # Create objects from scene state
        for obj_data in scene_state.objects:
            position = glm.vec3(*obj_data["position"])
            rotation = glm.vec3(*obj_data["rotation"])
            scale = glm.vec3(*obj_data["scale"])

            # Create the 3D object
            if obj_data["type"] == "cube":
                from .cube import Cube
                obj = Cube(position, rotation, scale, name=obj_data["name"])
            else:
                # Default to cube for unknown types
                from .cube import Cube
                obj = Cube(position, rotation, scale, name=obj_data["name"])

            # Create physics properties
            physics_data = obj_data["physics"]
            physics_props = PhysicsProperties(
                mass=physics_data["mass"],
                gravity_enabled=physics_data["gravity_enabled"],
                collision_enabled=physics_data["collision_enabled"],
                bounciness=physics_data["bounciness"],
                friction=physics_data["friction"],
                angular_friction=physics_data.get("angular_friction", 0.1),
                is_domino=physics_data.get("is_domino", False)
            )

            # Add to scene with physics
            scene.add_physics_object(obj, physics_props)

    def list_scenes(self) -> List[str]:
        """List all available scene files"""
        if not os.path.exists(self.scenes_dir):
            return []

        scene_files = []
        for filename in os.listdir(self.scenes_dir):
            if filename.endswith('.json'):
                scene_files.append(filename)

        return sorted(scene_files)

    def get_scene_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """Get information about a scene file without loading it"""
        filepath = os.path.join(self.scenes_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            metadata = data.get("metadata", {})
            objects_count = len(data.get("objects", []))

            return {
                "filename": filename,
                "name": metadata.get("scene_name", "Unknown"),
                "description": metadata.get("description", ""),
                "objects_count": objects_count,
                "version": metadata.get("version", "Unknown")
            }

        except Exception as e:
            print(f"Error reading scene info: {e}")
            return None

    def delete_scene(self, filename: str) -> bool:
        """Delete a scene file"""
        filepath = os.path.join(self.scenes_dir, filename)
        try:
            os.remove(filepath)
            print(f"Scene deleted: {filename}")
            return True
        except Exception as e:
            print(f"Error deleting scene: {e}")
            return False
