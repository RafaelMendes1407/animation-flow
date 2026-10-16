"""
Funções de NLA do Anim Flow: partes, animações, camadas e strips.

Convenções no NLA
-----------------
* Track de edição de parte (temporária): ``"✎ <Parte>"``. Existe só enquanto a
  parte está sendo gravada e fica em *solo*, isolando a parte.
* Track de camada de animação: ``"<Animação> › <Camada>"``. Cada parte
  colocada na camada é uma strip nessa track, em cada objeto.

Todas são tracks NLA normais: o editor NLA nativo continua funcionando.
"""

import math
import re

import bpy

from . import compat
from ..i18n import rpt

EDIT_PREFIX = "✎ "
SEP = " › "
POSE_BASE_TRACK = "· Pose base"
POSE_BASE_PREFIX = "AF_PoseBase_"
LOOSE_PREFIX = "◇ Loose "

# Expressão para extrair o nome do bone de um data_path de F-Curve.
# Ex.: pose.bones["Braço.L"].rotation_quaternion  ->  ("Braço.L", "rotation_quaternion")
_RE_BONE_PATH = re.compile(r'^pose\.bones\["((?:[^"\\]|\\.)*)"\]\.?(.*)$')

_CATEGORIAS = (
    ("location", "Loc"),
    ("rotation", "Rot"),
    ("scale", "Scale"),
    ("bbone", "BBone"),
)

# Propriedades copiadas ao clonar uma strip. A ordem importa: o intervalo da
# action vem antes da escala/repetição, que recalculam o fim da strip.
_STRIP_PROPS = (
    "action_frame_start", "action_frame_end",
    "scale", "repeat",
    "blend_type", "extrapolation",
    "blend_in", "blend_out", "use_auto_blend",
    "mute", "use_reverse", "use_sync_length",
)

# Opções editáveis pelo painel (proxy ANIMFLOW_PG_strip_edit).
_EDIT_PROPS = (
    "blend_type", "extrapolation", "use_reverse", "use_auto_blend",
    "scale", "repeat", "blend_in", "blend_out",
)


class AnimFlowError(Exception):
    """Erro com mensagem amigável, mostrado ao usuário pelos operadores."""


# =============================================================================
# Consultas gerais

def parse_bone_path(data_path):
    """Retorna (nome_do_bone, propriedade) ou (None, None)."""
    match = _RE_BONE_PATH.match(data_path)
    if not match:
        return None, None
    return bpy.utils.unescape_identifier(match.group(1)), match.group(2)


def categoria(prop):
    for prefixo, rotulo in _CATEGORIAS:
        if prop.startswith(prefixo):
            return rotulo
    return "Prop"


def animated_objects(scene):
    """Objetos da cena que possuem animation_data."""
    return [ob for ob in scene.objects if ob.animation_data is not None]


def animated_bones(action, slot, only_moved=True, eps=1e-5):
    """
    Bones com keyframes em (*action*, *slot*): {nome: set(categorias)}.
    Com *only_moved*, ignora F-Curves cujos valores nunca mudam.
    """
    bones = {}
    for fc in compat.fcurves_for(action, slot):
        bone, prop = parse_bone_path(fc.data_path)
        if bone is None or not len(fc.keyframe_points):
            continue
        if only_moved:
            valores = [k.co[1] for k in fc.keyframe_points]
            if max(valores) - min(valores) <= eps:
                continue
        bones.setdefault(bone, set()).add(categoria(prop))
    return bones


def keyed_bone_names(action, slot):
    """Nome de todos os bones que têm keyframes em (*action*, *slot*)."""
    names = set()
    for fc in compat.fcurves_for(action, slot):
        bone, _prop = parse_bone_path(fc.data_path)
        if bone is not None and len(fc.keyframe_points):
            names.add(bone)
    return names


def has_object_channels(action, slot):
    """True se houver keys fora de pose.bones (transformação do objeto)."""
    return any(
        not fc.data_path.startswith("pose.") and len(fc.keyframe_points)
        for fc in compat.fcurves_for(action, slot)
    )


def has_keys(action):
    for layer in action.layers:
        for strip in layer.strips:
            for channelbag in strip.channelbags:
                if any(len(fc.keyframe_points) for fc in channelbag.fcurves):
                    return True
    return False


def unique_name(nome, existentes):
    """*nome*, ou *nome*.001, .002... se já existir em *existentes*."""
    if nome not in existentes:
        return nome
    i = 1
    while f"{nome}.{i:03d}" in existentes:
        i += 1
    return f"{nome}.{i:03d}"


# =============================================================================
# Partes

def active_part(context):
    props = context.scene.animflow
    if 0 <= props.active_part_index < len(props.parts):
        return props.parts[props.active_part_index]
    return None


def part_for_action(scene, action):
    if action is None:
        return None
    for part in scene.animflow.parts:
        if part.action == action:
            return part
    return None


def part_slot_for(action, obj):
    """
    Slot da parte usado por *obj*: o slot com o nome do objeto ou, se a
    parte tiver um único slot, esse slot (permite usar a parte em outro rig
    com os mesmos bones).
    """
    slot = compat.find_slot(action, obj)
    if slot is None and len(action.slots) == 1:
        slot = action.slots[0]
    return slot


def part_targets(scene, action, selecionados):
    """
    Objetos que recebem a parte: os selecionados que têm slot utilizável;
    se nenhum, todos os objetos da cena com slot de mesmo nome.
    """
    alvo = [ob for ob in selecionados if part_slot_for(action, ob) is not None]
    if alvo:
        return alvo
    return [ob for ob in scene.objects if compat.find_slot(action, ob) is not None]


def part_range(action):
    """(início, fim) da parte = primeiro e último keyframe (ou intervalo manual)."""
    inicio, fim = action.frame_range
    if fim <= inicio:
        fim = inicio + 1
    return inicio, fim


def part_usage(scene, action):
    """Quantas strips de animações usam a parte."""
    total = 0
    for ob in animated_objects(scene):
        for track in ob.animation_data.nla_tracks:
            if track.name.startswith(EDIT_PREFIX):
                continue
            total += sum(1 for s in track.strips if s.action == action)
    return total


def new_part_action(nome):
    action = bpy.data.actions.new(nome)
    # Partes ficam na biblioteca mesmo sem uso no NLA.
    action.use_fake_user = True
    return action


# =============================================================================
# Modo tweak e gravação de partes

def tweak_target(obj):
    """(track, strip) onde os keyframes de *obj* estão sendo gravados, ou (None, None)."""
    ad = obj.animation_data if obj else None
    if ad is None or not ad.use_tweak_mode:
        return None, None
    track = ad.nla_tracks.active
    if track is not None:
        for strip in track.strips:
            if strip.active or strip.action == ad.action:
                return track, strip
    for track in ad.nla_tracks:
        for strip in track.strips:
            if strip.action == ad.action:
                return track, strip
    return None, None


def editing_part(scene):
    """Action da parte em gravação (track "✎"), ou None."""
    for ob in animated_objects(scene):
        for track in ob.animation_data.nla_tracks:
            if track.name.startswith(EDIT_PREFIX) and len(track.strips):
                return track.strips[0].action
    return editing_info(scene)[0]


def editing_info(scene):
    """
    (action, modo, nome_da_animação) da parte em gravação, ou (None, None, None).

    modo = 'ISOLATED' (track temporária em solo) ou 'CONTEXT' (strip da
    animação em modo tweak, com o resto da animação tocando).
    """
    owners = None
    for ob in animated_objects(scene):
        ad = ob.animation_data
        for track in ad.nla_tracks:
            if track.name.startswith(EDIT_PREFIX) and len(track.strips):
                return track.strips[0].action, 'ISOLATED', None
        if ad.use_tweak_mode and ad.action is not None and part_for_action(scene, ad.action):
            if owners is None:
                owners = track_owners(scene)
            track, _strip = tweak_target(ob)
            dono = owners.get(track.name) if track else None
            return ad.action, 'CONTEXT', dono[0].name if dono else None
    return None, None, None


def exit_tweak(obj):
    ad = obj.animation_data
    if ad is not None and ad.use_tweak_mode:
        ad.use_tweak_mode = False


def exit_tweak_all(scene):
    for ob in animated_objects(scene):
        exit_tweak(ob)


def set_record_target(obj, track):
    """Entra no modo tweak da primeira strip de *track* (como "Start Tweaking" do NLA)."""
    ad = obj.animation_data
    strip = track.strips[0] if len(track.strips) else None
    if ad is None or strip is None or strip.action is None:
        raise AnimFlowError(rpt("Track '{}' of '{}' has no strip with an Action").format(track.name, obj.name))

    exit_tweak(obj)
    for t in ad.nla_tracks:
        t.select = (t == track)
        for s in t.strips:
            s.select = False
    ad.nla_tracks.active = track
    strip.select = True
    ad.use_tweak_mode = True
    if not ad.use_tweak_mode:
        raise AnimFlowError(rpt("Could not enter tweak mode on '{}'").format(obj.name))


def start_part_edit(scene, part, objetos):
    """
    Começa a gravar a parte: cria em cada objeto uma track temporária
    "✎ <parte>" em solo e entra no modo tweak dela.

    A strip de edição fica com mapeamento 1:1 (frame da cena = frame da
    parte) e cobre todo o intervalo da cena, para gravar em qualquer frame.
    """
    if not objetos:
        raise AnimFlowError(rpt("Select the armature (or object) that will receive the keys"))
    linkados = [ob.name for ob in objetos if ob.library is not None]
    if linkados:
        raise AnimFlowError(rpt("Linked objects cannot be edited: {}").format(", ".join(linkados)))

    stop_part_edit(scene)
    action = part.action

    # Guarda o intervalo manual original para restaurar ao parar.
    if "animflow_range" not in action:
        action["animflow_range"] = (
            float(action.use_frame_range), action.frame_start, action.frame_end,
        )
    if has_keys(action):
        a0, a1 = action.frame_range
    else:
        a0, a1 = scene.frame_start, scene.frame_end
    inicio = math.floor(min(a0, scene.frame_start))
    fim = math.ceil(max(a1, scene.frame_end))
    action.use_frame_range = True
    action.frame_start = inicio
    action.frame_end = max(fim, inicio + 1)

    for ob in objetos:
        slot = part_slot_for(action, ob) or compat.ensure_slot(action, ob)
        exit_tweak(ob)
        ad = ob.animation_data_create()
        track = ad.nla_tracks.new()
        track.name = EDIT_PREFIX + part.name
        strip = track.strips.new(part.name, inicio, action)
        strip.action_slot = slot
        strip.use_sync_length = False
        track.is_solo = True
        set_record_target(ob, track)


def start_context_edit(context, anim, placements):
    """
    Grava a parte NO CONTEXTO da animação: entra no modo tweak da própria
    strip da animação, então as outras camadas continuam tocando e dá para
    ver a animação inteira enquanto anima.

    *placements*: [(objeto, track, strip)] da mesma colocação em cada objeto.
    """
    scene = context.scene
    stop_part_edit(scene)
    activate_animation(scene, anim)

    alvos = []
    for ob, track, strip in placements:
        ad = ob.animation_data
        # O Blender entra no tweak pela strip "ativa" da track, e essa flag não
        # pode ser limpa via Python. Se outra strip estiver ativa, recriamos a
        # track (as cópias nascem sem a flag).
        if any(s.active and s != strip for s in track.strips):
            chave = (strip.action, strip.frame_start)
            track = rebuild_track(ad, track, [(s, s.frame_start) for s in track.strips])
            strip = next(s for s in track.strips
                         if s.action == chave[0] and abs(s.frame_start - chave[1]) < 0.5)
        alvos.append((ob, track, strip))

    for ob in animated_objects(scene):
        for t in ob.animation_data.nla_tracks:
            t.select = False
            for s in t.strips:
                s.select = False
    for ob, track, strip in alvos:
        # Com sync length, o Blender avalia a parte pelo tamanho real dela,
        # então dá para gravar além do fim atual da strip.
        strip.use_sync_length = True
        strip.select = True
        track.select = True
        ob.animation_data.nla_tracks.active = track

    # Pelo operador do NLA dá para manter as camadas de CIMA tocando também
    # ("Full Stack"); pela API de dados só as de baixo.
    if context.area is not None and context.area.type == 'NLA_EDITOR':
        try:
            bpy.ops.nla.tweakmode_enter(use_upper_stack_evaluation=True)
        except RuntimeError:
            pass
    for ob, _track, _strip in alvos:
        ad = ob.animation_data
        if not ad.use_tweak_mode:
            ad.use_tweak_mode = True
        if not ad.use_tweak_mode:
            raise AnimFlowError(rpt("Could not enter tweak mode on '{}'").format(ob.name))


def stop_part_edit(scene):
    """
    Sai da gravação (isolada ou no contexto): remove as tracks "✎",
    sai do modo tweak e ajusta todas as strips que usam a parte.
    """
    editadas = set()
    for ob in animated_objects(scene):
        ad = ob.animation_data
        if ad.use_tweak_mode and ad.action is not None and part_for_action(scene, ad.action):
            editadas.add(ad.action)
        exit_tweak(ob)
        for track in [t for t in ad.nla_tracks if t.name.startswith(EDIT_PREFIX)]:
            editadas.update(s.action for s in track.strips if s.action is not None)
            if track.is_solo:
                track.is_solo = False
            ad.nla_tracks.remove(track)

    for action in editadas:
        salvo = action.get("animflow_range")
        if salvo is not None:
            usar, inicio, fim = salvo
            action.use_frame_range = bool(usar)
            if usar:
                action.frame_start, action.frame_end = inicio, fim
            del action["animflow_range"]
        # Desliga o sync length usado na gravação no contexto.
        for ob in animated_objects(scene):
            for track in ob.animation_data.nla_tracks:
                for s in track.strips:
                    if s.action == action and s.use_sync_length:
                        s.use_sync_length = False
        sync_part_strips(scene, action)
    if editadas:
        # Canais novos gravados nas partes entram na pose base.
        ensure_pose_base(scene, animated_objects(scene), criar=False)
    return editadas


def sync_part_strips(scene, action):
    """Ajusta as strips que usam *action* ao intervalo atual da parte (1ª–última key)."""
    if "animflow_range" in action:
        # Parte em gravação: o intervalo é temporário; sincroniza ao parar.
        return
    inicio, fim = part_range(action)
    for ob in animated_objects(scene):
        for track in ob.animation_data.nla_tracks:
            if track.name.startswith(EDIT_PREFIX):
                continue
            for strip in track.strips:
                if strip.action != action:
                    continue
                # Ordem evita que o Blender "trave" um valor no outro.
                if inicio > strip.action_frame_end:
                    strip.action_frame_end = fim
                    strip.action_frame_start = inicio
                else:
                    strip.action_frame_start = inicio
                    strip.action_frame_end = fim


# =============================================================================
# Animações e camadas

def active_animation(context):
    props = context.scene.animflow
    if 0 <= props.active_anim_index < len(props.animations):
        return props.animations[props.active_anim_index]
    return None


def layer_track_name(anim_name, layer_name):
    return f"{anim_name}{SEP}{layer_name}"


def animation_of_layer(scene, layer):
    for anim in scene.animflow.animations:
        for lay in anim.layers:
            if lay == layer:
                return anim
    return None


def track_owners(scene):
    """{nome_da_track: (animação, índice_da_camada)} para todas as animações."""
    owners = {}
    for anim in scene.animflow.animations:
        for i, layer in enumerate(anim.layers):
            owners[layer_track_name(anim.name, layer.name)] = (anim, i)
    return owners


def layer_tracks(scene, anim, layer_index):
    """Lista de (objeto, track) da camada em todos os objetos."""
    nome = layer_track_name(anim.name, anim.layers[layer_index].name)
    result = []
    for ob in animated_objects(scene):
        track = ob.animation_data.nla_tracks.get(nome)
        if track is not None:
            result.append((ob, track))
    return result


def animation_tracks(scene, anim):
    """Lista de (objeto, track, índice_da_camada) da animação."""
    result = []
    for i in range(len(anim.layers)):
        result.extend((ob, t, i) for ob, t in layer_tracks(scene, anim, i))
    return result


def animation_objects(scene, anim):
    vistos = []
    for ob, _t, _i in animation_tracks(scene, anim):
        if ob not in vistos:
            vistos.append(ob)
    return vistos


def animation_range(scene, anim):
    """(início, fim) da animação = da primeira à última strip, ou None."""
    inicios, fins = [], []
    for _ob, track, _i in animation_tracks(scene, anim):
        for s in track.strips:
            inicios.append(s.frame_start)
            fins.append(s.frame_end)
    if not inicios:
        return None
    return min(inicios), max(fins)


def ensure_layer_track(obj, anim, layer_index):
    """Track da camada em *obj*, criada logo acima da camada anterior se faltar."""
    ad = obj.animation_data_create()
    nome = layer_track_name(anim.name, anim.layers[layer_index].name)
    track = ad.nla_tracks.get(nome)
    if track is not None:
        return track

    # Procura a track da camada mais alta abaixo desta para inserir acima dela.
    anterior = None
    for i in range(layer_index - 1, -1, -1):
        anterior = ad.nla_tracks.get(layer_track_name(anim.name, anim.layers[i].name))
        if anterior is not None:
            break
    exit_tweak(obj)
    track = ad.nla_tracks.new(prev=anterior)
    track.name = nome
    if track.name != nome:
        raise AnimFlowError(rpt("A track named '{}' already exists on '{}'").format(nome, obj.name))
    return track


def rename_animation_tracks(scene, anim, antigo, novo):
    for ob in animated_objects(scene):
        tracks = ob.animation_data.nla_tracks
        for layer in anim.layers:
            track = tracks.get(layer_track_name(antigo, layer.name))
            if track is not None:
                track.name = layer_track_name(novo, layer.name)


def rename_layer_tracks(scene, anim, antigo, novo):
    for ob in animated_objects(scene):
        track = ob.animation_data.nla_tracks.get(layer_track_name(anim.name, antigo))
        if track is not None:
            track.name = layer_track_name(anim.name, novo)


def apply_layer_mutes(scene, anim):
    """Aplica o mute das camadas (só se a animação estiver tocando)."""
    ativa = _animacao_tocando(scene)
    for ob, track, i in animation_tracks(scene, anim):
        track.mute = anim.layers[i].mute or (ativa is not None and ativa != anim)


def _animacao_tocando(scene):
    props = scene.animflow
    if 0 <= props.active_anim_index < len(props.animations):
        return props.animations[props.active_anim_index]
    return None


def apply_holds(scene, anim, desligar=None):
    """
    Camadas com "Segurar pose": cada parte segura a última pose até a próxima
    (Hold Forward) e, na camada base, a 1ª parte segura a pose antes do início
    (Hold). Sem isso, fora das partes os canais voltam ao repouso (pose base)
    e o personagem "pula".

    Camadas sem a opção não são alteradas (respeita a escolha manual), exceto
    *desligar* (a camada que acabou de ter a opção desligada), que volta a "Nada".
    """
    for i, layer in enumerate(anim.layers):
        if not layer.hold and layer != desligar:
            continue
        for _ob, track in layer_tracks(scene, anim, i):
            for n, s in enumerate(sorted_strips(track)):
                if not layer.hold:
                    alvo = 'NOTHING'
                elif n == 0 and i == 0:
                    alvo = 'HOLD'
                else:
                    alvo = 'HOLD_FORWARD'
                if s.extrapolation != alvo:
                    try:
                        s.extrapolation = alvo
                    except (TypeError, ValueError):
                        pass


def activate_animation(scene, anim):
    """Deixa só *anim* audível no NLA (as outras animações ficam em mute)."""
    set_loose_playing(scene, False)
    if scene.animflow.use_pose_base:
        for ob in animation_objects(scene, anim):
            base = pose_base_track(ob)
            if base is not None and base.mute:
                base.mute = False
    apply_holds(scene, anim)
    ensure_pose_base(scene, animation_objects(scene, anim), criar=False)
    owners = track_owners(scene)
    for ob in animated_objects(scene):
        for track in ob.animation_data.nla_tracks:
            dono = owners.get(track.name)
            if dono is None:
                continue
            outra, i = dono
            track.mute = (outra != anim) or outra.layers[i].mute


def remove_animation_tracks(scene, anim):
    for ob, track, _i in animation_tracks(scene, anim):
        exit_tweak(ob)
        ob.animation_data.nla_tracks.remove(track)


# =============================================================================
# Strips (partes colocadas numa camada)

def sorted_strips(track):
    return sorted(track.strips, key=lambda s: s.frame_start)


def layer_end(scene, anim, layer_index):
    """Frame onde termina a última parte da camada (ou o início da cena)."""
    fins = [s.frame_end for _ob, t in layer_tracks(scene, anim, layer_index) for s in t.strips]
    return max(fins) if fins else float(scene.frame_start)


def reference_object(context, anim, layer_index):
    """Objeto usado para listar as strips: o ativo, se participar, senão o primeiro."""
    pares = layer_tracks(context.scene, anim, layer_index)
    for ob, track in pares:
        if ob == context.object:
            return ob, track
    return pares[0] if pares else (None, None)


def placement_strips(scene, anim, layer_index, action_name, start, tol=0.5):
    """Strips equivalentes (mesma parte, mesmo início) em todos os objetos."""
    result = []
    for ob, track in layer_tracks(scene, anim, layer_index):
        for s in track.strips:
            if s.action and s.action.name == action_name and abs(s.frame_start - start) < tol:
                result.append((ob, track, s))
                break
    return result


def add_part_to_layer(scene, anim, layer_index, part, frame, objetos):
    """Coloca a parte na camada, no *frame*, em cada objeto. Retorna as strips."""
    action = part.action
    criadas = []
    for ob in objetos:
        slot = part_slot_for(action, ob)
        if slot is None:
            continue
        track = ensure_layer_track(ob, anim, layer_index)
        exit_tweak(ob)
        try:
            strip = track.strips.new(part.name, int(round(frame)), action)
        except RuntimeError:
            raise AnimFlowError(
                rpt("No room at frame {} of layer '{}' on '{}'. Use 'After' or move the other parts")
                .format(int(frame), anim.layers[layer_index].name, ob.name)
            ) from None
        strip.action_slot = slot
        strip.use_sync_length = False
        strip.extrapolation = 'NOTHING'
        # Mistura padrão configurável (Combinar por padrão).
        strip.blend_type = scene.animflow.default_blend
        criadas.append(strip)
    if not criadas:
        raise AnimFlowError(rpt("No selected object has animation in part '{}'").format(part.name))
    apply_holds(scene, anim)
    return criadas


def layer_is_free(scene, anim, layer_index, inicio, fim, objetos):
    """True se nenhuma strip da camada ocupa [inicio, fim) nos *objetos*."""
    nome = layer_track_name(anim.name, anim.layers[layer_index].name)
    for ob in objetos:
        ad = ob.animation_data
        track = ad.nla_tracks.get(nome) if ad else None
        if track is None:
            continue
        for s in track.strips:
            if s.frame_start < fim - 1e-4 and inicio < s.frame_end - 1e-4:
                return False
    return True


def place_part(scene, anim, layer_index, part, frame, objetos):
    """
    Coloca a parte no *frame*: na camada indicada se houver espaço; senão
    na primeira camada acima com espaço; senão cria uma camada nova.
    Assim duas partes podem começar juntas (ex.: pernas + braços no frame 1).

    Retorna (índice_da_camada_usada, strips_criadas).
    """
    inicio, fim = part_range(part.action)
    frame = round(frame)
    fim_strip = frame + (fim - inicio)
    alvo = [ob for ob in objetos if part_slot_for(part.action, ob) is not None]

    for i in range(layer_index, len(anim.layers)):
        if layer_is_free(scene, anim, i, frame, fim_strip, alvo):
            return i, add_part_to_layer(scene, anim, i, part, frame, alvo)

    nome = unique_name(f"Layer {len(anim.layers) + 1}", {l.name for l in anim.layers})
    layer = anim.layers.add()
    layer.name = layer.track_name = nome
    i = len(anim.layers) - 1
    return i, add_part_to_layer(scene, anim, i, part, frame, alvo)


def placement_frame(context, anim, layer_index, modo):
    """Frame de início para colocar uma parte, conforme o modo de inserção."""
    scene = context.scene
    faixa = animation_range(scene, anim)
    inicio_anim = faixa[0] if faixa else float(scene.frame_start)
    if modo == 'AFTER':
        if any(len(t.strips) for _ob, t in layer_tracks(scene, anim, layer_index)):
            return layer_end(scene, anim, layer_index)
        return inicio_anim
    if modo == 'START':
        return inicio_anim
    if modo == 'WITH':
        sel_anim, _idx, strips = selected_placement(scene)
        if sel_anim is not None and sel_anim.name == anim.name and strips:
            return strips[0][2].frame_start
    return float(scene.frame_current)


def find_placement(scene, anim, action):
    """Primeira colocação de *action* na animação: lista [(ob, track, strip)] ou []."""
    for i in range(len(anim.layers)):
        for _ob, track in layer_tracks(scene, anim, i):
            for s in sorted_strips(track):
                if s.action == action:
                    return placement_strips(scene, anim, i, action.name, s.frame_start)
    return []


def clone_strip(dst_track, src, start):
    """Cria em *dst_track* uma cópia de *src* começando em *start*."""
    n = dst_track.strips.new(src.name, int(round(start)), src.action)
    if src.action_slot is not None:
        n.action_slot = src.action_slot
    for prop in _STRIP_PROPS:
        try:
            setattr(n, prop, getattr(src, prop))
        except (AttributeError, TypeError, ValueError, RuntimeError):
            pass
    n.frame_start_ui = start
    return n


def rebuild_track(ad, track, layout):
    """
    Recria *track* com as strips nas posições de *layout* [(strip, início)].

    A API não permite mover strips livremente (elas não podem se sobrepor
    durante o movimento), então criamos a track nova já organizada.
    """
    nome, mute, lock = track.name, track.mute, track.lock
    nova = ad.nla_tracks.new(prev=track)
    nomes = []
    for strip, inicio in sorted(layout, key=lambda par: par[1]):
        nomes.append((clone_strip(nova, strip, inicio), strip.name))
    nomes = [(n.name, original) for n, original in nomes]
    ad.nla_tracks.remove(track)
    nova.name, nova.mute, nova.lock = nome, mute, lock
    # Com a track antiga removida, as strips podem voltar aos nomes originais.
    for atual, original in nomes:
        nova.strips[atual].name = original
    return nova


def clone_track(ad, src, prev=None, name=None):
    """Cópia de *src* (com strips) acima de *prev* (ou no topo da pilha)."""
    dst = ad.nla_tracks.new(prev=prev)
    for s in src.strips:
        if s.action is not None:
            clone_strip(dst, s, s.frame_start)
    dst.name = name or src.name
    dst.mute, dst.lock = src.mute, src.lock
    return dst


def rebuild_stack(obj, ordem):
    """Reconstrói a pilha NLA de *obj* na ordem dada (de baixo para cima)."""
    ad = obj.animation_data
    atual = list(ad.nla_tracks)
    if atual == list(ordem):
        return
    exit_tweak(obj)
    nomes = [(t.name, [s.name for s in t.strips if s.action is not None]) for t in ordem]
    for t in ordem:
        clone_track(ad, t, name=t.name + ".tmp")
    for t in atual:
        ad.nla_tracks.remove(t)
    for t, (nome, strips) in zip(ad.nla_tracks, nomes):
        t.name = nome
        for s, original in zip(list(t.strips), strips):
            s.name = original


def reorder_layers(scene, anim):
    """Ordena as tracks da animação na pilha conforme a ordem das camadas."""
    nomes = [layer_track_name(anim.name, l.name) for l in anim.layers]
    for ob in animation_objects(scene, anim):
        tracks = list(ob.animation_data.nla_tracks)
        da_anim = [t for t in tracks if t.name in nomes]
        if not da_anim:
            continue
        pos = tracks.index(da_anim[0])
        outras = [t for t in tracks if t.name not in nomes]
        ordenadas = sorted(da_anim, key=lambda t: nomes.index(t.name))
        rebuild_stack(ob, outras[:pos] + ordenadas + outras[pos:])


# =============================================================================
# Pose base
#
# O Blender não reseta canais que nenhuma track ativa anima: um bone animado
# só em outra animação (silenciada) fica "preso" na última pose avaliada, e o
# resultado depende do frame em que você estava antes (efeito de teletransporte).
# A pose base é uma track no fundo da pilha, com extrapolação Hold, que segura
# cada canal animado no valor de repouso. Tudo acima dela substitui esse valor.

_PREFIXOS_REPOUSO = ("location", "rotation_", "scale", "bbone_")


def _default_do_canal(ob, data_path, index):
    """
    Valor de repouso de um canal, ou None se não houver um repouso confiável.

    * Transformações e B-Bone: o padrão do RNA (loc 0, escala 1, quaternion
      identidade...).
    * Influência de constraints, propriedades custom e o resto: ficam de fora.
      O add-on não deve mexer nesses valores do rig. Sem um padrão confiável,
      é melhor não segurar o canal do que forçar um valor errado.
    """
    if data_path.endswith('"]'):
        return None
    dono_path, _sep, nome = data_path.rpartition('.')
    if not nome.startswith(_PREFIXOS_REPOUSO):
        return None
    try:
        dono = ob.path_resolve(dono_path) if dono_path else ob
        prop = dono.bl_rna.properties.get(nome)
        if prop is None or prop.type != 'FLOAT':
            return None
        default = list(prop.default_array) if getattr(prop, "is_array", False) else prop.default
    except (ValueError, TypeError, AttributeError, KeyError):
        return None
    if isinstance(default, (list, tuple)):
        return float(default[index]) if index < len(default) else None
    return float(default) if default is not None else None


def pose_base_track(ob):
    ad = ob.animation_data
    return ad.nla_tracks.get(POSE_BASE_TRACK) if ad else None


def ensure_pose_base(scene, objetos, extras=None, criar=True):
    """
    Cria/atualiza a pose base de cada objeto.

    Com *criar*=False só atualiza os canais de pose bases que já existem
    (criar a track reorganiza a pilha e invalida referências a tracks/strips,
    então só é feito no começo dos operadores).

    Canais que já estão na pose base mantêm o valor; canais novos usam
    *extras* {(objeto, data_path, index): valor} ou o valor padrão.
    """
    if not scene.animflow.use_pose_base:
        return
    extras = extras or {}
    for ob in objetos:
        if ob.library is not None:
            continue
        if not criar and pose_base_track(ob) is None:
            continue
        ad = ob.animation_data_create()
        action = bpy.data.actions.get(POSE_BASE_PREFIX + ob.name)
        if action is None:
            action = bpy.data.actions.new(POSE_BASE_PREFIX + ob.name)
        slot = compat.ensure_slot(action, ob)
        channelbag = compat.ensure_channelbag(action, slot)

        # Todos os canais animados por alguma strip deste objeto.
        canais = set()
        for track in ad.nla_tracks:
            if track.name == POSE_BASE_TRACK:
                continue
            for s in track.strips:
                if s.action is not None and s.action != action:
                    canais.update((fc.data_path, fc.array_index)
                                  for fc in compat.fcurves_for(s.action, s.action_slot))
        canais.update((p, i) for (o, p, i) in extras if o == ob)

        frame = float(scene.frame_start)
        # Corrige canais que já existem (ex.: influência 0 gravada pela v1.3)
        # e remove os que não têm repouso confiável.
        for fc in list(channelbag.fcurves):
            valor = _default_do_canal(ob, fc.data_path, fc.array_index)
            if valor is None:
                channelbag.fcurves.remove(fc)
            elif len(fc.keyframe_points) != 1 or abs(fc.keyframe_points[0].co[1] - valor) > 1e-6:
                fc.keyframe_points.clear()
                fc.keyframe_points.add(1)
                fc.keyframe_points[0].co = (frame, valor)
                fc.keyframe_points[0].interpolation = 'CONSTANT'
                fc.update()

        for data_path, index in sorted(canais):
            if channelbag.fcurves.find(data_path, index=index) is not None:
                continue
            valor = _default_do_canal(ob, data_path, index)
            if valor is None:
                continue
            fc = channelbag.fcurves.new(data_path, index=index)
            fc.keyframe_points.add(1)
            fc.keyframe_points[0].co = (frame, valor)
            fc.keyframe_points[0].interpolation = 'CONSTANT'

        track = ad.nla_tracks.get(POSE_BASE_TRACK)
        if track is None:
            exit_tweak(ob)
            track = ad.nla_tracks.new()
            track.name = POSE_BASE_TRACK
            strip = track.strips.new("Pose base", int(frame), action)
            strip.action_slot = slot
            strip.blend_type = 'REPLACE'
            strip.extrapolation = 'HOLD'
            strip.use_sync_length = False
            track.lock = True
            # Leva para o fundo da pilha.
            outras = [t for t in ad.nla_tracks if t != track]
            rebuild_stack(ob, [track] + outras)


def ensure_pose_base_for(scene, anim):
    """Pose base dos objetos de uma animação."""
    ensure_pose_base(scene, animation_objects(scene, anim))


# =============================================================================
# Painel de opções da strip (proxy)

def load_strip_edit(edit, anim, layer, strip):
    """Carrega no proxy as opções de *strip* (sem disparar a aplicação)."""
    edit.loading = True
    try:
        edit.anim_name = anim.name
        edit.layer_name = layer.name
        edit.action_name = strip.action.name if strip.action else ""
        edit.start = strip.frame_start
        edit.frame_start = strip.frame_start
        for prop in _EDIT_PROPS:
            setattr(edit, prop, getattr(strip, prop))
    finally:
        edit.loading = False


def selected_placement(scene):
    """(animação, índice_da_camada, [(ob, track, strip)]) da strip selecionada."""
    edit = scene.animflow.strip_edit
    anim = scene.animflow.animations.get(edit.anim_name)
    if anim is None or not edit.action_name:
        return None, -1, []
    idx = anim.layers.find(edit.layer_name)
    if idx < 0:
        return anim, -1, []
    return anim, idx, placement_strips(scene, anim, idx, edit.action_name, edit.start)


def apply_strip_edit(scene, edit):
    anim, idx, strips = selected_placement(scene)
    if not strips:
        return
    for _ob, _track, s in strips:
        for prop in _EDIT_PROPS:
            try:
                if getattr(s, prop) != getattr(edit, prop):
                    setattr(s, prop, getattr(edit, prop))
            except (TypeError, ValueError, RuntimeError):
                pass
        if abs(s.frame_start - edit.frame_start) > 1e-4:
            s.frame_start_ui = edit.frame_start
    # Atualiza a identificação (o início pode ter mudado ou sido limitado).
    load_strip_edit(edit, anim, anim.layers[idx], strips[0][2])


# =============================================================================
# Cópia de F-Curves (canais)

def fcurve_to_dict(fc):
    """Serializa uma F-Curve para a área de transferência interna."""
    n = len(fc.keyframe_points)
    co = [0.0] * (2 * n)
    hl = [0.0] * (2 * n)
    hr = [0.0] * (2 * n)
    fc.keyframe_points.foreach_get("co", co)
    fc.keyframe_points.foreach_get("handle_left", hl)
    fc.keyframe_points.foreach_get("handle_right", hr)
    extras = [
        (k.interpolation, k.handle_left_type, k.handle_right_type, k.easing, k.type)
        for k in fc.keyframe_points
    ]
    return {
        "data_path": fc.data_path,
        "index": fc.array_index,
        "group": fc.group.name if fc.group else "",
        "extrapolation": fc.extrapolation,
        "co": co, "hl": hl, "hr": hr, "extra": extras,
    }


def dict_to_fcurve(channelbag, data, offset=0.0, replace=True):
    """Escreve uma F-Curve serializada em *channelbag*."""
    fc = channelbag.fcurves.find(data["data_path"], index=data["index"])
    if fc is None:
        fc = channelbag.fcurves.new(data["data_path"], index=data["index"])
        if data["group"]:
            grupo = channelbag.groups.get(data["group"]) or channelbag.groups.new(data["group"])
            try:
                fc.group = grupo
            except (TypeError, RuntimeError):
                pass
    elif replace:
        fc.keyframe_points.clear()

    fc.extrapolation = data["extrapolation"]
    n = len(data["extra"])

    def desloca(valores):
        return [v + offset if i % 2 == 0 else v for i, v in enumerate(valores)]

    co, hl, hr = desloca(data["co"]), desloca(data["hl"]), desloca(data["hr"])

    if len(fc.keyframe_points) == 0:
        fc.keyframe_points.add(n)
        fc.keyframe_points.foreach_set("co", co)
        fc.keyframe_points.foreach_set("handle_left", hl)
        fc.keyframe_points.foreach_set("handle_right", hr)
        keys = list(fc.keyframe_points)
    else:
        keys = []
        for i in range(n):
            k = fc.keyframe_points.insert(co[2 * i], co[2 * i + 1], options={'FAST'})
            k.handle_left = hl[2 * i:2 * i + 2]
            k.handle_right = hr[2 * i:2 * i + 2]
            keys.append(k)

    for k, (interp, hlt, hrt, easing, ktype) in zip(keys, data["extra"]):
        k.interpolation = interp
        k.handle_left_type = hlt
        k.handle_right_type = hrt
        k.easing = easing
        k.type = ktype
    fc.update()
    return fc


# =============================================================================
# Migração da versão 1.0 (animação = uma Action com track própria)

def migrate_v1(scene):
    """Converte animações antigas em Parte + Animação com camada "Base"."""
    props = scene.animflow
    convertidas = 0
    for anim in props.animations:
        action = anim.action
        if action is None or len(anim.layers):
            continue
        if part_for_action(scene, action) is None:
            part = props.parts.add()
            part.action = action
            part.name = action.name
        action.use_fake_user = True
        if action.use_frame_range:
            action.use_frame_range = False

        layer = anim.layers.add()
        layer.name = "Base"
        layer.track_name = "Base"
        anim.track_prefix = anim.name
        novo_nome = layer_track_name(anim.name, "Base")
        for ob in animated_objects(scene):
            for track in ob.animation_data.nla_tracks:
                if any(s.action == action for s in track.strips) and not track.name.startswith(EDIT_PREFIX):
                    track.name = novo_nome
                    for s in track.strips:
                        s.extrapolation = 'NOTHING'
                        s.use_sync_length = False
                    break
        sync_part_strips(scene, action)
        anim.action = None
        convertidas += 1
    return convertidas


# =============================================================================
# Reparo: as versões 1.3 a 1.5 zeravam a influência de constraints

_RE_INFLUENCIA = re.compile(
    r'^pose\.bones\["((?:[^"\\]|\\.)*)"\]\.constraints\["((?:[^"\\]|\\.)*)"\]\.influence$'
)


def repair_constraint_influence():
    """
    Desfaz o que as versões 1.3–1.5 faziam no bake com Visual Keying: keys de
    influência 0 nas constraints (na Action "[bake]") e o canal de influência
    na pose base. Tocar o "[bake]" deixava a constraint com influência 0 no rig
    (ex.: IK desligado).

    Remove esses canais e devolve influência 1.0 às constraints afetadas que
    ficaram em 0. Retorna a lista de "objeto › bone › constraint" reparados.
    """
    afetadas = set()
    for action in bpy.data.actions:
        eh_base = action.name.startswith(POSE_BASE_PREFIX)
        eh_bake = action.name.split(".")[0].endswith("_bake")
        if not (eh_base or eh_bake):
            continue
        for layer in action.layers:
            for strip in layer.strips:
                for channelbag in strip.channelbags:
                    for fc in list(channelbag.fcurves):
                        m = _RE_INFLUENCIA.match(fc.data_path)
                        if not m:
                            continue
                        pontos = fc.keyframe_points
                        # Só os canais criados pelo add-on: 1 key constante (0 no bake).
                        if eh_bake and not (len(pontos) == 1 and abs(pontos[0].co[1]) < 1e-6):
                            continue
                        afetadas.add((bpy.utils.unescape_identifier(m.group(1)),
                                      bpy.utils.unescape_identifier(m.group(2))))
                        channelbag.fcurves.remove(fc)

    reparadas = []
    if not afetadas:
        return reparadas
    for ob in bpy.data.objects:
        if ob.type != 'ARMATURE' or ob.library is not None:
            continue
        for bone, nome_c in afetadas:
            pb = ob.pose.bones.get(bone)
            c = pb.constraints.get(nome_c) if pb else None
            if c is not None and c.influence < 1e-6:
                c.influence = 1.0
                reparadas.append(f"{ob.name} › {bone} › {nome_c}")
    return reparadas


# =============================================================================
# Verificação do rig

def ik_cycles(ob):
    """
    Alvos (e poles) de IK que são filhos de um bone da própria cadeia.

    Isso cria um ciclo de dependência: o alvo se move junto com a perna que
    ele puxa, e o Blender passa a usar valores do frame anterior. A pose de um
    frame muda conforme de onde você veio na timeline ("às vezes salta, às
    vezes não"), e o bake copia esse comportamento.
    Retorna [(bone_com_IK, alvo, bone_da_cadeia_que_é_ancestral)].
    """
    if ob is None or ob.type != 'ARMATURE':
        return []
    result = []
    for pb in ob.pose.bones:
        for c in pb.constraints:
            if c.type not in {'IK', 'SPLINE_IK'} or not c.enabled:
                continue
            cadeia, atual = [], pb
            limite = c.chain_count if c.chain_count > 0 else 10 ** 6
            while atual is not None and len(cadeia) < limite:
                cadeia.append(atual.name)
                atual = atual.parent
            alvos = [getattr(c, "subtarget", ""), getattr(c, "pole_subtarget", "")]
            for alvo in alvos:
                bone = ob.data.bones.get(alvo) if alvo and getattr(c, "target", None) == ob else None
                pai = bone.parent if bone else None
                while pai is not None:
                    if pai.name in cadeia:
                        result.append((pb.name, alvo, pai.name))
                        break
                    pai = pai.parent
    return result



# =============================================================================
# Strips soltas
#
# Partes colocadas no NLA fora de qualquer animação (duplo clique na parte),
# em tracks "◇ Loose N". Todas as soltas tocam juntas; tocar uma animação as
# silencia, e tocar as soltas silencia as animações.

def is_loose_track(track):
    return track.name.startswith(LOOSE_PREFIX)


def loose_strips(scene):
    """[(objeto, track, strip)] de todas as strips soltas, em ordem de tempo."""
    result = []
    for ob in animated_objects(scene):
        for track in ob.animation_data.nla_tracks:
            if is_loose_track(track):
                result.extend((ob, track, s) for s in track.strips)
    return sorted(result, key=lambda item: (item[2].frame_start, item[0].name))


def set_loose_playing(scene, tocar):
    """Liga/desliga as strips soltas (e silencia as animações quando ligadas)."""
    props = scene.animflow
    props.loose_playing = tocar
    owners = track_owners(scene) if tocar else {}
    for ob in animated_objects(scene):
        for track in ob.animation_data.nla_tracks:
            if is_loose_track(track):
                track.mute = not tocar
            elif tocar and track.name in owners:
                track.mute = True


def add_loose_strip(scene, part, frame, objetos):
    """
    Coloca *part* como strip solta no *frame*: na primeira track solta com
    espaço, ou numa track solta nova. Retorna as strips criadas.
    """
    action = part.action
    inicio, fim = part_range(action)
    frame = round(frame)
    fim_strip = frame + (fim - inicio)
    criadas = []
    for ob in objetos:
        slot = part_slot_for(action, ob)
        if slot is None or ob.library is not None:
            continue
        exit_tweak(ob)
        ad = ob.animation_data_create()
        soltas = [t for t in ad.nla_tracks if is_loose_track(t)]
        alvo = None
        for track in soltas:
            if all(not (s.frame_start < fim_strip - 1e-4 and frame < s.frame_end - 1e-4)
                   for s in track.strips):
                alvo = track
                break
        if alvo is None:
            alvo = ad.nla_tracks.new(prev=soltas[-1] if soltas else None)
            alvo.name = unique_name(f"{LOOSE_PREFIX}{len(soltas) + 1}",
                                    {t.name for t in ad.nla_tracks})
        strip = alvo.strips.new(part.name, frame, action)
        strip.action_slot = slot
        strip.use_sync_length = False
        strip.extrapolation = 'NOTHING'
        strip.blend_type = scene.animflow.default_blend
        criadas.append(strip)
    if not criadas:
        raise AnimFlowError(rpt("No selected object has animation in part '{}'").format(part.name))
    ensure_pose_base(scene, objetos, criar=False)
    set_loose_playing(scene, True)
    return criadas


def clear_loose(scene):
    """Remove todas as tracks soltas. Retorna quantas strips foram removidas."""
    total = 0
    for ob in animated_objects(scene):
        ad = ob.animation_data
        for track in [t for t in ad.nla_tracks if is_loose_track(t)]:
            exit_tweak(ob)
            total += len(track.strips)
            ad.nla_tracks.remove(track)
    scene.animflow.loose_playing = False
    return total
