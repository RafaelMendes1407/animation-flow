"""
Menus: "Substituir Shape" no clique direito do Pose Mode e
"Adicionar Parte" na composição de animações.
"""

import bpy

from ..utils import nla
from ..utils import shapes


class ANIMFLOW_MT_shapes(bpy.types.Menu):
    """Shape library for the selected bones"""

    bl_idname = "ANIMFLOW_MT_shapes"
    bl_label = "Replace Shape"

    def draw(self, context):
        layout = self.layout
        escala = context.scene.animflow.shape_scale
        for ident, nome, icone, _desc in shapes.SHAPES:
            op = layout.operator("animflow.shape_replace", text=nome, icon=icone)
            op.shape = ident
            op.scale = escala
        layout.separator()
        layout.operator("animflow.shape_copy_to_selected", icon='COPYDOWN')
        layout.operator("animflow.shape_clear", icon='X')


class ANIMFLOW_MT_add_part(bpy.types.Menu):
    """Choose the part to place on the active layer"""

    bl_idname = "ANIMFLOW_MT_add_part"
    bl_label = "Add Part"

    def draw(self, context):
        layout = self.layout
        parts = context.scene.animflow.parts
        if not len(parts):
            layout.label(text="No parts in the library", icon='INFO')
            return
        for i, part in enumerate(parts):
            if part.action is None:
                continue
            inicio, fim = nla.part_range(part.action)
            op = layout.operator("animflow.strip_add", text=f"{part.name}   ({fim - inicio:.0f})",
                                 icon='ACTION', translate=False)
            op.part_index = i


def draw_pose_context(self, _context):
    layout = self.layout
    layout.separator()
    layout.menu("ANIMFLOW_MT_shapes", icon='MOD_ARMATURE')


classes = (
    ANIMFLOW_MT_shapes,
    ANIMFLOW_MT_add_part,
)


def register():
    bpy.types.VIEW3D_MT_pose_context_menu.append(draw_pose_context)


def unregister():
    bpy.types.VIEW3D_MT_pose_context_menu.remove(draw_pose_context)
