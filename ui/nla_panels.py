"""
Painéis da sidebar (tecla N), aba "Anim Flow".

Editor NLA — um seletor no topo separa as funções em três modos:
* **Parts**: biblioteca, gravar/parar, strips soltas, bones animados, canais.
* **Animations**: composição das partes em camadas e opções de cada strip.
* **Bake**: lista de animações a "assar" e opções.

Viewport 3D — partes (gravação rápida) e shapes (biblioteca + personalização).

Textos com valores dinâmicos usam ``iface("...{}").format(...)`` para que o
modelo seja traduzido antes de receber os valores.
"""

import bpy

from .. import handlers
from ..i18n import iface
from ..utils import bake
from ..utils import nla
from ..utils import shapes

CATEGORIA = "Anim Flow"
LIMITE_BONES = 60


def _modo(context):
    return context.scene.animflow.ui_mode


# =============================================================================
# Blocos reaproveitados

def draw_record_status(layout, context):
    """Mostra explicitamente para onde os próximos keyframes vão."""
    scene = context.scene
    ob = context.object
    for dono, alvo, ancestral in nla.ik_cycles(ob):
        aviso = layout.box().column(align=True)
        aviso.alert = True
        aviso.label(text=iface("Rig cycle: '{}' is a child of '{}'").format(alvo, ancestral), icon='ERROR')
        aviso.label(text=iface("(part of the IK chain of '{}'). The pose will 'jump'.").format(dono))
        aviso.label(text="Fix it: Edit Mode › select the target › Alt+P › Clear Parent")
    box = layout.box()

    editando, modo, nome_anim = nla.editing_info(scene)
    if editando is not None:
        part = nla.part_for_action(scene, editando)
        col = box.column(align=True)
        col.label(text=iface("Recording part: {}").format(part.name if part else editando.name), icon='REC')
        alvo, _s = nla.tweak_target(ob)
        sub = col.row()
        sub.active = False
        if alvo is None and ob is not None:
            sub.alert = True
            sub.label(text=iface("'{}' is not in this part").format(ob.name))
        elif modo == 'CONTEXT':
            sub.label(text=iface("In the context of '{}' (seeing the animation)").format(nome_anim), icon='NLA')
        else:
            sub.label(text="Isolated (solo): only this part plays", icon='SOLO_ON')
        box.operator("animflow.part_stop", icon='PAUSE')
        _draw_bones_selecionados(box)
        return

    col = box.column(align=True)
    alvo, strip = nla.tweak_target(ob)
    if alvo is not None:
        # Modo tweak aberto pelo NLA nativo numa strip de animação.
        col.label(text=iface("Editing strip '{}' (NLA tweak)").format(strip.name), icon='ACTION_TWEAK')
        box.operator("animflow.part_stop", text="Exit Tweak", icon='PAUSE')
        return

    col.alert = True
    ad = ob.animation_data if ob else None
    if ad is not None and ad.action is not None:
        col.label(text=iface("Keys go to the stray Action '{}'").format(ad.action.name), icon='ERROR')
    else:
        col.label(text="No part is being recorded", icon='ERROR')
    sub = col.row()
    sub.alert = False
    sub.active = False
    sub.label(text="Create a part or click ● on a part")
    _draw_bones_selecionados(box)


def _draw_bones_selecionados(layout):
    """Linha com os bones selecionados e em quantas partes eles têm keys."""
    selecao = handlers.HIGHLIGHT["selecao"]
    nomes = sorted(b for bones in selecao.values() for b in bones)
    if not nomes:
        return
    texto = ", ".join(nomes[:3]) + (f" +{len(nomes) - 3}" if len(nomes) > 3 else "")
    n_partes = len(handlers.HIGHLIGHT["parts"])
    row = layout.row()
    row.alert = n_partes > 0
    row.label(text=iface("{}: keys in {} part(s)").format(texto, n_partes), icon='BONE_DATA')


def draw_parts_list(layout, context, rows=6, completo=True):
    props = context.scene.animflow
    row = layout.row()
    row.template_list("ANIMFLOW_UL_parts", "", props, "parts", props, "active_part_index", rows=rows)
    col = row.column(align=True)
    col.operator("animflow.part_new", icon='ADD', text="")
    col.operator("animflow.part_remove", icon='REMOVE', text="")
    if completo:
        col.separator()
        col.operator("animflow.part_duplicate", icon='DUPLICATE', text="")
        col.separator()
        col.operator("animflow.import_existing", icon='IMPORT', text="")
    part = nla.active_part(context)
    if part is not None:
        # O duplo clique na lista adiciona uma strip solta; o nome é editado aqui.
        layout.prop(part, "name", text="", icon='ACTION')
    sub = layout.row()
    sub.active = False
    sub.label(text="Double-click a part: add it as a loose strip", icon='MOUSE_LMB_2X')


def draw_loose(layout, context):
    """Strips soltas: partes no NLA fora das animações, tocando juntas."""
    scene = context.scene
    props = scene.animflow
    soltas = nla.loose_strips(scene)
    box = layout.box()
    row = box.row(align=True)
    row.label(text=iface("Loose Strips ({})").format(len(soltas)), icon='NLA_PUSHDOWN')
    sub = row.row(align=True)
    sub.enabled = bool(soltas)
    sub.operator("animflow.loose_play", text="", icon='PLAY', depress=props.loose_playing)
    sub.operator("animflow.loose_clear", text="", icon='TRASH')
    if not soltas:
        nota = box.row()
        nota.active = False
        nota.label(text="Double-click a part to add one here")
        return
    col = box.column(align=True)
    for ob, track, s in soltas[:20]:
        linha = col.row(align=True)
        linha.alert = s.action is not None and s.action.name in handlers.HIGHLIGHT["parts"]
        linha.label(text=f"{s.name}   {s.frame_start:.0f}–{s.frame_end:.0f}", translate=False,
                    icon='MUTE_IPO_ON' if s.mute else 'ACTION')
        op = linha.operator("animflow.loose_remove", text="", icon='X', emboss=False)
        op.object_name = ob.name
        op.track_name = track.name
        op.strip_name = s.name
    if len(soltas) > 20:
        col.label(text=iface("... and {} more").format(len(soltas) - 20))
    box.prop(props, "default_blend")


# =============================================================================
# NLA: cabeçalho com o seletor de modo

class ANIMFLOW_PT_nla_main(bpy.types.Panel):
    bl_space_type = 'NLA_EDITOR'
    bl_region_type = 'UI'
    bl_category = CATEGORIA
    bl_label = "Anim Flow"
    bl_options = {'HIDE_HEADER'}
    bl_order = 0

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.scale_y = 1.3
        row.prop(context.scene.animflow, "ui_mode", expand=True)
        draw_record_status(layout, context)
        layout.operator("animflow.diagnose", icon='INFO')


# =============================================================================
# NLA: modo Partes

class ANIMFLOW_PT_nla_parts(bpy.types.Panel):
    bl_space_type = 'NLA_EDITOR'
    bl_region_type = 'UI'
    bl_category = CATEGORIA
    bl_label = "Parts"
    bl_order = 1

    @classmethod
    def poll(cls, context):
        return _modo(context) == 'PARTS'

    def draw(self, context):
        layout = self.layout
        draw_parts_list(layout, context)
        part = nla.active_part(context)
        if part is None or part.action is None:
            layout.label(text="Create a part with +", icon='INFO')
            draw_loose(layout, context)
            return
        gravando = nla.editing_part(context.scene) == part.action
        row = layout.row(align=True)
        row.scale_y = 1.2
        if gravando:
            row.operator("animflow.part_stop", icon='PAUSE', text="Stop")
        else:
            row.operator("animflow.part_record", icon='REC', text="Record").index = -1
        row.operator("animflow.loose_add", icon='NLA_PUSHDOWN', text="Loose").part_index = -1
        row.operator("animflow.part_set_range", icon='PREVIEW_RANGE', text="Range")
        layout.prop(context.scene.animflow, "record_in_context")
        usos = nla.part_usage(context.scene, part.action)
        sub = layout.row()
        sub.active = False
        sub.label(text=iface("Used in {} strip(s)").format(usos), icon='INFO')
        draw_loose(layout, context)


class ANIMFLOW_PT_nla_part_bones(bpy.types.Panel):
    bl_space_type = 'NLA_EDITOR'
    bl_region_type = 'UI'
    bl_category = CATEGORIA
    bl_label = "Animated Bones"
    bl_parent_id = "ANIMFLOW_PT_nla_parts"

    @classmethod
    def poll(cls, context):
        part = nla.active_part(context)
        return part is not None and part.action is not None

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.animflow
        action = nla.active_part(context).action

        row = layout.row(align=True)
        row.prop(props, "only_moved", toggle=True)
        row.prop(props, "only_selected_bones", toggle=True)

        selecao = handlers.HIGHLIGHT["selecao"]
        algum = False
        for ob in nla.part_targets(scene, action, context.selected_objects):
            if ob.type != 'ARMATURE':
                continue
            bones = nla.animated_bones(action, nla.part_slot_for(action, ob), props.only_moved)
            sel_ob = selecao.get(ob.name, set())
            if props.only_selected_bones:
                bones = {b: c for b, c in bones.items() if b in sel_ob}
            if not bones:
                continue
            algum = True

            col = layout.column(align=True)
            col.label(text=iface("{} ({} bones)").format(ob.name, len(bones)), icon='OUTLINER_OB_ARMATURE')
            for i, (bone, cats) in enumerate(bones.items()):
                if i >= LIMITE_BONES:
                    col.label(text=iface("... and {} more").format(len(bones) - LIMITE_BONES))
                    break
                selecionado = bone in sel_ob
                linha = col.row(align=True)
                linha.alert = selecionado
                op = linha.operator("animflow.select_bone", text=bone, emboss=False, translate=False,
                                    icon='RADIOBUT_ON' if selecionado else 'BONE_DATA')
                op.object_name = ob.name
                op.bone_name = bone
                resumo = linha.row()
                resumo.alignment = 'RIGHT'
                resumo.active = False
                resumo.label(text=" · ".join(iface(c) for c in sorted(cats)), translate=False)

        if not algum:
            layout.label(text="No bone with keys in this part", icon='INFO')

        layout.separator()
        layout.label(text="Channels of the selected bones:")
        row = layout.row(align=True)
        row.operator("animflow.channels_copy", icon='COPYDOWN', text="Copy")
        row.operator("animflow.channels_paste", icon='PASTEDOWN', text="Paste")
        row = layout.row(align=True)
        row.operator("animflow.channels_transfer", icon='FORWARD', text="Send to…")
        row.operator("animflow.channels_delete", icon='TRASH', text="Delete")


# =============================================================================
# NLA: modo Animações

class ANIMFLOW_PT_nla_anims(bpy.types.Panel):
    bl_space_type = 'NLA_EDITOR'
    bl_region_type = 'UI'
    bl_category = CATEGORIA
    bl_label = "Animations"
    bl_order = 1

    @classmethod
    def poll(cls, context):
        return _modo(context) == 'ANIMS'

    def draw(self, context):
        layout = self.layout
        props = context.scene.animflow
        row = layout.row()
        row.template_list("ANIMFLOW_UL_animations", "", props, "animations", props,
                          "active_anim_index", rows=5)
        col = row.column(align=True)
        col.operator("animflow.anim_new", icon='ADD', text="")
        col.operator("animflow.anim_remove", icon='REMOVE', text="")
        col.separator()
        col.operator("animflow.anim_duplicate", icon='DUPLICATE', text="")
        col.separator()
        col.operator("animflow.import_existing", icon='IMPORT', text="")

        layout.prop(props, "auto_activate")
        layout.prop(props, "record_in_context")
        layout.prop(props, "default_blend")
        row = layout.row(align=True)
        row.prop(props, "use_pose_base")
        sub = row.row(align=True)
        sub.enabled = props.use_pose_base
        sub.operator("animflow.pose_base_update", text="", icon='FILE_REFRESH')
        if nla.active_animation(context) is not None:
            row = layout.row(align=True)
            row.operator("animflow.anim_play", icon='PLAY', text="Play").index = -1
            row.operator("animflow.anim_add_objects", icon='ADD', text="Add Objects")


class ANIMFLOW_PT_nla_composition(bpy.types.Panel):
    bl_space_type = 'NLA_EDITOR'
    bl_region_type = 'UI'
    bl_category = CATEGORIA
    bl_label = "Composition"
    bl_parent_id = "ANIMFLOW_PT_nla_anims"

    @classmethod
    def poll(cls, context):
        return nla.active_animation(context) is not None

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.animflow
        anim = nla.active_animation(context)

        # Camadas.
        layout.label(text="Layers (top to bottom):")
        row = layout.row()
        row.template_list("ANIMFLOW_UL_layers", "", anim, "layers", anim, "active_layer_index", rows=3)
        col = row.column(align=True)
        col.operator("animflow.layer_add", icon='ADD', text="")
        col.operator("animflow.layer_remove", icon='REMOVE', text="")
        col.separator()
        col.operator("animflow.layer_move", icon='TRIA_UP', text="").direction = 'UP'
        col.operator("animflow.layer_move", icon='TRIA_DOWN', text="").direction = 'DOWN'

        idx = anim.active_layer_index
        if not (0 <= idx < len(anim.layers)):
            return
        layer = anim.layers[idx]

        # Partes da camada ativa, em ordem de tempo.
        box = layout.box()
        box.label(text=iface("Parts in '{}':").format(layer.name), icon='SEQUENCE')
        _ob_ref, track = nla.reference_object(context, anim, idx)
        edit = props.strip_edit
        if track is None or not len(track.strips):
            sub = box.row()
            sub.active = False
            sub.label(text="No parts. Add one below.")
        else:
            col = box.column(align=True)
            for n, s in enumerate(nla.sorted_strips(track), start=1):
                nome = s.action.name if s.action else s.name
                sel = (edit.anim_name == anim.name and edit.layer_name == layer.name
                       and edit.action_name == nome and abs(edit.start - s.frame_start) < 0.5)
                extra = f"  ×{s.repeat:g}" if abs(s.repeat - 1.0) > 1e-4 else ""
                texto = f"{n}. {nome}   {s.frame_start:.0f}–{s.frame_end:.0f}{extra}"
                linha = col.row(align=True)
                # Partes com keys dos bones selecionados ficam em vermelho.
                destacada = nome in handlers.HIGHLIGHT["parts"]
                linha.alert = destacada
                icone = 'MUTE_IPO_ON' if s.mute else ('KEYFRAME_HLT' if destacada else 'ACTION')
                op = linha.operator("animflow.strip_select", text=texto, depress=sel, icon=icone,
                                    translate=False)
                op.layer_index = idx
                op.action_name = nome
                op.start = s.frame_start

            row = box.row(align=True)
            row.operator("animflow.strip_move", icon='TRIA_LEFT', text="").direction = 'LEFT'
            row.operator("animflow.strip_move", icon='TRIA_RIGHT', text="").direction = 'RIGHT'
            row.operator("animflow.strip_duplicate", icon='DUPLICATE', text="")
            row.operator("animflow.strip_remove", icon='X', text="")
            row.separator()
            row.operator("animflow.layer_pack", icon='ALIGN_JUSTIFY', text="Pack")

        layout.label(text="Insert part:")
        row = layout.row(align=True)
        row.prop(props, "place_mode", expand=True)
        row = layout.row()
        row.scale_y = 1.2
        row.menu("ANIMFLOW_MT_add_part", icon='ADD')


class ANIMFLOW_PT_nla_strip(bpy.types.Panel):
    bl_space_type = 'NLA_EDITOR'
    bl_region_type = 'UI'
    bl_category = CATEGORIA
    bl_label = "Part Options"
    bl_parent_id = "ANIMFLOW_PT_nla_anims"

    @classmethod
    def poll(cls, context):
        anim = nla.active_animation(context)
        edit = context.scene.animflow.strip_edit
        return anim is not None and edit.anim_name == anim.name and bool(edit.action_name)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        scene = context.scene
        edit = scene.animflow.strip_edit
        anim_sel, idx_sel, strips = nla.selected_placement(scene)
        if not strips:
            layout.label(text="Part not found (changed in the NLA?)", icon='ERROR')
            return
        base_segura = anim_sel.layers[idx_sel].hold
        s = strips[0][2]

        layout.label(text=iface("{}  ({} object(s))").format(edit.action_name, len(strips)), icon='ACTION')
        col = layout.column(align=True)
        col.prop(edit, "frame_start")
        sub = col.row()
        sub.enabled = False
        sub.label(text=iface("End: {:.1f}   ·   length {:.1f}").format(s.frame_end, s.frame_end - s.frame_start))

        col = layout.column(align=True)
        col.prop(edit, "repeat")
        col.prop(edit, "scale")
        col.prop(edit, "use_reverse")

        col = layout.column(align=True)
        col.prop(edit, "blend_type")
        sub = col.row()
        sub.enabled = not base_segura
        sub.prop(edit, "extrapolation")
        if base_segura:
            nota = col.row()
            nota.active = False
            nota.label(text="Layer with 'Hold Pose' (pin in the layer list)", icon='INFO')
        col = layout.column(align=True)
        col.prop(edit, "use_auto_blend")
        sub = col.column(align=True)
        sub.enabled = not edit.use_auto_blend
        sub.prop(edit, "blend_in")
        sub.prop(edit, "blend_out")


# =============================================================================
# NLA: modo Bake

class ANIMFLOW_PT_nla_bake(bpy.types.Panel):
    bl_space_type = 'NLA_EDITOR'
    bl_region_type = 'UI'
    bl_category = CATEGORIA
    bl_label = "Bake"
    bl_order = 1

    @classmethod
    def poll(cls, context):
        return _modo(context) == 'BAKE'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.animflow

        row = layout.row()
        row.label(text="Animations to bake:")
        row.operator("animflow.bake_toggle_all", text="", icon='CHECKBOX_HLT')
        layout.template_list("ANIMFLOW_UL_bake_anims", "", props, "animations", props,
                             "active_anim_index", rows=5)

        col = layout.column(align=True)
        col.prop(props, "bake_step")
        col.prop(props, "bake_visual")
        if props.bake_visual:
            sub = col.row()
            sub.active = False
            sub.label(text="Inside Blender, the constraints act again on top", icon='ERROR')
        col.prop(props, "bake_clean")
        col.prop(props, "bake_all_bones")

        # Detalhes da animação selecionada: o que vai entrar no bake.
        anim = nla.active_animation(context)
        if anim is not None:
            box = layout.box()
            faixa = nla.animation_range(scene, anim)
            if faixa:
                texto = iface("{}: frames {:.0f}–{:.0f}").format(anim.name, faixa[0], faixa[1])
            else:
                texto = iface("{}: empty").format(anim.name)
            box.label(text=texto, icon='INFO')
            for ob, dados in bake.animation_summary(scene, anim, props.bake_all_bones).items():
                partes = []
                if dados["bones"]:
                    partes.append(iface("{} bones").format(len(dados["bones"])))
                if dados["object"]:
                    partes.append(iface("object"))
                sub = box.row()
                sub.active = False
                sub.label(text=f"{ob.name}: {', '.join(partes) or iface('nothing')}", translate=False,
                          icon='OUTLINER_OB_ARMATURE' if ob.type == 'ARMATURE' else 'OBJECT_DATA')

        n = sum(1 for a in props.animations if a.bake_include)
        row = layout.row()
        row.scale_y = 1.5
        row.operator("animflow.bake", icon='RENDER_ANIMATION', text=iface("Bake ({} animation(s))").format(n))
        sub = layout.row()
        sub.active = False
        sub.label(text="Result: new Part + '[bake]' Animation")


# =============================================================================
# Viewport 3D

class ANIMFLOW_PT_view3d_parts(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORIA
    bl_label = "Parts"

    def draw(self, context):
        layout = self.layout
        draw_record_status(layout, context)
        draw_parts_list(layout, context, rows=4, completo=False)


class ANIMFLOW_PT_view3d_shapes(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORIA
    bl_label = "Bone Shapes"

    @classmethod
    def poll(cls, context):
        return context.mode == 'POSE'

    def draw(self, context):
        layout = self.layout
        props = context.scene.animflow
        n = len(context.selected_pose_bones or [])
        layout.label(text=iface("{} bone(s) selected").format(n), icon='BONE_DATA')
        layout.prop(props, "shape_scale")
        grid = layout.grid_flow(columns=2, even_columns=True, align=True)
        for ident, nome, icone, _desc in shapes.SHAPES:
            op = grid.operator("animflow.shape_replace", text=nome, icon=icone)
            op.shape = ident
            op.scale = props.shape_scale
        layout.operator("animflow.shape_clear", icon='X', text="Remove Shape")


class ANIMFLOW_PT_view3d_shape_custom(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORIA
    bl_label = "Customize Shape"
    bl_parent_id = "ANIMFLOW_PT_view3d_shapes"

    @classmethod
    def poll(cls, context):
        return context.mode == 'POSE'

    def draw(self, context):
        layout = self.layout
        pb = context.active_pose_bone
        if pb is None:
            layout.label(text="No active bone", icon='INFO')
            return
        layout.use_property_split = True
        layout.use_property_decorate = False

        layout.label(text=iface("Active bone: {}").format(pb.name), icon='BONE_DATA')
        layout.prop(pb, "custom_shape", text="Shape")

        col = layout.column(align=True)
        col.prop(pb, "custom_shape_scale_xyz", text="Size")
        col = layout.column(align=True)
        col.prop(pb, "custom_shape_translation", text="Offset")
        col = layout.column(align=True)
        col.prop(pb, "custom_shape_rotation_euler", text="Rotation")

        col = layout.column()
        col.prop(pb, "use_custom_shape_bone_size", text="Scale to Bone Length")
        if hasattr(pb, "custom_shape_wire_width"):
            col.prop(pb, "custom_shape_wire_width", text="Wire Width")
        col.prop(pb.bone, "show_wire", text="Wireframe")
        col.prop_search(pb, "custom_shape_transform", pb.id_data.pose, "bones", text="Follow Bone")

        col = layout.column()
        col.prop(pb.color, "palette", text="Color")
        if pb.color.palette == 'CUSTOM':
            sub = col.column(align=True)
            sub.prop(pb.color.custom, "normal", text="Normal")
            sub.prop(pb.color.custom, "select", text="Selected")
            sub.prop(pb.color.custom, "active", text="Active")

        layout.use_property_split = False
        row = layout.row(align=True)
        row.operator("animflow.shape_copy_to_selected", icon='COPYDOWN')
        row.operator("animflow.shape_reset", icon='LOOP_BACK', text="Reset")


classes = (
    ANIMFLOW_PT_nla_main,
    ANIMFLOW_PT_nla_parts,
    ANIMFLOW_PT_nla_part_bones,
    ANIMFLOW_PT_nla_anims,
    ANIMFLOW_PT_nla_composition,
    ANIMFLOW_PT_nla_strip,
    ANIMFLOW_PT_nla_bake,
    ANIMFLOW_PT_view3d_parts,
    ANIMFLOW_PT_view3d_shapes,
    ANIMFLOW_PT_view3d_shape_custom,
)
