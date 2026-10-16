"""
Traduções do Anim Flow.

O texto da interface é escrito em inglês (padrão do Blender) e traduzido
para português pelo sistema nativo ``bpy.app.translations``. Para usar em
português: Edit › Preferences › Interface › Translation › Language
"Português (Brasil)" (ou "Português") e marque "Interface", "Tooltips" e
"Reports".

* Textos fixos (nomes, descrições, ``text=``, ``bl_label``) são traduzidos
  automaticamente pelo Blender a partir deste dicionário.
* Textos com valores usam ``iface("...{}").format(...)``: o modelo é traduzido
  antes de receber os valores.
* Mensagens de relatório/erro usam ``rpt(...)``.
"""

import bpy

_translations = bpy.app.translations


def iface(msg):
    """Traduz um texto de interface (rótulos)."""
    return _translations.pgettext_iface(msg)


def rpt(msg):
    """Traduz uma mensagem de relatório/erro."""
    traduzir = getattr(_translations, "pgettext_rpt", _translations.pgettext)
    return traduzir(msg)


# Inglês -> português (Brasil).
PT_BR = {
    # --- Geral / modos ----------------------------------------------------------
    "Anim Flow": "Anim Flow",
    "Mode": "Modo",
    "Parts": "Partes",
    "Animations": "Animações",
    "Bake": "Bake",
    "Record and edit parts": "Gravar e editar partes",
    "Compose animations from parts": "Compor animações com as partes",
    "Bake animations": "Bake das animações",
    "Name": "Nome",
    "Part": "Parte",
    "Animation": "Animação",
    "Layer": "Camada",
    "Action": "Action",
    "Mute": "Mute",
    "Mute this layer": "Silencia esta camada",
    "empty": "vazia",
    "nothing": "nada",
    "object": "objeto",
    "Start": "Início",
    "End": "Fim",
    "Play": "Tocar",
    "Stop": "Parar",
    "Record": "Gravar",
    "Range": "Intervalo",
    "Copy": "Copiar",
    "Paste": "Colar",
    "Delete": "Apagar",
    "Pack": "Encostar",
    "Reset": "Resetar",
    "Up": "Subir",
    "Down": "Descer",
    "Before": "Antes",
    "After": "Depois",
    "Together": "Junto",
    "Target": "Destino",
    "Loose": "Solta",
    "Send to…": "Enviar para…",
    "Diagnostics": "Diagnóstico",

    # --- Propriedades -----------------------------------------------------------
    "Hold Pose": "Segurar pose",
    "Each part holds its last pose until the next one (and, on the base layer, the first part holds "
    "its pose before it starts). Turn off on overlay layers that should release back to the layer "
    "below when the part ends":
        "Cada parte segura a última pose até a próxima (e, na camada base, a primeira segura a pose "
        "antes do início). Desligue em camadas de sobreposição que devem 'soltar' de volta para a "
        "camada de baixo quando a parte acaba",
    "Active Layer": "Camada ativa",
    "Include in Bake": "Incluir no bake",
    "Frame where the part starts": "Frame em que a parte começa",
    "Repeat": "Repetir",
    "How many times the part repeats": "Quantas vezes a parte se repete",
    "Speed (Scale)": "Velocidade (escala)",
    "Time scale: 2 = half speed, 0.5 = double speed": "Escala de tempo: 2 = metade da velocidade, 0.5 = dobro",
    "Reverse": "Inverter",
    "Play the part backwards": "Toca a parte de trás para frente",
    "Blend In": "Blend In",
    "Transition frames at the start": "Frames de transição na entrada",
    "Blend Out": "Blend Out",
    "Transition frames at the end": "Frames de transição na saída",
    "Auto Blend": "Blend automático",
    "Compute blend in/out from the overlap with neighbor strips":
        "Calcula blend in/out pela sobreposição com strips vizinhas",
    "Before/After": "Antes/depois",
    "Nothing": "Nada",
    "Outside the strip the part has no effect": "Fora da strip a parte não tem efeito",
    "Hold Forward": "Manter depois",
    "Hold the last pose until the next strip": "Mantém a última pose até a próxima strip",
    "Hold": "Manter antes e depois",
    "Hold the first and last pose (first strip only)": "Mantém a primeira e a última pose (só a 1ª strip)",
    "Blending": "Mistura",
    "Replace": "Substituir",
    "Replace the result of the layers below": "Substitui o resultado das camadas de baixo",
    "Combine": "Combinar",
    "Combine with the layers below (good for layering)": "Combina com as camadas de baixo (ideal para camadas)",
    "Add": "Somar",
    "Add to the layers below": "Soma às camadas de baixo",
    "Subtract": "Subtrair",
    "Subtract from the layers below": "Subtrai das camadas de baixo",
    "Multiply": "Multiplicar",
    "Multiply with the layers below": "Multiplica com as camadas de baixo",
    "Active Part": "Parte ativa",
    "Active Animation": "Animação ativa",
    "Play on Select": "Tocar ao selecionar",
    "Clicking an animation mutes the others so only it plays":
        "Ao clicar numa animação, silencia as outras para ver só ela",
    "Insert": "Inserir",
    "Where to place the part. If the layer is occupied at that frame, the part goes to a layer above "
    "(created automatically if needed)":
        "Onde colocar a parte. Se a camada estiver ocupada nesse frame, a parte vai para uma camada "
        "acima (criada automaticamente se preciso)",
    "Right after the last part of the active layer": "Logo depois da última parte da camada ativa",
    "At the start of the animation (e.g. frame 1), together with the others":
        "No início da animação (ex.: frame 1), junto com as outras",
    "Starting together with the selected part": "Começando junto com a parte selecionada",
    "Current Frame": "Frame atual",
    "At the current frame": "No frame atual",
    "Base Pose (Rest)": "Pose base (repouso)",
    "Keep a track at the bottom of the NLA that returns to rest the channels the active animation "
    "doesn't animate. Prevents bones stuck in another animation's pose":
        "Mantém no fundo do NLA uma track que devolve ao repouso os canais que a animação ativa não "
        "anima. Evita bones presos na pose de outra animação",
    "Record in Animation Context": "Gravar no contexto da animação",
    "When recording a part used in the active animation, record directly on its strip while seeing "
    "the whole animation. Off: the part is recorded isolated (solo)":
        "Ao gravar uma parte usada na animação ativa, grava direto na strip dela, vendo a animação "
        "inteira. Desligado, a parte é gravada isolada (solo)",
    "Default Blending": "Mistura padrão",
    "Blending of newly placed parts (in animations and as loose strips)":
        "Mistura das partes recém-colocadas (nas animações e como strips soltas)",
    "Loose Strips Playing": "Strips soltas tocando",
    "Loose strips are playing (animations muted)": "As strips soltas estão tocando (animações silenciadas)",
    "Only Moving": "Só movimentados",
    "Hide bones whose keys never change value": "Esconde bones cujas keys não mudam de valor",
    "Only Selected": "Só selecionados",
    "List only the bones selected in Pose Mode": "Lista apenas os bones selecionados no Pose Mode",
    "Scale": "Escala",
    "Shape scale (relative to the bone length)": "Escala do shape (relativa ao tamanho do bone)",
    "Step": "Step",
    "Frames between generated keys": "Intervalo entre as keys geradas",
    "Visual Keying (for Export)": "Visual Keying (para exportar)",
    "Record the final pose (with IK, constraints, drivers), useful to export to game engines. Inside "
    "Blender the constraints stay active and act again on top. Off (default): records the channels "
    "and the rig recomputes, identical result in Blender":
        "Grava a pose final (com IK, constraints, drivers), útil para exportar para engines. Dentro do "
        "Blender as constraints continuam ativas e agem de novo por cima. Desligado (padrão), grava os "
        "canais e o rig recalcula: resultado idêntico no Blender",
    "Clean Redundant Keys": "Limpar keys redundantes",
    "Remove keys that don't change the curve": "Remove keys que não mudam a curva",
    "All Bones": "Todos os bones",
    "Include every bone; off: only bones with keys in the parts or moved by the rig":
        "Inclui todos os bones; desligado, só os que têm keys nas partes ou são movidos pelo rig",

    # --- Preferências ----------------------------------------------------------
    "Timeline Controls in the NLA": "Controles de timeline no NLA",
    "Show play, current frame and frame range in the NLA editor header":
        "Mostra play, frame atual e intervalo no header do editor NLA",
    "Recording Indicator in the Viewport": "Indicador de gravação no Viewport",
    "Show in the 3D Viewport header which part the keys will be recorded into":
        "Mostra no header do Viewport 3D em qual parte as keys serão gravadas",
    "Select Tracks in the NLA": "Selecionar tracks no NLA",
    "When bones are selected, select the NLA tracks that have keys of those bones (native NLA highlight)":
        "Ao selecionar bones, seleciona no NLA as tracks que têm keys desses bones (destaque nativo do NLA)",
    "Protect Keyframe Insertion (I Key)": "Proteger inserção de keyframes (tecla I)",
    "In Pose Mode, the I key only inserts keyframes if a part is being recorded. Off: Blender works as usual":
        "No Pose Mode, a tecla I só insere keyframes se houver uma parte em gravação. Desligado, o "
        "Blender funciona como sempre",

    # --- Partes ------------------------------------------------------------------
    "Create a new part (animation clip) and start recording into it":
        "Cria uma parte nova (trecho de animação) e começa a gravar nela",
    "New Part": "Nova Parte",
    "Start Recording": "Começar a gravar",
    "The next keyframes go into this part": "Os próximos keyframes vão para esta parte",
    "Place in Active Animation": "Colocar na animação ativa",
    "Place the part in the active animation right away (using the chosen insert mode) and record while "
    "seeing the whole animation":
        "Já coloca a parte na animação ativa (no modo de inserção escolhido) e grava vendo a animação inteira",
    "Place in '{}'": "Colocar em '{}'",
    "Objects ({}):": "Objetos ({}):",
    "Select the armature (or object) to animate": "Selecione o armature (ou objeto) que vai ser animado",
    "Give the part a name": "Dê um nome para a parte",
    "Part '{}' created in '{}' (frame {:.0f})": "Parte '{}' criada em '{}' (frame {:.0f})",
    "Part '{}' created": "Parte '{}' criada",
    "Record the next keyframes into this part": "Grava os próximos keyframes nesta parte",
    "Record Part": "Gravar Parte",
    "No part selected": "Nenhuma parte selecionada",
    "Recording '{}' {}": "Gravando '{}' {}",
    "in the context of '{}'": "no contexto de '{}'",
    "isolated": "isolada",
    "Stop recording: remove the temporary track and update the animations that use the part":
        "Para a gravação: remove a track temporária e ajusta as animações que usam a parte",
    "Stop Recording": "Parar Gravação",
    "Duplicate the active part (to make a variation)": "Duplica a parte ativa (para criar uma variação)",
    "Duplicate Part": "Duplicar Parte",
    "No active part": "Nenhuma parte ativa",
    "Remove the active part from the library": "Remove a parte ativa da biblioteca",
    "Remove Part": "Remover Parte",
    "Also Remove from Animations": "Remover também das animações",
    "Delete this part's strips in the animations; off: cancel if the part is in use":
        "Apaga as strips desta parte nas animações; desligado, cancela se ela estiver em uso",
    "Delete the Action": "Apagar a Action",
    "Delete the data; off: the Action stays in the file (with Fake User)":
        "Apaga os dados; desligado, a Action fica no arquivo (com Fake User)",
    "'{}' is used in {} strip(s)": "'{}' é usada em {} strip(s)",
    "'{}' is used in {} strip(s). Check 'Also Remove from Animations'":
        "'{}' é usada em {} strip(s). Marque 'Remover também das animações'",
    "Use the active part's range (first to last key) as the Preview Range":
        "Usa o intervalo da parte ativa (1ª à última key) como Preview Range",
    "Part Range": "Intervalo da Parte",
    "Click: select the part. Double-click: add it to the NLA as a loose strip at the current frame":
        "Clique: seleciona a parte. Duplo clique: adiciona no NLA como strip solta no frame atual",
    "Select Part": "Selecionar Parte",
    "Add the active part to the NLA as a loose strip at the current frame (same as double-clicking it)":
        "Adiciona a parte ativa no NLA como strip solta no frame atual (o mesmo que o duplo clique)",
    "Add as Loose Strip": "Adicionar como Strip Solta",
    "Play all loose strips together (mutes the animations). Click again to go back to the active animation":
        "Toca todas as strips soltas juntas (silencia as animações). Clique de novo para voltar à animação ativa",
    "Play Loose Strips": "Tocar Strips Soltas",
    "Remove this loose strip (the part stays in the library)": "Remove esta strip solta (a parte continua na biblioteca)",
    "Remove Loose Strip": "Remover Strip Solta",
    "Remove all loose strips (the parts stay in the library)": "Remove todas as strips soltas (as partes continuam na biblioteca)",
    "Clear Loose Strips": "Limpar Strips Soltas",
    "'{}' added as a loose strip at frame {:.0f}": "'{}' adicionada como strip solta no frame {:.0f}",
    "There are no loose strips. Double-click a part to add one":
        "Não há strips soltas. Dê um duplo clique numa parte para adicionar",
    "Loose strip not found": "Strip solta não encontrada",
    "{} loose strip(s) removed": "{} strip(s) solta(s) removida(s)",
    "Organize what already exists in the file: strip Actions become Parts and stray tracks become Animations":
        "Organiza o que já existe no arquivo: Actions das strips viram Partes e tracks soltas viram Animações",
    "Import from NLA": "Importar do NLA",
    "Convert Tracks to Animations": "Converter tracks em animações",
    "Each track that doesn't belong to an animation becomes an animation with a 'Base' layer":
        "Cada track que não pertence a uma animação vira uma animação com camada 'Base'",
    "{} part(s) and {} animation(s) imported": "{} parte(s) e {} animação(ões) importadas",
    "{} v1.0 animation(s) converted": "{} animação(ões) da v1.0 convertidas",
    "Select this bone (Shift: add to the selection)": "Seleciona este bone (Shift: adiciona à seleção)",
    "Select Bone": "Selecionar Bone",
    "Invalid armature": "Armature inválido",
    "Put '{}' in Pose Mode to select bones": "Coloque '{}' em Pose Mode para selecionar bones",
    "Bone '{}' doesn't exist": "Bone '{}' não existe",
    "Insert a keyframe only if a part is being recorded (optional protection of the I key)":
        "Insere keyframe apenas se houver uma parte em gravação (proteção opcional da tecla I)",
    "Insert Keyframe (with Target Part)": "Inserir Keyframe (com Parte Alvo)",
    "No part is being recorded: create a part or click ● Record":
        "Nenhuma parte em gravação: crie uma parte ou clique em ● Gravar",

    # --- Animações ---------------------------------------------------------------
    "Create a full animation (e.g. \"Jump\") from one or more parts":
        "Cria uma animação completa (ex.: \"Pular\") a partir de uma ou mais partes",
    "New Animation": "Nova Animação",
    "Parts that go into the animation": "Partes que entram na animação",
    "Arrange": "Organizar",
    "In Sequence": "Em sequência",
    "One after the other on the same layer": "Uma depois da outra na mesma camada",
    "All starting at the same frame, each on its own layer": "Todas começando no mesmo frame, cada uma na sua camada",
    "Empty library: the animation starts without parts": "Biblioteca vazia: a animação começa sem partes",
    "Parts (in library order):": "Partes (na ordem da biblioteca):",
    "Give the animation a name": "Dê um nome para a animação",
    "Select the objects of the animation": "Selecione os objetos da animação",
    "Animation '{}' created with {} part(s)": "Animação '{}' criada com {} parte(s)",
    "No active animation": "Nenhuma animação ativa",
    "'{}' has no layer selected": "'{}' não tem camada selecionada",
    "Remove the active animation (the parts stay in the library)":
        "Remove a animação ativa (as partes continuam na biblioteca)",
    "Remove Animation": "Remover Animação",
    "Duplicate the active animation (same parts, layers and options)":
        "Duplica a animação ativa (mesmas partes, camadas e opções)",
    "Duplicate Animation": "Duplicar Animação",
    "Play this animation: mute the others and use its frame range":
        "Toca esta animação: silencia as outras e usa o intervalo dela",
    "Play Animation": "Tocar Animação",
    "Set Frame Range": "Ajustar intervalo",
    "'{}' has the stray Action '{}' playing on top of the NLA": "'{}' tem a Action solta '{}' tocando por cima do NLA",
    "Add the selected objects to the animation (creates the layer tracks)":
        "Adiciona os objetos selecionados à animação (cria as tracks das camadas)",
    "Add Objects": "Adicionar Objetos",
    "Select the objects": "Selecione os objetos",
    "Add a layer on top (e.g. an arm waving over a walk)": "Adiciona uma camada por cima (ex.: braço acenando sobre o andar)",
    "New Layer": "Nova Camada",
    "Remove the active layer and the parts placed on it": "Remove a camada ativa e as partes colocadas nela",
    "Remove Layer": "Remover Camada",
    "The animation needs at least one layer": "A animação precisa de ao menos uma camada",
    "Change the layer order (upper layers override the ones below)":
        "Muda a ordem da camada (camadas de cima se sobrepõem às de baixo)",
    "Move Layer": "Mover Camada",
    "Place a part on the active layer of the animation": "Coloca uma parte na camada ativa da animação",
    "Add Part": "Adicionar Parte",
    "Choose a part from the library": "Escolha uma parte da biblioteca",
    "Layer occupied: '{}' went to '{}'": "Camada ocupada: '{}' foi para '{}'",
    "Select this part to edit its options": "Seleciona esta parte para editar as opções dela",
    "Select Animation Part": "Selecionar Parte da Animação",
    "Strip not found (was it moved in the NLA?)": "Strip não encontrada (foi movida no NLA?)",
    "Take the selected part out of the animation (the part stays in the library)":
        "Tira a parte selecionada da animação (a parte continua na biblioteca)",
    "Remove from Animation": "Remover da Animação",
    "No part selected in the animation": "Nenhuma parte selecionada na animação",
    "Repeat the selected part at the end of the layer (with the same options)":
        "Repete a parte selecionada no fim da camada (com as mesmas opções)",
    "Duplicate at End": "Duplicar no Fim",
    "Swap the selected part with its neighbor": "Troca a parte selecionada de lugar com a vizinha",
    "Move Part": "Mover Parte",
    "The part is already at the end of the layer": "A parte já está na ponta da camada",
    "Pack the layer's parts one after the other (removes gaps and overlaps)":
        "Encosta as partes da camada uma após a outra (remove buracos e sobreposições)",
    "Pack in Sequence": "Organizar em Sequência",
    "Gap Between Parts": "Espaço entre partes",
    "Update the base pose (rest) of every animated object": "Atualiza a pose base (repouso) de todos os objetos animados",
    "Update Base Pose": "Atualizar Pose Base",
    "Rebuild from Scratch": "Recriar do zero",
    "Delete and recreate the rest values (use it if you changed the bones' rotation mode)":
        "Apaga e recria os valores de repouso (use se mudou o rotation mode dos bones)",
    "Turn on the 'Base Pose' option first": "Ligue a opção 'Pose base' primeiro",
    "Influence restored to 1.0 on: {}": "Influência 1.0 devolvida a: {}",
    "Base pose updated on {} object(s)": "Pose base atualizada em {} objeto(s)",

    # --- Canais -------------------------------------------------------------------
    "Copy the channels (keys) of the selected bones in the active part":
        "Copia os canais (keys) dos bones selecionados na parte ativa",
    "Copy Channels": "Copiar Canais",
    "Paste the copied channels into the active part, on the active object":
        "Cola os canais copiados na parte ativa, no objeto ativo",
    "Paste Channels": "Colar Canais",
    "Copy or move the channels of the selected bones to another part":
        "Copia ou move os canais dos bones selecionados para outra parte",
    "Send Channels to Part": "Enviar Canais para Parte",
    "Delete the channels of the selected bones from the active part":
        "Apaga da parte ativa os canais dos bones selecionados",
    "Delete Channels": "Apagar Canais",
    "Use every channel of the object, not only those of the selected bones":
        "Usa todos os canais do objeto, não só os dos bones selecionados",
    "Replace the existing keys; off: merge with them": "Substitui as keys existentes; desligado, mescla com elas",
    "At Current Frame": "No frame atual",
    "Offset the keys so they start at the current frame": "Desloca as keys para começarem no frame atual",
    "Move (Remove from Source)": "Mover (remove da origem)",
    "Replace Keys in Target": "Substituir keys no destino",
    "No active object": "Nenhum objeto ativo",
    "No bone selected (or check 'All Bones')": "Nenhum bone selecionado (ou marque 'Todos os bones')",
    "{} channel(s) moved to '{}'": "{} canal(is) movido(s) para '{}'",
    "{} channel(s) copied to '{}'": "{} canal(is) copiado(s) para '{}'",
    "There are no keys to copy": "Não há keys para copiar",
    "Choose a target part": "Escolha uma parte de destino",
    "Choose a target part different from the source": "Escolha uma parte de destino diferente da origem",
    "There are no keys to send": "Não há keys para enviar",
    "There are no keys to delete": "Não há keys para apagar",
    "'{}' has no animation in part '{}'": "'{}' não tem animação na parte '{}'",
    "{} channel(s) copied from '{}'": "{} canal(is) copiado(s) de '{}'",
    "{} channel(s) pasted into '{}'": "{} canal(is) colado(s) em '{}'",
    "{} channel(s) deleted from '{}'": "{} canal(is) apagado(s) de '{}'",
    "(none)": "(nenhuma)",

    # --- Bake ----------------------------------------------------------------------
    "Bake the checked animations (each one becomes a Part + a \"[bake]\" Animation)":
        "Faz o bake das animações marcadas (cada uma vira Parte + Animação \"[bake]\")",
    "Bake Animations": "Bake das Animações",
    "Check or uncheck every animation for the bake": "Marca ou desmarca todas as animações para o bake",
    "Toggle All": "Marcar Todas",
    "Bake finished: {}": "Bake concluído: {}",
    "'{}' has no parts placed": "'{}' não tem nenhuma parte colocada",
    "'{}' has no keys to bake": "'{}' não tem keys para fazer bake",
    "Write a scene report (NLA, base pose, constraints, shapes) to help find problems":
        "Gera um relatório da cena (NLA, pose base, constraints, shapes) para encontrar problemas",
    "Diagnostics saved to {}": "Diagnóstico salvo em {}",

    # --- Shapes --------------------------------------------------------------------
    "Replace the custom shape of the selected bones": "Substitui o shape (custom shape) dos bones selecionados",
    "Replace Shape": "Substituir Shape",
    "Remove the custom shape of the selected bones (back to the default drawing)":
        "Remove o custom shape dos bones selecionados (volta ao desenho padrão)",
    "Remove Shape": "Remover Shape",
    "Adjust the shape scale of the selected bones without changing the shape":
        "Ajusta a escala do shape dos bones selecionados, sem trocar o shape",
    "Shape Scale": "Escala do Shape",
    "Copy the shape look of the active bone to the other selected bones":
        "Copia a aparência do shape do bone ativo para os outros bones selecionados",
    "Apply to Selected": "Aplicar nos Selecionados",
    "Reset size, offset, rotation, line and color of the selected bones (keeps the shape)":
        "Volta tamanho, offset, rotação, linha e cor dos bones selecionados ao padrão (mantém o shape)",
    "Reset Look": "Resetar Aparência",
    "Shape": "Shape",
    "Shape scale (multiplied by the bone length)": "Escala do shape (multiplicada pelo tamanho do bone)",
    "Only Active Bone": "Só o bone ativo",
    "Apply only to the active bone instead of every selected bone":
        "Aplica apenas ao bone ativo em vez de todos os selecionados",
    "Display as Wireframe": "Exibir como wireframe",
    "Always draw the bone as wireframe (recommended for line shapes)":
        "Desenha o bone sempre em wireframe (recomendado para shapes de linha)",
    "The object used as the shape": "O objeto usado como shape",
    "Size/Offset/Rotation": "Tamanho/Offset/Rotação",
    "Shape scale, translation and rotation": "Escala, translação e rotação do shape",
    "Color": "Cor",
    "Palette and custom colors": "Paleta e cores personalizadas",
    "Line": "Linha",
    "Wire width, wireframe and bone size usage": "Espessura, wireframe e uso do tamanho do bone",
    "Select an armature": "Selecione um armature",
    "Enter Pose Mode to change shapes": "Entre no Pose Mode para trocar shapes",
    "No bone selected": "Nenhum bone selecionado",
    "Bones of a linked armature cannot be changed": "Bones de armature linkado não podem ser alterados",
    "Select other bones besides the active one": "Selecione outros bones além do ativo",
    "Shape '{}' applied to {} bone(s)": "Shape '{}' aplicado em {} bone(s)",
    "Shape removed from {} bone(s)": "Shape removido de {} bone(s)",
    "Look copied to {} bone(s)": "Aparência copiada para {} bone(s)",
    "Circle": "Círculo",
    "Circle around the bone": "Círculo em volta do bone",
    "Semicircle": "Semicírculo",
    "Half circle (e.g. eyebrows, eyelids)": "Meio círculo (ex.: sobrancelhas, pálpebras)",
    "Square": "Quadrado",
    "Square around the bone": "Quadrado em volta do bone",
    "Diamond": "Losango",
    "Diamond around the bone": "Losango em volta do bone",
    "Hexagon": "Hexágono",
    "Hexagon around the bone": "Hexágono em volta do bone",
    "Triangle": "Triângulo",
    "Triangle around the bone": "Triângulo em volta do bone",
    "Sphere": "Esfera",
    "Three orthogonal circles": "Três círculos ortogonais",
    "Cube": "Cubo",
    "Wireframe cube": "Cubo em wireframe",
    "Pyramid": "Pirâmide",
    "Pyramid pointing along the bone": "Pirâmide apontando ao longo do bone",
    "Arrow": "Seta",
    "Arrow along the bone": "Seta ao longo do bone",
    "Double Arrow": "Seta dupla",
    "Arrow with two heads": "Seta com duas pontas",
    "Four Arrows": "Quatro setas",
    "Cross with arrows (move/root control)": "Cruz com setas (controle de movimento/root)",
    "Cross": "Cruz",
    "Simple cross": "Cruz simples",
    "Circle with a cross (IK target / eyes)": "Círculo com cruz (alvo de IK / olhos)",
    "Rotate": "Rotação",
    "Arc with arrows (rotation control)": "Arco com setas (controle de rotação)",
    "Line along the bone": "Linha ao longo do bone",
    "Size": "Tamanho",
    "Offset": "Offset",
    "Rotation": "Rotação",
    "Scale to Bone Length": "Escalar pelo bone",
    "Wire Width": "Espessura da linha",
    "Wireframe": "Wireframe",
    "Follow Bone": "Seguir bone",
    "Normal": "Normal",
    "Selected": "Selecionado",
    "Active": "Ativo",

    # --- Painéis e cabeçalho -------------------------------------------------------
    "Animated Bones": "Bones Animados",
    "Composition": "Composição",
    "Part Options": "Opções da Parte",
    "Bone Shapes": "Shapes de Bones",
    "Customize Shape": "Personalizar Shape",
    "Rig cycle: '{}' is a child of '{}'": "Ciclo no rig: '{}' é filho de '{}'",
    "(part of the IK chain of '{}'). The pose will 'jump'.": "(parte da cadeia do IK de '{}'). A pose vai 'saltar'.",
    "Fix it: Edit Mode › select the target › Alt+P › Clear Parent":
        "Corrija: Edit Mode › selecione o alvo › Alt+P › Clear Parent",
    "Recording part: {}": "Gravando parte: {}",
    "'{}' is not in this part": "'{}' não está nesta parte",
    "In the context of '{}' (seeing the animation)": "No contexto de '{}' (vendo a animação)",
    "Isolated (solo): only this part plays": "Isolada (solo): só esta parte toca",
    "Editing strip '{}' (NLA tweak)": "Editando strip '{}' (tweak do NLA)",
    "Exit Tweak": "Sair do Tweak",
    "Keys go to the stray Action '{}'": "Keys vão para a Action solta '{}'",
    "No part is being recorded": "Nenhuma parte em gravação",
    "Create a part or click ● on a part": "Crie uma parte ou clique em ● numa parte",
    "{}: keys in {} part(s)": "{}: keys em {} parte(s)",
    "Double-click a part: add it as a loose strip": "Duplo clique numa parte: adiciona como strip solta",
    "Loose Strips ({})": "Strips Soltas ({})",
    "Double-click a part to add one here": "Dê um duplo clique numa parte para adicionar aqui",
    "... and {} more": "... e mais {}",
    "Create a part with +": "Crie uma parte com +",
    "Used in {} strip(s)": "Usada em {} strip(s)",
    "{} ({} bones)": "{} ({} bones)",
    "Loc": "Loc",
    "Rot": "Rot",
    "BBone": "BBone",
    "Prop": "Prop",
    "No bone with keys in this part": "Nenhum bone com keys nesta parte",
    "Channels of the selected bones:": "Canais dos bones selecionados:",
    "Layers (top to bottom):": "Camadas (de cima para baixo):",
    "Parts in '{}':": "Partes em '{}':",
    "No parts. Add one below.": "Nenhuma parte. Adicione abaixo.",
    "Insert part:": "Inserir parte:",
    "No parts in the library": "Nenhuma parte na biblioteca",
    "Choose the part to place on the active layer": "Escolha a parte para colocar na camada ativa",
    "Shape library for the selected bones": "Biblioteca de shapes para os bones selecionados",
    "Part not found (changed in the NLA?)": "Parte não encontrada (alterada no NLA?)",
    "{}  ({} object(s))": "{}  ({} objeto(s))",
    "End: {:.1f}   ·   length {:.1f}": "Fim: {:.1f}   ·   duração {:.1f}",
    "Layer with 'Hold Pose' (pin in the layer list)": "Camada com 'Segurar pose' (alfinete na lista de camadas)",
    "Animations to bake:": "Animações para o bake:",
    "Inside Blender, the constraints act again on top": "No Blender, as constraints agem de novo por cima",
    "{}: frames {:.0f}–{:.0f}": "{}: frames {:.0f}–{:.0f}",
    "{}: empty": "{}: vazia",
    "{} bones": "{} bones",
    "Bake ({} animation(s))": "Bake ({} animação(ões))",
    "Result: new Part + '[bake]' Animation": "Resultado: nova Parte + Animação '[bake]'",
    "{} bone(s) selected": "{} bone(s) selecionado(s)",
    "No active bone": "Nenhum bone ativo",
    "Active bone: {}": "Bone ativo: {}",
    "Recording: {}": "Gravando: {}",
    "Recording: {} (solo)": "Gravando: {} (solo)",
    "No part being recorded": "Sem parte em gravação",

    # --- Mensagens dos utilitários -------------------------------------------------
    "Select the armature (or object) that will receive the keys":
        "Selecione o armature (ou objeto) que vai receber as keys",
    "Track '{}' of '{}' has no strip with an Action": "A track '{}' de '{}' não tem strip com Action",
    "Could not enter tweak mode on '{}'": "Não foi possível entrar no modo tweak em '{}'",
    "Linked objects cannot be edited: {}": "Objetos linkados não podem ser editados: {}",
    "A track named '{}' already exists on '{}'": "Já existe uma track chamada '{}' em '{}'",
    "No room at frame {} of layer '{}' on '{}'. Use 'After' or move the other parts":
        "Não há espaço no frame {} da camada '{}' em '{}'. Use 'Depois' ou mova as outras partes",
    "No selected object has animation in part '{}'": "Nenhum objeto da seleção tem animação na parte '{}'",
}

# Contextos usados pelo Blender: "*" (padrão: rótulos, propriedades,
# descrições) e "Operator" (nomes de operadores e botões de operador).
_CONTEXTOS = ("*", "Operator")


def _dicionario():
    pt = {(ctx, en): tr for en, tr in PT_BR.items() for ctx in _CONTEXTOS}
    return {"pt_BR": pt, "pt_PT": pt, "pt": pt}


def register():
    _translations.register(__package__, _dicionario())


def unregister():
    _translations.unregister(__package__)
