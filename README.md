# Raytracing_computacion-grafica

Proyecto de raytracing con editor 3D interactivo y panel lateral escalable.

## Características

- **Editor 3D Interactivo**: Manipulación de objetos en tiempo real
- **Panel Lateral Escalable**: UI adaptable con controles de redimensionamiento
- **Raytracing GPU**: Renderizado acelerado por hardware
- **Controles Intuitivos**: Navegación WASD + mouse

## Panel Escalable

El panel lateral puede ser redimensionado dinámicamente:
- **Mouse**: Arrastrar el borde izquierdo del panel
- **Teclado**: Flechas ← → para ajustar el ancho
- **Límites**: 20% - 50% del ancho de pantalla
- **Escalado Automático**: Botones, texto e íconos se ajustan proporcionalmente

## Escalado de UI Responsivo

La interfaz de usuario se escala automáticamente según el tamaño de la ventana:
- **Ventana Grande**: UI más compacta para aprovechar el espacio de la escena 3D
- **Ventana Pequeña**: UI más grande para mantener usabilidad
- **Proporcional**: Mantiene las proporciones óptimas en cualquier resolución
- **Límites Inteligentes**: Evita UI demasiado pequeña o demasiado grande

### Comportamiento de Escalado
- **800x600** (compacto): UI tamaño normal (escala 1.0x)
- **1400x900** (recomendado): UI 38% más compacta (escala 0.62x)
- **1920x1080** (Full HD): UI 52% más compacta (escala 0.48x)
- **2560x1440** (QHD): UI 60% más compacta (escala 0.40x)

## Instalación

1. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Ejecutar la aplicación**:
   ```bash
   python -m src.main
   ```

   La aplicación se abrirá en una ventana de **1400x900 píxeles** para proporcionar una experiencia óptima con más espacio de trabajo.

   **Tamaño de ventana personalizado** (opcional):
   ```bash
   python -m src.main 1920 1080  # Para pantalla completa
   python -m src.main 800 600    # Para tamaño compacto
   ```

## Controles

### Navegación 3D
- **WASD**: Movimiento de cámara
- **Mouse derecho**: Rotación de cámara
- **Q/E**: Subir/bajar

### Manipulación de Objetos
- **C**: Ciclar selección de objetos
- **R**: Modo rotación (WASD para rotar)
- **T**: Modo escala (WASD para escalar)
- **DELETE**: Eliminar objeto seleccionado
- **ENTER**: Confirmar eliminación

### Panel UI
- **Mouse drag**: Redimensionar panel lateral
- **← →**: Ajustar ancho del panel
- **Click**: Seleccionar herramientas

### Creación de Objetos
- **1**: Agregar cubo en posición de cámara
- **2**: Agregar esfera en posición de cámara
- **Click + Shift**: Agregar cubo en posición del mouse

## Dependencias

- `pyglet`: Framework de ventanas y OpenGL
- `moderngl`: Contexto OpenGL moderno
- `PyGLM`: Operaciones matemáticas vectoriales
- `numpy`: Computación numérica

## Estructura del Proyecto

```
src/
├── main.py              # Punto de entrada
├── window.py            # Ventana principal y controles
├── ui_overlay.py        # Panel lateral escalable
├── scene.py             # Gestión de escena 3D
├── camera.py            # Cámara y proyección
├── raytracer.py         # Motor de raytracing
├── material.py          # Materiales y shaders
└── [otros módulos...]

shaders/                 # Shaders GLSL
├── basic.vert/frag      # Shader básico
├── sprite.vert/frag     # Shader para sprites
└── raytracer.comp       # Compute shader raytracing
```
