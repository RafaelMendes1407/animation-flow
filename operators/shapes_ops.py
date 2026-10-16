"""
Operadores de substituição de shapes (custom shapes) dos bones.

Só alteram ``pose_bone.custom_shape`` e propriedades de exibição do shape.
Transformações, constraints, hierarquia e pesos do bone não são tocados.
"""

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty

from ..i18n import iface, rpt
from ..utils import shapes


def _bones_alvo(context, apenas_ativo):
    """Bones que receberão o shape, com validação e mensagem de erro."""
    ob = context.object
    if ob is None or ob.type != 'ARMATURE':
        return None, rpt("Select an armature")
    if context.mode != 'POSE':
        return None, rpt("Enter Pose Mode to change shapes")
    if apenas_ativo:
        pb = context.active_pose_bone
        bones = [pb] if pb else []
    else:
        bones = list(context.selected_pose_bones or [])
        # Se nada estiver selecionado, usa o bone ativo.
        if not bones and context.active_pose_bone:
            bones = [context.active_pose_bone]
    if not bones:
        return None, rpt("No bone selected")
    linkados = [pb for pb in bones if pb.id_data.library is not None]
    if linkados:
        return None, rpt("Bones of a linked armature cannot be changed")
    return bones, None


class ANIMFLOW_OT_shape_replace(bpy.types.Operator):
    """Replace the custom shape of the selected bones"""

    bl_idname = "animflow.shape_replace"
    bl_label = "Replace Shape"
    bl_options = {'REGISTER', 'UNDO'}

    shape: EnumProperty(name="Shape", items=shapes.SHAPE_ITEMS)
    scale: FloatProperty(
        name="Scale", default=1.0, min=0.01, soft_max=10.0,
        description="Shape scale (multiplied by the bone length)",
    )
    only_active: BoolProperty(
        name="Only Active Bone", default=False,
        description="Apply only to the active bone instead of every selected bone",
    )
    show_wire: BoolProperty(
        name="Display as Wireframe", default=True,
        description="Always draw the bone as wireframe (recommended for line shapes)",
    )

    @classmethod
    def poll(cls, context):
        return context.mode == 'POSE'

    def execute(self, context):
        bones, erro = _bones_alvo(context, self.only_active)
        if erro:
            self.report({'ERROR'}, erro)
            return {'CANCELLED'}

        widget = shapes.get_widget(context.scene, self.shape)
        for pb in bones:
            pb.custom_shape = widget
            pb.custom_shape_scale_xyz = (self.scale,) * 3
            pb.use_custom_shape_bone_size = True
            pb.bone.show_wire = self.show_wire

        # Guarda a última escolha para o painel lateral.
        context.scene.animflow.shape_type = self.shape
        context.scene.animflow.shape_scale = self.scale

        nome = iface(shapes.SHAPE_NOMES[self.shape])
        self.report({'INFO'}, rpt("Shape '{}' applied to {} bone(s)").format(nome, len(bones)))
        return {'FINISHED'}


class ANIMFLOW_OT_shape_clear(bpy.types.Operator):
    """Remove the custom shape of the selected bones (back to the default drawing)"""

    bl_idname = "animflow.shape_clear"
    bl_label = "Remove Shape"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'POSE'

    def execute(self, context):
        bones, erro = _bones_alvo(context, False)
        if erro:
            self.report({'ERROR'}, erro)
            return {'CANCELLED'}
        for pb in bones:
            pb.custom_shape = None
        self.report({'INFO'}, rpt("Shape removed from {} bone(s)").format(len(bones)))
        return {'FINISHED'}


class ANIMFLOW_OT_shape_scale(bpy.types.Operator):
    """Adjust the shape scale of the selected bones without changing the shape"""

    bl_idname = "animflow.shape_scale"
    bl_label = "Shape Scale"
    bl_options = {'REGISTER', 'UNDO'}

    scale: FloatProperty(name="Scale", default=1.0, min=0.01, soft_max=10.0)

    @classmethod
    def poll(cls, context):
        return context.mode == 'POSE'

    def execute(self, context):
        bones, erro = _bones_alvo(context, False)
        if erro:
            self.report({'ERROR'}, erro)
            return {'CANCELLED'}
        for pb in bones:
            pb.custom_shape_scale_xyz = (self.scale,) * 3
        return {'FINISHED'}


_GRUPOS_COPIA = (
    ('SHAPE', "Shape", "The object used as the shape"),
    ('TRANSFORM', "Size/Offset/Rotation", "Shape scale, translation and rotation"),
    ('COLOR', "Color", "Palette and custom colors"),
    ('WIRE', "Line", "Wire width, wireframe and bone size usage"),
)


def _copiar_aparencia(origem, destino, grupos):
    """Copia a aparência do shape de *origem* para *destino* (pose bones)."""
    if 'SHAPE' in grupos:
        destino.custom_shape = origem.custom_shape
        destino.custom_shape_transform = origem.custom_shape_transform
    if 'TRANSFORM' in grupos:
        destino.custom_shape_scale_xyz = origem.custom_shape_scale_xyz
        destino.custom_shape_translation = origem.custom_shape_translation
        destino.custom_shape_rotation_euler = origem.custom_shape_rotation_euler
    if 'COLOR' in grupos:
        destino.color.palette = origem.color.palette
        if origem.color.palette == 'CUSTOM':
            for campo in ("normal", "select", "active"):
                setattr(destino.color.custom, campo, getattr(origem.color.custom, campo))
    if 'WIRE' in grupos:
        destino.use_custom_shape_bone_size = origem.use_custom_shape_bone_size
        destino.bone.show_wire = origem.bone.show_wire
        if hasattr(origem, "custom_shape_wire_width"):
            destino.custom_shape_wire_width = origem.custom_shape_wire_width


class ANIMFLOW_OT_shape_copy_to_selected(bpy.types.Operator):
    """Copy the shape look of the active bone to the other selected bones"""

    bl_idname = "animflow.shape_copy_to_selected"
    bl_label = "Apply to Selected"
    bl_options = {'REGISTER', 'UNDO'}

    groups: EnumProperty(
        name="Copy", items=_GRUPOS_COPIA, options={'ENUM_FLAG'},
        default={'SHAPE', 'TRANSFORM', 'COLOR', 'WIRE'},
    )

    @classmethod
    def poll(cls, context):
        return context.mode == 'POSE' and context.active_pose_bone is not None

    def execute(self, context):
        origem = context.active_pose_bone
        bones, erro = _bones_alvo(context, False)
        if erro:
            self.report({'ERROR'}, erro)
            return {'CANCELLED'}
        alvos = [pb for pb in bones if pb != origem]
        if not alvos:
            self.report({'ERROR'}, rpt("Select other bones besides the active one"))
            return {'CANCELLED'}
        for pb in alvos:
            _copiar_aparencia(origem, pb, self.groups)
        self.report({'INFO'}, rpt("Look copied to {} bone(s)").format(len(alvos)))
        return {'FINISHED'}


class ANIMFLOW_OT_shape_reset(bpy.types.Operator):
    """Reset size, offset, rotation, line and color of the selected bones (keeps the shape)"""

    bl_idname = "animflow.shape_reset"
    bl_label = "Reset Look"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'POSE'

    def execute(self, context):
        bones, erro = _bones_alvo(context, False)
        if erro:
            self.report({'ERROR'}, erro)
            return {'CANCELLED'}
        for pb in bones:
            pb.custom_shape_scale_xyz = (1.0, 1.0, 1.0)
            pb.custom_shape_translation = (0.0, 0.0, 0.0)
            pb.custom_shape_rotation_euler = (0.0, 0.0, 0.0)
            pb.custom_shape_transform = None
            pb.use_custom_shape_bone_size = True
            pb.color.palette = 'DEFAULT'
            if hasattr(pb, "custom_shape_wire_width"):
                pb.custom_shape_wire_width = 1.0
        return {'FINISHED'}


classes = (
    ANIMFLOW_OT_shape_replace,
    ANIMFLOW_OT_shape_clear,
    ANIMFLOW_OT_shape_scale,
    ANIMFLOW_OT_shape_copy_to_selected,
    ANIMFLOW_OT_shape_reset,
)
