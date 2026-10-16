"""
PropertyGroups do Anim Flow.

Tudo fica em ``scene.animflow`` e é salvo junto com o .blend.

Modelo
------
* **Parte** (``parts``): um trecho gravado. É uma Action em camadas (um slot
  por objeto), guardada com Fake User numa biblioteca. Não aparece no NLA,
  exceto enquanto está sendo gravada (track temporária "✎ ...").
* **Animação** (``animations``): a animação completa, composta por partes.
  Cada camada vira uma track NLA chamada "<Animação> › <Camada>" em cada
  objeto; cada parte colocada vira uma strip nessa track.
"""

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)

from .utils import nla
from .utils import shapes


# -----------------------------------------------------------------------------
# Callbacks de atualização

def _on_part_rename(self, _context):
    """Renomear a parte renomeia a Action."""
    if self.action is not None and self.action.name != self.name:
        self.action.name = self.name


def _on_anim_rename(self, context):
    """Renomear a animação renomeia as tracks de todas as camadas."""
    antigo = self.track_prefix
    if not antigo or antigo == self.name:
        self.track_prefix = self.name
        return
    nla.rename_animation_tracks(context.scene, self, antigo, self.name)
    self.track_prefix = self.name


def _on_layer_rename(self, context):
    """Renomear a camada renomeia a track correspondente."""
    anim = nla.animation_of_layer(context.scene, self)
    antigo = self.track_name
    if anim is not None and antigo and antigo != self.name:
        nla.rename_layer_tracks(context.scene, anim, antigo, self.name)
    self.track_name = self.name


def _on_layer_mute(self, context):
    anim = nla.animation_of_layer(context.scene, self)
    if anim is not None:
        nla.apply_layer_mutes(context.scene, anim)


def _on_layer_hold(self, context):
    anim = nla.animation_of_layer(context.scene, self)
    if anim is not None:
        nla.apply_holds(context.scene, anim, desligar=self)


def _on_active_anim(self, context):
    """Selecionar uma animação na lista a torna a animação em reprodução."""
    if self.auto_activate and 0 <= self.active_anim_index < len(self.animations):
        nla.activate_animation(context.scene, self.animations[self.active_anim_index])


def _on_strip_edit(self, context):
    """Aplica as opções editadas em todas as strips da colocação selecionada."""
    if self.loading:
        return
    nla.apply_strip_edit(context.scene, self)


# -----------------------------------------------------------------------------
# Itens de enum compartilhados

EXTRAPOLATION_ITEMS = (
    ('NOTHING', "Nothing", "Outside the strip the part has no effect"),
    ('HOLD_FORWARD', "Hold Forward", "Hold the last pose until the next strip"),
    ('HOLD', "Hold", "Hold the first and last pose (first strip only)"),
)

BLEND_ITEMS = (
    ('REPLACE', "Replace", "Replace the result of the layers below"),
    ('COMBINE', "Combine", "Combine with the layers below (good for layering)"),
    ('ADD', "Add", "Add to the layers below"),
    ('SUBTRACT', "Subtract", "Subtract from the layers below"),
    ('MULTIPLY', "Multiply", "Multiply with the layers below"),
)


# -----------------------------------------------------------------------------
# Classes

class ANIMFLOW_PG_part(bpy.types.PropertyGroup):
    """Parte: trecho gravado, reaproveitável em várias animações."""

    name: StringProperty(name="Name", update=_on_part_rename)
    action: PointerProperty(name="Action", type=bpy.types.Action)


class ANIMFLOW_PG_layer(bpy.types.PropertyGroup):
    """Camada de uma animação (= uma track NLA por objeto)."""

    name: StringProperty(name="Name", update=_on_layer_rename)
    track_name: StringProperty(options={'HIDDEN'})
    mute: BoolProperty(name="Mute", description="Mute this layer", update=_on_layer_mute)
    hold: BoolProperty(
        name="Hold Pose",
        description=(
            "Each part holds its last pose until the next one (and, on the base layer, the first "
            "part holds its pose before it starts). Turn off on overlay layers that should "
            "release back to the layer below when the part ends"
        ),
        default=True,
        update=_on_layer_hold,
    )


class ANIMFLOW_PG_animation(bpy.types.PropertyGroup):
    """Animação completa composta por partes em camadas."""

    name: StringProperty(name="Name", update=_on_anim_rename)
    track_prefix: StringProperty(options={'HIDDEN'})
    layers: CollectionProperty(type=ANIMFLOW_PG_layer)
    active_layer_index: IntProperty(name="Active Layer")
    bake_include: BoolProperty(name="Include in Bake", default=True)

    # Campo da versão 1.0 (animação = uma Action). Usado só na migração.
    action: PointerProperty(type=bpy.types.Action, options={'HIDDEN'})


class ANIMFLOW_PG_strip_edit(bpy.types.PropertyGroup):
    """
    Opções da parte (strip) selecionada na composição.

    Funciona como um "proxy": ao editar aqui, o valor é aplicado à strip
    correspondente em todos os objetos da animação.
    """

    # Identificação da colocação selecionada.
    anim_name: StringProperty(options={'HIDDEN'})
    layer_name: StringProperty(options={'HIDDEN'})
    action_name: StringProperty(options={'HIDDEN'})
    start: FloatProperty(options={'HIDDEN'})
    loading: BoolProperty(options={'HIDDEN'})

    frame_start: FloatProperty(name="Start", update=_on_strip_edit,
                               description="Frame where the part starts")
    repeat: FloatProperty(name="Repeat", default=1.0, min=0.1, soft_max=100.0, update=_on_strip_edit,
                          description="How many times the part repeats")
    scale: FloatProperty(name="Speed (Scale)", default=1.0, min=0.0001, soft_max=10.0,
                         update=_on_strip_edit,
                         description="Time scale: 2 = half speed, 0.5 = double speed")
    use_reverse: BoolProperty(name="Reverse", update=_on_strip_edit,
                              description="Play the part backwards")
    blend_in: FloatProperty(name="Blend In", min=0.0, update=_on_strip_edit,
                            description="Transition frames at the start")
    blend_out: FloatProperty(name="Blend Out", min=0.0, update=_on_strip_edit,
                             description="Transition frames at the end")
    use_auto_blend: BoolProperty(name="Auto Blend", update=_on_strip_edit,
                                 description="Compute blend in/out from the overlap with neighbor strips")
    extrapolation: EnumProperty(
        name="Before/After",
        items=EXTRAPOLATION_ITEMS,
        default='NOTHING',
        update=_on_strip_edit,
    )
    blend_type: EnumProperty(
        name="Blending",
        items=BLEND_ITEMS,
        default='COMBINE',
        update=_on_strip_edit,
    )


class ANIMFLOW_PG_settings(bpy.types.PropertyGroup):
    ui_mode: EnumProperty(
        name="Mode",
        items=(
            ('PARTS', "Parts", "Record and edit parts", 'ACTION', 0),
            ('ANIMS', "Animations", "Compose animations from parts", 'NLA', 1),
            ('BAKE', "Bake", "Bake animations", 'RENDER_ANIMATION', 2),
        ),
        default='PARTS',
    )

    parts: CollectionProperty(type=ANIMFLOW_PG_part)
    active_part_index: IntProperty(name="Active Part")

    animations: CollectionProperty(type=ANIMFLOW_PG_animation)
    active_anim_index: IntProperty(name="Active Animation", update=_on_active_anim)
    auto_activate: BoolProperty(
        name="Play on Select",
        description="Clicking an animation mutes the others so only it plays",
        default=True,
    )
    place_mode: EnumProperty(
        name="Insert",
        items=(
            ('AFTER', "After", "Right after the last part of the active layer"),
            ('START', "Start", "At the start of the animation (e.g. frame 1), together with the others"),
            ('WITH', "Together", "Starting together with the selected part"),
            ('CURRENT', "Current Frame", "At the current frame"),
        ),
        default='AFTER',
        description=(
            "Where to place the part. If the layer is occupied at that frame, the part goes "
            "to a layer above (created automatically if needed)"
        ),
    )
    use_pose_base: BoolProperty(
        name="Base Pose (Rest)",
        description=(
            "Keep a track at the bottom of the NLA that returns to rest the channels the active "
            "animation doesn't animate. Prevents bones stuck in another animation's pose"
        ),
        default=True,
    )
    record_in_context: BoolProperty(
        name="Record in Animation Context",
        description=(
            "When recording a part used in the active animation, record directly on its strip "
            "while seeing the whole animation. Off: the part is recorded isolated (solo)"
        ),
        default=True,
    )
    strip_edit: PointerProperty(type=ANIMFLOW_PG_strip_edit)
    default_blend: EnumProperty(
        name="Default Blending",
        description="Blending of newly placed parts (in animations and as loose strips)",
        items=BLEND_ITEMS,
        default='COMBINE',
    )
    loose_playing: BoolProperty(
        name="Loose Strips Playing",
        description="Loose strips are playing (animations muted)",
        default=False,
    )

    # --- Exibição -----------------------------------------------------------
    only_moved: BoolProperty(name="Only Moving", default=True,
                             description="Hide bones whose keys never change value")
    only_selected_bones: BoolProperty(name="Only Selected", default=False,
                                      description="List only the bones selected in Pose Mode")

    # --- Shapes -------------------------------------------------------------
    shape_type: EnumProperty(name="Shape", items=shapes.SHAPE_ITEMS, default='CIRCLE')
    shape_scale: FloatProperty(name="Scale", default=1.0, min=0.01, soft_max=10.0,
                               description="Shape scale (relative to the bone length)")

    # --- Bake ---------------------------------------------------------------
    bake_step: IntProperty(name="Step", default=1, min=1, max=120,
                           description="Frames between generated keys")
    bake_visual: BoolProperty(
        name="Visual Keying (for Export)", default=False,
        description=(
            "Record the final pose (with IK, constraints, drivers), useful to export to game engines. "
            "Inside Blender the constraints stay active and act again on top. "
            "Off (default): records the channels and the rig recomputes, identical result in Blender"
        ),
    )
    bake_clean: BoolProperty(name="Clean Redundant Keys", default=True,
                             description="Remove keys that don't change the curve")
    bake_all_bones: BoolProperty(
        name="All Bones", default=False,
        description="Include every bone; off: only bones with keys in the parts or moved by the rig",
    )


classes = (
    ANIMFLOW_PG_part,
    ANIMFLOW_PG_layer,
    ANIMFLOW_PG_animation,
    ANIMFLOW_PG_strip_edit,
    ANIMFLOW_PG_settings,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.animflow = PointerProperty(type=ANIMFLOW_PG_settings)


def unregister():
    del bpy.types.Scene.animflow
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
