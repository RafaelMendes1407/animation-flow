"""
Operadores de Partes: criar, gravar, parar, duplicar, remover, importar,
strips soltas (duplo clique), além de utilidades (selecionar bone, inserir
keyframe protegido).
"""

import time

import bpy
from bpy.props import BoolProperty, IntProperty, StringProperty

from ..i18n import iface, rpt
from ..utils import compat
from ..utils import nla
from ..utils.nla import AnimFlowError


def objetos_alvo(context):
    """Objetos selecionados (ou o ativo), editáveis."""
    obs = list(context.selected_objects)
    if not obs and context.object:
        obs = [context.object]
    return [ob for ob in obs if ob.library is None]


def nova_parte(scene, action, nome):
    """Registra uma parte no topo da biblioteca e a torna ativa."""
    props = scene.animflow
    part = props.parts.add()
    part.action = action
    part.name = nome
    props.parts.move(len(props.parts) - 1, 0)
    props.active_part_index = 0
    return props.parts[0]


class AnimOperator:
    """Base comum: trata AnimFlowError com mensagem clara."""

    def execute(self, context):
        try:
            return self.run(context)
        except AnimFlowError as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}


def gravar_parte(context, part, objetos=None):
    """
    Começa a gravar *part*. Se ela for usada na animação ativa (e a opção
    estiver ligada), grava no contexto da animação; senão, isolada.
    Retorna um texto descrevendo o modo, para o relatório.
    """
    scene = context.scene
    props = scene.animflow
    anim = nla.active_animation(context)
    if props.record_in_context and anim is not None:
        nla.ensure_pose_base_for(scene, anim)
        sel_anim, _idx, strips = nla.selected_placement(scene)
        if (sel_anim is not None and sel_anim.name == anim.name and strips
                and strips[0][2].action == part.action):
            colocacao = strips
        else:
            colocacao = nla.find_placement(scene, anim, part.action)
        if colocacao:
            nla.start_context_edit(context, anim, colocacao)
            return rpt("in the context of '{}'").format(anim.name)

    alvo = nla.part_targets(scene, part.action, objetos if objetos is not None else objetos_alvo(context))
    if not alvo:
        # Parte ainda vazia: usa os objetos selecionados.
        alvo = objetos_alvo(context)
    nla.start_part_edit(scene, part, alvo)
    return rpt("isolated")


def _part_por_indice(context, index):
    props = context.scene.animflow
    if index < 0:
        index = props.active_part_index
    if 0 <= index < len(props.parts):
        return props.parts[index]
    return None


class ANIMFLOW_OT_part_new(AnimOperator, bpy.types.Operator):
    """Create a new part (animation clip) and start recording into it"""

    bl_idname = "animflow.part_new"
    bl_label = "New Part"
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(name="Name", default="Part")
    record: BoolProperty(name="Start Recording", default=True,
                         description="The next keyframes go into this part")
    place_in_anim: BoolProperty(
        name="Place in Active Animation", default=True,
        description=(
            "Place the part in the active animation right away (using the chosen insert mode) "
            "and record while seeing the whole animation"
        ),
    )

    def invoke(self, context, _event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "name")
        layout.prop(self, "record")
        anim = nla.active_animation(context)
        if anim is not None:
            layout.prop(self, "place_in_anim", text=iface("Place in '{}'").format(anim.name))
            row = layout.row()
            row.enabled = self.place_in_anim
            row.prop(context.scene.animflow, "place_mode", expand=True)
        obs = objetos_alvo(context)
        box = layout.box()
        box.label(text=iface("Objects ({}):").format(len(obs)), icon='OBJECT_DATA')
        for ob in obs[:8]:
            box.label(text=ob.name, translate=False,
                      icon='OUTLINER_OB_ARMATURE' if ob.type == 'ARMATURE' else 'OBJECT_DATA')

    def run(self, context):
        scene = context.scene
        obs = objetos_alvo(context)
        if not obs:
            raise AnimFlowError(rpt("Select the armature (or object) to animate"))
        nome = self.name.strip()
        if not nome:
            raise AnimFlowError(rpt("Give the part a name"))

        action = nla.new_part_action(nome)
        for ob in obs:
            compat.ensure_slot(action, ob)
        part = nova_parte(scene, action, action.name)
        nome_parte = part.name

        anim = nla.active_animation(context)
        if anim is not None and self.place_in_anim:
            nla.stop_part_edit(scene)
            nla.ensure_pose_base(scene, obs)
            idx = min(max(anim.active_layer_index, 0), len(anim.layers) - 1)
            frame = nla.placement_frame(context, anim, idx, scene.animflow.place_mode)
            idx, strips = nla.place_part(scene, anim, idx, part, frame, obs)
            anim.active_layer_index = idx
            nla.load_strip_edit(scene.animflow.strip_edit, anim, anim.layers[idx], strips[0])
            if self.record:
                colocacao = nla.placement_strips(scene, anim, idx, action.name, strips[0].frame_start)
                nla.start_context_edit(context, anim, colocacao)
            self.report({'INFO'}, rpt("Part '{}' created in '{}' (frame {:.0f})").format(
                nome_parte, anim.name, strips[0].frame_start))
            return {'FINISHED'}

        if self.record:
            nla.start_part_edit(scene, part, obs)
        self.report({'INFO'}, rpt("Part '{}' created").format(nome_parte))
        return {'FINISHED'}


class ANIMFLOW_OT_part_record(AnimOperator, bpy.types.Operator):
    """Record the next keyframes into this part"""

    bl_idname = "animflow.part_record"
    bl_label = "Record Part"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(default=-1, options={'HIDDEN', 'SKIP_SAVE'})

    def run(self, context):
        scene = context.scene
        part = _part_por_indice(context, self.index)
        if part is None or part.action is None:
            raise AnimFlowError(rpt("No part selected"))
        if self.index >= 0:
            scene.animflow.active_part_index = self.index
            part = scene.animflow.parts[self.index]

        # Clicar de novo na parte em gravação para a gravação.
        if nla.editing_part(scene) == part.action:
            nla.stop_part_edit(scene)
            return {'FINISHED'}

        modo = gravar_parte(context, part)
        self.report({'INFO'}, rpt("Recording '{}' {}").format(part.name, modo))
        return {'FINISHED'}


class ANIMFLOW_OT_part_stop(bpy.types.Operator):
    """Stop recording: remove the temporary track and update the animations that use the part"""

    bl_idname = "animflow.part_stop"
    bl_label = "Stop Recording"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        nla.stop_part_edit(scene)
        nla.exit_tweak_all(scene)
        anim = nla.active_animation(context)
        if scene.animflow.loose_playing:
            nla.set_loose_playing(scene, True)
        elif anim is not None and scene.animflow.auto_activate:
            nla.activate_animation(scene, anim)
        return {'FINISHED'}


class ANIMFLOW_OT_part_duplicate(AnimOperator, bpy.types.Operator):
    """Duplicate the active part (to make a variation)"""

    bl_idname = "animflow.part_duplicate"
    bl_label = "Duplicate Part"
    bl_options = {'REGISTER', 'UNDO'}

    def run(self, context):
        part = nla.active_part(context)
        if part is None or part.action is None:
            raise AnimFlowError(rpt("No active part"))
        copia = part.action.copy()
        copia.use_fake_user = True
        nova_parte(context.scene, copia, copia.name)
        return {'FINISHED'}


class ANIMFLOW_OT_part_remove(AnimOperator, bpy.types.Operator):
    """Remove the active part from the library"""

    bl_idname = "animflow.part_remove"
    bl_label = "Remove Part"
    bl_options = {'REGISTER', 'UNDO'}

    from_animations: BoolProperty(
        name="Also Remove from Animations", default=False,
        description="Delete this part's strips in the animations; off: cancel if the part is in use",
    )
    delete_action: BoolProperty(
        name="Delete the Action", default=True,
        description="Delete the data; off: the Action stays in the file (with Fake User)",
    )

    def invoke(self, context, _event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        part = nla.active_part(context)
        if part and part.action:
            usos = nla.part_usage(context.scene, part.action)
            layout.label(text=iface("'{}' is used in {} strip(s)").format(part.name, usos), icon='INFO')
        layout.prop(self, "from_animations")
        layout.prop(self, "delete_action")

    def run(self, context):
        scene = context.scene
        props = scene.animflow
        part = nla.active_part(context)
        if part is None:
            raise AnimFlowError(rpt("No active part"))
        action = part.action
        if action is not None:
            usos = nla.part_usage(scene, action)
            if usos and not self.from_animations:
                raise AnimFlowError(
                    rpt("'{}' is used in {} strip(s). Check 'Also Remove from Animations'")
                    .format(part.name, usos)
                )
            if nla.editing_part(scene) == action:
                nla.stop_part_edit(scene)
            for ob in nla.animated_objects(scene):
                nla.exit_tweak(ob)
                for track in ob.animation_data.nla_tracks:
                    for s in [s for s in track.strips if s.action == action]:
                        track.strips.remove(s)
        props.parts.remove(props.active_part_index)
        props.active_part_index = min(props.active_part_index, len(props.parts) - 1)
        if action is not None:
            if self.delete_action:
                bpy.data.actions.remove(action)
            else:
                action.use_fake_user = True
        return {'FINISHED'}


class ANIMFLOW_OT_part_set_range(AnimOperator, bpy.types.Operator):
    """Use the active part's range (first to last key) as the Preview Range"""

    bl_idname = "animflow.part_set_range"
    bl_label = "Part Range"
    bl_options = {'REGISTER', 'UNDO'}

    def run(self, context):
        part = nla.active_part(context)
        if part is None or part.action is None:
            raise AnimFlowError(rpt("No active part"))
        inicio, fim = nla.part_range(part.action)
        scene = context.scene
        scene.use_preview_range = True
        scene.frame_preview_start = int(inicio)
        scene.frame_preview_end = int(fim)
        return {'FINISHED'}


# =============================================================================
# Clique / duplo clique e strips soltas

# Último clique na lista de partes, para detectar o duplo clique.
_ultimo_clique = {"index": -1, "t": 0.0}


def adicionar_solta(operador, context, index):
    """Coloca a parte *index* como strip solta no frame atual."""
    scene = context.scene
    part = _part_por_indice(context, index)
    if part is None or part.action is None:
        raise AnimFlowError(rpt("No part selected"))
    if nla.editing_part(scene) is not None:
        nla.stop_part_edit(scene)
    alvo = nla.part_targets(scene, part.action, objetos_alvo(context))
    if not alvo:
        raise AnimFlowError(rpt("No selected object has animation in part '{}'").format(part.name))
    nla.ensure_pose_base(scene, alvo)
    strips = nla.add_loose_strip(scene, part, scene.frame_current, alvo)
    operador.report({'INFO'}, rpt("'{}' added as a loose strip at frame {:.0f}").format(
        part.name, strips[0].frame_start))
    return {'FINISHED'}


class ANIMFLOW_OT_part_click(AnimOperator, bpy.types.Operator):
    """Click: select the part. Double-click: add it to the NLA as a loose strip at the current frame"""

    bl_idname = "animflow.part_click"
    bl_label = "Select Part"
    bl_options = {'UNDO'}

    index: IntProperty(options={'HIDDEN'})

    def invoke(self, context, event):
        agora = time.monotonic()
        limite = context.preferences.inputs.mouse_double_click_time / 1000.0
        duplo = (event.value == 'DOUBLE_CLICK'
                 or (_ultimo_clique["index"] == self.index and agora - _ultimo_clique["t"] <= limite))
        # Depois de um duplo clique, zera para o 3º clique não contar de novo.
        _ultimo_clique.update(index=self.index, t=0.0 if duplo else agora)
        context.scene.animflow.active_part_index = self.index
        if not duplo:
            return {'FINISHED'}
        return self.execute(context)

    def run(self, context):
        return adicionar_solta(self, context, self.index)


class ANIMFLOW_OT_loose_add(AnimOperator, bpy.types.Operator):
    """Add the active part to the NLA as a loose strip at the current frame (same as double-clicking it)"""

    bl_idname = "animflow.loose_add"
    bl_label = "Add as Loose Strip"
    bl_options = {'REGISTER', 'UNDO'}

    part_index: IntProperty(default=-1, options={'HIDDEN', 'SKIP_SAVE'})

    def run(self, context):
        return adicionar_solta(self, context, self.part_index)


class ANIMFLOW_OT_loose_play(AnimOperator, bpy.types.Operator):
    """Play all loose strips together (mutes the animations). Click again to go back to the active animation"""

    bl_idname = "animflow.loose_play"
    bl_label = "Play Loose Strips"
    bl_options = {'REGISTER', 'UNDO'}

    def run(self, context):
        scene = context.scene
        if not nla.loose_strips(scene):
            raise AnimFlowError(rpt("There are no loose strips. Double-click a part to add one"))
        nla.stop_part_edit(scene)
        if scene.animflow.loose_playing:
            anim = nla.active_animation(context)
            if anim is not None:
                nla.activate_animation(scene, anim)
            else:
                nla.set_loose_playing(scene, False)
        else:
            nla.set_loose_playing(scene, True)
        return {'FINISHED'}


class ANIMFLOW_OT_loose_remove(AnimOperator, bpy.types.Operator):
    """Remove this loose strip (the part stays in the library)"""

    bl_idname = "animflow.loose_remove"
    bl_label = "Remove Loose Strip"
    bl_options = {'REGISTER', 'UNDO'}

    object_name: StringProperty(options={'HIDDEN'})
    track_name: StringProperty(options={'HIDDEN'})
    strip_name: StringProperty(options={'HIDDEN'})

    def run(self, context):
        ob = context.scene.objects.get(self.object_name)
        ad = ob.animation_data if ob else None
        track = ad.nla_tracks.get(self.track_name) if ad else None
        strip = track.strips.get(self.strip_name) if track else None
        if strip is None:
            raise AnimFlowError(rpt("Loose strip not found"))
        nla.exit_tweak(ob)
        track.strips.remove(strip)
        if not len(track.strips):
            ad.nla_tracks.remove(track)
        return {'FINISHED'}


class ANIMFLOW_OT_loose_clear(AnimOperator, bpy.types.Operator):
    """Remove all loose strips (the parts stay in the library)"""

    bl_idname = "animflow.loose_clear"
    bl_label = "Clear Loose Strips"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def run(self, context):
        scene = context.scene
        n = nla.clear_loose(scene)
        anim = nla.active_animation(context)
        if anim is not None:
            nla.activate_animation(scene, anim)
        self.report({'INFO'}, rpt("{} loose strip(s) removed").format(n))
        return {'FINISHED'}


# =============================================================================
# Importar e utilidades

class ANIMFLOW_OT_import(AnimOperator, bpy.types.Operator):
    """Organize what already exists in the file: strip Actions become Parts and stray tracks become Animations"""

    bl_idname = "animflow.import_existing"
    bl_label = "Import from NLA"
    bl_options = {'REGISTER', 'UNDO'}

    convert_tracks: BoolProperty(
        name="Convert Tracks to Animations", default=True,
        description="Each track that doesn't belong to an animation becomes an animation with a 'Base' layer",
    )

    def invoke(self, context, _event):
        return context.window_manager.invoke_props_dialog(self)

    def run(self, context):
        scene = context.scene
        props = scene.animflow
        convertidas = nla.migrate_v1(scene)

        # Remove partes cujas Actions foram apagadas.
        for i in reversed(range(len(props.parts))):
            if props.parts[i].action is None:
                props.parts.remove(i)

        registradas = {p.action for p in props.parts}
        owners = nla.track_owners(scene)
        n_partes = n_anims = 0
        soltas = []
        for ob in nla.animated_objects(scene):
            for track in ob.animation_data.nla_tracks:
                if (track.name.startswith(nla.EDIT_PREFIX) or track.name == nla.POSE_BASE_TRACK
                        or nla.is_loose_track(track)):
                    continue
                for strip in track.strips:
                    act = strip.action
                    if act is not None and act not in registradas:
                        act.use_fake_user = True
                        part = props.parts.add()
                        part.action = act
                        part.name = act.name
                        registradas.add(act)
                        n_partes += 1
                if track.name not in owners:
                    soltas.append((ob.name, track.name))

        if self.convert_tracks:
            for ob_name, track_name in soltas:
                ob = scene.objects[ob_name]
                track = ob.animation_data.nla_tracks.get(track_name)
                anim = props.animations.get(track_name)
                if anim is None:
                    anim = props.animations.add()
                    anim.name = track_name
                    anim.track_prefix = track_name
                    layer = anim.layers.add()
                    layer.name = layer.track_name = "Base"
                    n_anims += 1
                track.name = nla.layer_track_name(track_name, "Base")
                for s in track.strips:
                    s.use_sync_length = False

        nla.ensure_pose_base(scene, nla.animated_objects(scene))
        msg = rpt("{} part(s) and {} animation(s) imported").format(n_partes, n_anims)
        if convertidas:
            msg += "; " + rpt("{} v1.0 animation(s) converted").format(convertidas)
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class ANIMFLOW_OT_select_bone(AnimOperator, bpy.types.Operator):
    """Select this bone (Shift: add to the selection)"""

    bl_idname = "animflow.select_bone"
    bl_label = "Select Bone"
    bl_options = {'REGISTER', 'UNDO'}

    object_name: StringProperty(options={'HIDDEN'})
    bone_name: StringProperty(options={'HIDDEN'})
    extend: BoolProperty(default=False, options={'SKIP_SAVE'})

    def invoke(self, context, event):
        self.extend = event.shift
        return self.execute(context)

    def run(self, context):
        ob = context.scene.objects.get(self.object_name)
        if ob is None or ob.type != 'ARMATURE':
            raise AnimFlowError(rpt("Invalid armature"))
        if ob.mode != 'POSE':
            raise AnimFlowError(rpt("Put '{}' in Pose Mode to select bones").format(ob.name))
        pb = ob.pose.bones.get(self.bone_name)
        if pb is None:
            raise AnimFlowError(rpt("Bone '{}' doesn't exist").format(self.bone_name))
        if not self.extend:
            for outro in ob.pose.bones:
                compat.pose_bone_set_selected(outro, False)
        compat.pose_bone_set_selected(pb, True)
        ob.data.bones.active = pb.bone
        compat.tag_redraw_all()
        return {'FINISHED'}


class ANIMFLOW_OT_insert_keyframe(bpy.types.Operator):
    """Insert a keyframe only if a part is being recorded (optional protection of the I key)"""

    bl_idname = "animflow.insert_keyframe"
    bl_label = "Insert Keyframe (with Target Part)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'POSE'

    def execute(self, context):
        track, _strip = nla.tweak_target(context.object)
        if track is None:
            self.report({'ERROR'}, rpt("No part is being recorded: create a part or click ● Record"))
            return {'CANCELLED'}
        return bpy.ops.anim.keyframe_insert()


classes = (
    ANIMFLOW_OT_part_new,
    ANIMFLOW_OT_part_record,
    ANIMFLOW_OT_part_stop,
    ANIMFLOW_OT_part_duplicate,
    ANIMFLOW_OT_part_remove,
    ANIMFLOW_OT_part_set_range,
    ANIMFLOW_OT_part_click,
    ANIMFLOW_OT_loose_add,
    ANIMFLOW_OT_loose_play,
    ANIMFLOW_OT_loose_remove,
    ANIMFLOW_OT_loose_clear,
    ANIMFLOW_OT_import,
    ANIMFLOW_OT_select_bone,
    ANIMFLOW_OT_insert_keyframe,
)
