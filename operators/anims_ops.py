"""
Operadores de Animações (composição de partes em camadas) e das strips
que formam cada camada.
"""

import bpy
from bpy.props import EnumProperty, IntProperty, StringProperty, BoolProperty, FloatProperty

from ..i18n import iface, rpt
from ..utils import compat
from ..utils import nla
from ..utils.nla import AnimFlowError
from .parts_ops import AnimOperator, objetos_alvo


def _anim_ativa(context):
    anim = nla.active_animation(context)
    if anim is None:
        raise AnimFlowError(rpt("No active animation"))
    return anim


def _camada_ativa(context):
    anim = _anim_ativa(context)
    idx = anim.active_layer_index
    if not (0 <= idx < len(anim.layers)):
        raise AnimFlowError(rpt("'{}' has no layer selected").format(anim.name))
    return anim, idx


def _selecionar(scene, anim, idx, strip):
    nla.load_strip_edit(scene.animflow.strip_edit, anim, anim.layers[idx], strip)


def _nova_animacao(scene, nome):
    """Cria a animação (com camada 'Base') no topo da lista. Retorna o nome final."""
    props = scene.animflow
    nome = nla.unique_name(nome, {a.name for a in props.animations})
    anim = props.animations.add()
    anim.name = nome
    anim.track_prefix = nome
    layer = anim.layers.add()
    layer.name = layer.track_name = "Base"
    props.animations.move(len(props.animations) - 1, 0)
    # Muda o índice sem disparar a ativação automática (é feita pelo chamador).
    auto = props.auto_activate
    props.auto_activate = False
    props.active_anim_index = 0
    props.auto_activate = auto
    return nome


# =============================================================================
# Animações

# Enum dinâmico das partes (o Blender exige manter as strings referenciadas).
_cache_partes = []


def _itens_partes(_self, context):
    parts = context.scene.animflow.parts
    _cache_partes[:] = [
        (str(i), p.name, p.name, 'ACTION', 1 << i)
        for i, p in enumerate(parts) if i < 32 and p.action is not None
    ]
    return _cache_partes


class ANIMFLOW_OT_anim_new(AnimOperator, bpy.types.Operator):
    """Create a full animation (e.g. "Jump") from one or more parts"""

    bl_idname = "animflow.anim_new"
    bl_label = "New Animation"
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(name="Name", default="Animation")
    parts: EnumProperty(name="Parts", items=_itens_partes, options={'ENUM_FLAG'},
                        description="Parts that go into the animation")
    arrange: EnumProperty(
        name="Arrange",
        items=(
            ('SEQUENCE', "In Sequence", "One after the other on the same layer"),
            ('TOGETHER', "Together", "All starting at the same frame, each on its own layer"),
        ),
        default='SEQUENCE',
    )

    def invoke(self, context, _event):
        # Começa com a parte ativa marcada.
        idx = context.scene.animflow.active_part_index
        if 0 <= idx < min(32, len(context.scene.animflow.parts)):
            self.parts = {str(idx)}
        return context.window_manager.invoke_props_dialog(self, width=360)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "name")
        if not len(context.scene.animflow.parts):
            layout.label(text="Empty library: the animation starts without parts", icon='INFO')
            return
        layout.label(text="Parts (in library order):")
        col = layout.column(align=True)
        for ident, *_resto in _itens_partes(self, context):
            col.prop_enum(self, "parts", ident)
        layout.prop(self, "arrange", expand=True)

    def run(self, context):
        scene = context.scene
        props = scene.animflow
        nome = self.name.strip()
        if not nome:
            raise AnimFlowError(rpt("Give the animation a name"))
        # Nomes (e não referências) porque a coleção pode mudar no caminho.
        escolhidas = [props.parts[int(i)].name for i in sorted(self.parts, key=int)
                      if int(i) < len(props.parts)]

        obs = objetos_alvo(context)
        for nome_parte in escolhidas:
            for ob in nla.part_targets(scene, props.parts[nome_parte].action, obs):
                if ob not in obs:
                    obs.append(ob)
        obs = [ob for ob in obs if not escolhidas
               or any(nla.part_slot_for(props.parts[p].action, ob) for p in escolhidas)]
        if not obs:
            raise AnimFlowError(rpt("Select the objects of the animation"))

        nla.stop_part_edit(scene)
        nla.ensure_pose_base(scene, obs)
        nome = _nova_animacao(scene, nome)
        anim = props.animations[nome]
        for ob in obs:
            nla.ensure_layer_track(ob, anim, 0)

        primeira = None
        for nome_parte in escolhidas:
            part = props.parts[nome_parte]
            if self.arrange == 'TOGETHER':
                frame = scene.frame_start
            else:
                frame = nla.placement_frame(context, anim, 0, 'AFTER')
            idx, strips = nla.place_part(scene, anim, 0, part, frame, obs)
            if primeira is None:
                primeira = (idx, strips[0])
        if primeira is not None:
            anim.active_layer_index = primeira[0]
            _selecionar(scene, anim, primeira[0], primeira[1])
        nla.activate_animation(scene, anim)
        self.report({'INFO'}, rpt("Animation '{}' created with {} part(s)").format(nome, len(escolhidas)))
        return {'FINISHED'}


class ANIMFLOW_OT_anim_remove(AnimOperator, bpy.types.Operator):
    """Remove the active animation (the parts stay in the library)"""

    bl_idname = "animflow.anim_remove"
    bl_label = "Remove Animation"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def run(self, context):
        scene = context.scene
        props = scene.animflow
        anim = _anim_ativa(context)
        nla.remove_animation_tracks(scene, anim)
        props.animations.remove(props.active_anim_index)
        props.active_anim_index = min(props.active_anim_index, len(props.animations) - 1)
        return {'FINISHED'}


class ANIMFLOW_OT_anim_duplicate(AnimOperator, bpy.types.Operator):
    """Duplicate the active animation (same parts, layers and options)"""

    bl_idname = "animflow.anim_duplicate"
    bl_label = "Duplicate Animation"
    bl_options = {'REGISTER', 'UNDO'}

    def run(self, context):
        scene = context.scene
        origem = _anim_ativa(context)
        nome_origem = origem.name
        camadas = [(l.name, l.mute) for l in origem.layers]

        nome = _nova_animacao(scene, nome_origem)
        props = scene.animflow
        nova = props.animations[nome]
        nova.layers[0].name = camadas[0][0]
        nova.layers[0].mute = camadas[0][1]
        for lname, lmute in camadas[1:]:
            layer = nova.layers.add()
            layer.name = layer.track_name = lname
            layer.mute = lmute

        for ob in nla.animated_objects(scene):
            ad = ob.animation_data
            for lname, _m in camadas:
                src = ad.nla_tracks.get(nla.layer_track_name(nome_origem, lname))
                if src is not None:
                    nla.clone_track(ad, src, prev=None, name=nla.layer_track_name(nome, lname))
        nla.activate_animation(scene, props.animations[nome])
        return {'FINISHED'}


class ANIMFLOW_OT_anim_play(AnimOperator, bpy.types.Operator):
    """Play this animation: mute the others and use its frame range"""

    bl_idname = "animflow.anim_play"
    bl_label = "Play Animation"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(default=-1, options={'HIDDEN', 'SKIP_SAVE'})
    set_range: BoolProperty(name="Set Frame Range", default=True)

    def run(self, context):
        scene = context.scene
        props = scene.animflow
        if self.index >= 0:
            props.active_anim_index = self.index
        anim = _anim_ativa(context)
        nla.stop_part_edit(scene)
        # Uma Action ativa solta toca POR CIMA do NLA e esconde a animação.
        # Se for uma parte da biblioteca, é seguro tirá-la (ela continua salva).
        for ob in nla.animation_objects(scene, anim):
            ad = ob.animation_data
            if ad.action is not None and not ad.use_tweak_mode:
                if nla.part_for_action(scene, ad.action) is not None:
                    ad.action = None
                else:
                    self.report({'WARNING'}, rpt("'{}' has the stray Action '{}' playing on top of the NLA").format(
                        ob.name, ad.action.name))
        nla.ensure_pose_base_for(scene, anim)
        nla.activate_animation(scene, anim)
        faixa = nla.animation_range(scene, anim)
        if self.set_range and faixa:
            scene.use_preview_range = True
            scene.frame_preview_start = int(faixa[0])
            scene.frame_preview_end = int(round(faixa[1]))
        return {'FINISHED'}


class ANIMFLOW_OT_anim_add_objects(AnimOperator, bpy.types.Operator):
    """Add the selected objects to the animation (creates the layer tracks)"""

    bl_idname = "animflow.anim_add_objects"
    bl_label = "Add Objects"
    bl_options = {'REGISTER', 'UNDO'}

    def run(self, context):
        anim = _anim_ativa(context)
        obs = objetos_alvo(context)
        if not obs:
            raise AnimFlowError(rpt("Select the objects"))
        nla.ensure_pose_base(context.scene, obs)
        for ob in obs:
            for i in range(len(anim.layers)):
                nla.ensure_layer_track(ob, anim, i)
        nla.activate_animation(context.scene, anim)
        return {'FINISHED'}


# =============================================================================
# Camadas

class ANIMFLOW_OT_layer_add(AnimOperator, bpy.types.Operator):
    """Add a layer on top (e.g. an arm waving over a walk)"""

    bl_idname = "animflow.layer_add"
    bl_label = "New Layer"
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(name="Name", default="Layer")

    def invoke(self, context, _event):
        return context.window_manager.invoke_props_dialog(self)

    def run(self, context):
        scene = context.scene
        anim = _anim_ativa(context)
        nome = nla.unique_name(self.name.strip() or "Layer", {l.name for l in anim.layers})
        obs = nla.animation_objects(scene, anim) or objetos_alvo(context)
        layer = anim.layers.add()
        layer.name = layer.track_name = nome
        anim.active_layer_index = len(anim.layers) - 1
        for ob in obs:
            nla.ensure_layer_track(ob, anim, anim.active_layer_index)
        nla.activate_animation(scene, anim)
        return {'FINISHED'}


class ANIMFLOW_OT_layer_remove(AnimOperator, bpy.types.Operator):
    """Remove the active layer and the parts placed on it"""

    bl_idname = "animflow.layer_remove"
    bl_label = "Remove Layer"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def run(self, context):
        scene = context.scene
        anim, idx = _camada_ativa(context)
        if len(anim.layers) == 1:
            raise AnimFlowError(rpt("The animation needs at least one layer"))
        for ob, track in nla.layer_tracks(scene, anim, idx):
            nla.exit_tweak(ob)
            ob.animation_data.nla_tracks.remove(track)
        anim.layers.remove(idx)
        anim.active_layer_index = min(idx, len(anim.layers) - 1)
        return {'FINISHED'}


class ANIMFLOW_OT_layer_move(AnimOperator, bpy.types.Operator):
    """Change the layer order (upper layers override the ones below)"""

    bl_idname = "animflow.layer_move"
    bl_label = "Move Layer"
    bl_options = {'REGISTER', 'UNDO'}

    direction: EnumProperty(items=(('UP', "Up", ""), ('DOWN', "Down", "")))

    def run(self, context):
        anim, idx = _camada_ativa(context)
        # Na lista, a camada de cima é desenhada primeiro (índice maior = mais acima).
        novo = idx + 1 if self.direction == 'UP' else idx - 1
        if not (0 <= novo < len(anim.layers)):
            return {'CANCELLED'}
        anim.layers.move(idx, novo)
        anim.active_layer_index = novo
        nla.reorder_layers(context.scene, anim)
        return {'FINISHED'}


# =============================================================================
# Strips (partes colocadas)

class ANIMFLOW_OT_strip_add(AnimOperator, bpy.types.Operator):
    """Place a part on the active layer of the animation"""

    bl_idname = "animflow.strip_add"
    bl_label = "Add Part"
    bl_options = {'REGISTER', 'UNDO'}

    part_index: IntProperty(default=-1, options={'HIDDEN', 'SKIP_SAVE'})

    def run(self, context):
        scene = context.scene
        props = scene.animflow
        anim, idx = _camada_ativa(context)
        pi = self.part_index if self.part_index >= 0 else props.active_part_index
        if not (0 <= pi < len(props.parts)) or props.parts[pi].action is None:
            raise AnimFlowError(rpt("Choose a part from the library"))
        part = props.parts[pi]

        nla.stop_part_edit(scene)
        obs = [ob for ob in nla.animation_objects(scene, anim)
               if nla.part_slot_for(part.action, ob) is not None]
        if not obs:
            obs = nla.part_targets(scene, part.action, objetos_alvo(context))

        nla.ensure_pose_base(scene, obs)
        frame = nla.placement_frame(context, anim, idx, props.place_mode)
        # Se a camada estiver ocupada nesse frame, vai para uma camada acima.
        usada, strips = nla.place_part(scene, anim, idx, part, frame, obs)
        anim.active_layer_index = usada
        _selecionar(scene, anim, usada, strips[0])
        nla.activate_animation(scene, anim)
        if usada != idx:
            self.report({'INFO'}, rpt("Layer occupied: '{}' went to '{}'").format(
                part.name, anim.layers[usada].name))
        return {'FINISHED'}


class ANIMFLOW_OT_strip_select(AnimOperator, bpy.types.Operator):
    """Select this part to edit its options"""

    bl_idname = "animflow.strip_select"
    bl_label = "Select Animation Part"

    layer_index: IntProperty(options={'HIDDEN'})
    action_name: StringProperty(options={'HIDDEN'})
    start: FloatProperty(options={'HIDDEN'})

    def run(self, context):
        scene = context.scene
        anim = _anim_ativa(context)
        anim.active_layer_index = self.layer_index
        strips = nla.placement_strips(scene, anim, self.layer_index, self.action_name, self.start)
        if not strips:
            raise AnimFlowError(rpt("Strip not found (was it moved in the NLA?)"))
        _selecionar(scene, anim, self.layer_index, strips[0][2])
        # Seleciona também no NLA nativo.
        for _ob, track, s in strips:
            for outra in track.strips:
                outra.select = outra == s
        return {'FINISHED'}


class ANIMFLOW_OT_strip_remove(AnimOperator, bpy.types.Operator):
    """Take the selected part out of the animation (the part stays in the library)"""

    bl_idname = "animflow.strip_remove"
    bl_label = "Remove from Animation"
    bl_options = {'REGISTER', 'UNDO'}

    def run(self, context):
        anim, _idx, strips = nla.selected_placement(context.scene)
        if not strips:
            raise AnimFlowError(rpt("No part selected in the animation"))
        for ob, track, s in strips:
            nla.exit_tweak(ob)
            track.strips.remove(s)
        nla.apply_holds(context.scene, anim)
        context.scene.animflow.strip_edit.action_name = ""
        return {'FINISHED'}


class ANIMFLOW_OT_strip_duplicate(AnimOperator, bpy.types.Operator):
    """Repeat the selected part at the end of the layer (with the same options)"""

    bl_idname = "animflow.strip_duplicate"
    bl_label = "Duplicate at End"
    bl_options = {'REGISTER', 'UNDO'}

    def run(self, context):
        scene = context.scene
        anim, idx, strips = nla.selected_placement(scene)
        if not strips:
            raise AnimFlowError(rpt("No part selected in the animation"))
        fim = nla.layer_end(scene, anim, idx)
        novas = []
        for ob, track, s in strips:
            nla.exit_tweak(ob)
            novas.append(nla.clone_strip(track, s, fim))
        nla.apply_holds(scene, anim)
        _selecionar(scene, anim, idx, novas[0])
        return {'FINISHED'}


class ANIMFLOW_OT_strip_move(AnimOperator, bpy.types.Operator):
    """Swap the selected part with its neighbor"""

    bl_idname = "animflow.strip_move"
    bl_label = "Move Part"
    bl_options = {'REGISTER', 'UNDO'}

    direction: EnumProperty(items=(('LEFT', "Before", ""), ('RIGHT', "After", "")))

    def run(self, context):
        scene = context.scene
        anim, idx, strips = nla.selected_placement(scene)
        if not strips:
            raise AnimFlowError(rpt("No part selected in the animation"))
        nova_sel = None
        for ob, track, s in strips:
            ordem = nla.sorted_strips(track)
            i = ordem.index(s)
            j = i - 1 if self.direction == 'LEFT' else i + 1
            if not (0 <= j < len(ordem)):
                raise AnimFlowError(rpt("The part is already at the end of the layer"))
            a, b = sorted((i, j))
            sa, sb = ordem[a], ordem[b]
            folga = sb.frame_start - sa.frame_end
            layout = [(x, x.frame_start) for x in ordem]
            layout[b] = (sa, sa.frame_start + (sb.frame_end - sb.frame_start) + folga)
            layout[a] = (sb, sa.frame_start)
            nla.exit_tweak(ob)
            nova = nla.rebuild_track(ob.animation_data, track, layout)
            if nova_sel is None:
                # A parte movida termina na posição j da nova ordem.
                nova_sel = nla.sorted_strips(nova)[j]
        nla.apply_holds(scene, anim)
        _selecionar(scene, anim, idx, nova_sel)
        return {'FINISHED'}


class ANIMFLOW_OT_layer_pack(AnimOperator, bpy.types.Operator):
    """Pack the layer's parts one after the other (removes gaps and overlaps)"""

    bl_idname = "animflow.layer_pack"
    bl_label = "Pack in Sequence"
    bl_options = {'REGISTER', 'UNDO'}

    gap: IntProperty(name="Gap Between Parts", default=0, min=0)

    def run(self, context):
        scene = context.scene
        anim, idx = _camada_ativa(context)
        for ob, track in nla.layer_tracks(scene, anim, idx):
            ordem = nla.sorted_strips(track)
            if not ordem:
                continue
            cursor = ordem[0].frame_start
            layout = []
            for s in ordem:
                layout.append((s, cursor))
                cursor += (s.frame_end - s.frame_start) + self.gap
            nla.exit_tweak(ob)
            nla.rebuild_track(ob.animation_data, track, layout)
        scene.animflow.strip_edit.action_name = ""
        nla.apply_holds(scene, anim)
        return {'FINISHED'}


class ANIMFLOW_OT_pose_base_update(AnimOperator, bpy.types.Operator):
    """Update the base pose (rest) of every animated object"""

    bl_idname = "animflow.pose_base_update"
    bl_label = "Update Base Pose"
    bl_options = {'REGISTER', 'UNDO'}

    reset: BoolProperty(
        name="Rebuild from Scratch", default=False,
        description="Delete and recreate the rest values (use it if you changed the bones' rotation mode)",
    )

    def run(self, context):
        scene = context.scene
        if not scene.animflow.use_pose_base:
            raise AnimFlowError(rpt("Turn on the 'Base Pose' option first"))
        nla.stop_part_edit(scene)
        reparadas = nla.repair_constraint_influence()
        if reparadas:
            self.report({'INFO'}, rpt("Influence restored to 1.0 on: {}").format(", ".join(reparadas)))
        obs = nla.animated_objects(scene)
        if self.reset:
            for ob in obs:
                action = bpy.data.actions.get(nla.POSE_BASE_PREFIX + ob.name)
                slot = compat.find_slot(action, ob) if action else None
                channelbag = compat.get_channelbag(action, slot) if slot else None
                if channelbag is not None:
                    channelbag.fcurves.clear()
        nla.ensure_pose_base(scene, obs)
        anim = nla.active_animation(context)
        if anim is not None:
            nla.activate_animation(scene, anim)
        self.report({'INFO'}, rpt("Base pose updated on {} object(s)").format(len(obs)))
        return {'FINISHED'}


classes = (
    ANIMFLOW_OT_anim_new,
    ANIMFLOW_OT_anim_remove,
    ANIMFLOW_OT_anim_duplicate,
    ANIMFLOW_OT_anim_play,
    ANIMFLOW_OT_anim_add_objects,
    ANIMFLOW_OT_layer_add,
    ANIMFLOW_OT_layer_remove,
    ANIMFLOW_OT_layer_move,
    ANIMFLOW_OT_strip_add,
    ANIMFLOW_OT_strip_select,
    ANIMFLOW_OT_strip_remove,
    ANIMFLOW_OT_strip_duplicate,
    ANIMFLOW_OT_strip_move,
    ANIMFLOW_OT_layer_pack,
    ANIMFLOW_OT_pose_base_update,
)
