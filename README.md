# Anim Flow 1.7 — Blender 4.4+

Fluxo de animação em dois níveis:

| | **Parte** | **Animação** |
|---|---|---|
| O que é | Um trecho gravado ("Impulso", "Aterrissar") | A animação completa composta de partes ("Pular") |
| No Blender | Action com slots, guardada numa biblioteca (Fake User) | Tracks NLA `"<Animação> › <Camada>"` com strips das partes |
| Você faz | Grava os keyframes | Organiza, repete, inverte, mistura e ajusta o tempo |
| Bake | — | ✅ |

## Estrutura

```
anim_flow/
├── __init__.py, blender_manifest.toml
├── properties.py        # partes, animações, camadas, proxy da strip, opções
├── preferences.py       # preferências + atalho opcional da tecla I
├── handlers.py          # destaque automático + migração da v1.0
├── utils/
│   ├── compat.py        # Actions em camadas, slots, channelbags, seleção de bones
│   ├── nla.py           # gravação de partes, camadas, strips, reorganização
│   ├── shapes.py        # biblioteca de 16 widgets
│   └── bake.py          # bake de animações
├── operators/
│   ├── parts_ops.py     # nova/gravar/parar/duplicar/remover parte, importar
│   ├── anims_ops.py     # animações, camadas, colocar/mover/encostar partes
│   ├── track_ops.py     # copiar/colar/enviar/apagar canais de bones
│   ├── bake_ops.py      # bake das animações marcadas
│   └── shapes_ops.py    # substituir/remover shape, copiar aparência, resetar
└── ui/
    ├── lists.py, menus.py, nla_header.py
    └── nla_panels.py    # seletor Partes | Animações | Bake, painéis do Viewport
```

## Instalação
*Edit › Preferences › Get Extensions › ˅ › Install from Disk…* e escolha o `anim_flow-1.7.0.zip`.
Se uma versão anterior estiver instalada, o zip novo a substitui.
Arquivos feitos na 1.0 são convertidos sozinhos ao abrir: cada animação antiga vira Parte + Animação.

## Idiomas
A interface é escrita em **inglês** e traduzida para **português** pelo sistema nativo do Blender.
Para usar em português: *Edit › Preferences › Interface › Translation*, escolha o idioma
"Português (Brasil)" e marque **Interface**, **Tooltips** e **Reports**. Com o Blender em inglês,
o add-on aparece em inglês. As traduções ficam em `i18n.py`.

## Strips soltas (Loose Strips)
* **Duplo clique** numa parte da lista coloca uma strip dela no NLA, no frame atual, numa track
  `◇ Loose N`, fora das animações. O nome da parte agora é editado no campo abaixo da lista.
* Várias soltas **tocam juntas**. Se a track já estiver ocupada naquele frame, a nova vai para outra track.
* No modo Partes, a caixa **Loose Strips** lista as soltas: ▶ toca as soltas (silencia as animações),
  🗑 limpa todas, e o X de cada linha remove uma. Tocar uma animação silencia as soltas.
* O botão **Loose** ao lado de Gravar faz o mesmo que o duplo clique.
* **Mistura padrão:** as partes novas (nas animações e soltas) usam **Combinar** por padrão.
  Isso pode ser mudado em *Default Blending*, nos modos Partes e Animações.

## Uso

O NLA tem a aba **N › Anim Flow**, com o seletor **Partes | Animações | Bake** no topo.
Logo abaixo fica sempre o indicador de gravação (para onde vão os keyframes).

### 1. Partes
* **+** cria uma parte e já começa a gravar. Se houver uma animação ativa, a parte já entra
  nela (no modo de inserção escolhido) e você grava **vendo a animação inteira**.
* **Gravar no contexto** (ligado por padrão): ao clicar ● numa parte usada na animação ativa,
  a gravação acontece na própria strip dela, com as outras camadas tocando. Clicando a partir
  do NLA, até as camadas de cima continuam tocando.
* Desligado (ou parte fora da animação ativa): grava **isolada**, numa track temporária
  **"✎ Nome"** em *solo*.
* O destaque mostra em vermelho, com o ícone de osso e a contagem, as partes que têm keys dos
  bones selecionados. O quadro de gravação mostra quais bones estão selecionados.
* **● / Parar** (na lista, no painel ou no header do NLA). Ao parar, a track temporária some
  e todas as animações que usam a parte se ajustam ao novo tamanho.
* A parte vai do **primeiro ao último keyframe**.
* **Bones Animados** mostra quem se mexe na parte (Loc · Rot · Esc). Os canais dos bones
  selecionados podem ser copiados, colados, enviados para outra parte ou apagados.
* **Importar** organiza o que já existe no arquivo: Actions das strips viram partes e
  tracks soltas viram animações.

### 2. Animações
* **+** cria a animação (ex.: "Pular") escolhendo uma ou mais partes, **em sequência** ou
  **juntas** (todas no mesmo frame, cada uma na sua camada).
* Clicar numa animação a **toca** (silencia as outras). **▶** também ajusta o preview range.
* **Composição:**
  * **Camadas:** a de cima se sobrepõe à de baixo. Por padrão todas usam *Substituir*: cada
    parte manda só nos bones que ela anima, então pernas + braços tocam juntos. Mute por camada.
  * **Segurar pose** (alfinete na lista de camadas, ligado por padrão): cada parte segura a
    última pose até a próxima e, na camada base, a primeira segura a pose antes do início.
    Assim nada volta ao repouso fora das partes. Desligue numa camada de sobreposição
    (ex.: aceno sobre o andar) para ela "soltar" de volta à camada de baixo quando acabar.
  * **Partes da camada**, em ordem de tempo. Clique numa para editá-la.
    ◀ ▶ trocam de lugar com a vizinha, ⧉ repete no fim, ✕ remove, **Encostar** cola
    uma após a outra.
  * **Adicionar Parte**, com modo de inserção: **Depois** (fim da camada), **Início** (frame
    inicial da animação), **Junto** (mesmo início da parte selecionada) ou **Frame atual**.
    Se a camada estiver ocupada, a parte vai sozinha para uma camada acima, que é criada se preciso.
  * Partes com keys dos bones selecionados ficam em vermelho na composição.
* **Opções da Parte:** início, repetir, velocidade (escala), inverter, mistura, antes/depois
  (Nada / Manter depois / Manter antes e depois), blend in/out ou automático.
  Valem para a strip em todos os objetos da animação.

### Pose base
O Blender não reseta canais que nenhuma track ativa anima. Um bone animado só em outra animação
ficaria "preso" na pose dela, e o resultado mudaria conforme o frame em que você estava antes.
A track **"· Pose base"**, no fundo do NLA de cada objeto, segura todo canal animado no valor de
repouso, e as animações substituem esse valor por cima. Ela é criada e atualizada sozinha.
O botão ⟳ ao lado da opção atualiza (ou recria, se você mudou o rotation mode dos bones).
Bones que nunca foram animados continuam livres para posar à mão.

### 3. Bake
* Marque as **animações** na lista. A caixa abaixo mostra o que entra
  (objetos, quantidade de bones, intervalo).
* Opções: step, visual keying, limpar keys redundantes, todos os bones
  (desligado = bones com keys + bones movidos pelo rig: com constraints, da cadeia de IK/Spline IK
  e com drivers).
* **O bake nunca altera o rig.** Por padrão (sem Visual Keying), ele grava os canais (FK, alvos
  de IK...) e o rig recalcula IK e constraints ao tocar, com resultado idêntico no Blender.
* **Visual Keying (para exportar):** grava a pose final, útil para engines. Dentro do Blender,
  as constraints continuam ativas e agem de novo por cima.
* As versões 1.3 a 1.5 zeravam a influência de constraints (ex.: IK desligado). Ao abrir o
  arquivo, o add-on remove essas keys e devolve influência 1.0 às constraints afetadas.
* Cada animação gera uma Parte **"<nome>_bake"** e uma Animação **"<nome> [bake]"**.

### Shapes (Viewport, Pose Mode)
* Clique direito › **Substituir Shape**, ou *N › Anim Flow › Shapes de Bones*.
* **Personalizar Shape** (bone ativo): shape, tamanho XYZ, offset, rotação, escalar pelo bone,
  espessura da linha, wireframe, seguir outro bone e cor (paleta do tema ou personalizada).
* **Aplicar nos Selecionados** copia a aparência do bone ativo. **Resetar** volta ao padrão
  e mantém o shape.

## Limitações conhecidas
* **Sem drag & drop:** as listas do Blender não suportam arrastar, então a ordem muda pelos botões.
* **NLA nativo sem filtro nem cores:** o destaque seleciona as tracks no NLA.
* **Strips movidas à mão no NLA:** mover uma strip direto no NLA pode tirá-la da seleção do
  painel. Clique nela de novo na lista.
* **Mudar o início pelo painel** respeita as vizinhas (o NLA não deixa sobrepor).
  Use **Encostar** ou ◀ ▶ para reorganizar.
* **Mover/encostar recria a track** da camada. Influência animada e F-Modifiers de strip
  não são copiados.
* **Uma parte em gravação por vez.**
* **Gravando no contexto:** é o modo tweak nativo, então as outras partes da MESMA camada não
  tocam durante a gravação. As camadas de cima só tocam se a gravação for iniciada pelo painel
  do NLA (o Blender não expõe essa opção na API de dados).
* **Partes com Repetir/Inverter:** gravar no contexto mapeia o tempo pela strip; para edições
  grandes nessas partes, prefira gravar isolada.
* **Proteção da tecla I** é opcional e não cobre auto-key.
* **Testes:** testado em background no Blender 5.2 (lógica completa + desenho da UI com
  layout simulado). As APIs foram conferidas contra o código do 4.4, sem execução real no 4.4/4.5.

* **Pose base:** segura só transformações e B-Bone. Influências de constraints e propriedades
  custom (ex.: switch IK/FK) ficam de fora: o add-on não mexe nesses valores do rig.

### Avisos do rig
O painel avisa quando o **alvo (ou pole) de um IK é filho de um bone da própria cadeia**. Isso cria um
ciclo de dependência: a pose de um frame passa a depender de onde você veio na timeline (saltos que
aparecem "às vezes"), e o bake copia esse comportamento. Corrija no Edit Mode com Alt+P › Clear Parent.
Ao tocar uma animação (▶), uma parte que tenha ficado como Action ativa solta por cima do NLA é retirada.

### Diagnóstico
O botão **Diagnóstico**, no topo do painel do NLA, salva em `Documentsnim_flow_diagnostico.txt` um
relatório da cena: pilha NLA, valores da pose base, constraints e ajustes de shape.

## Próximos passos
* Máscara de bones por camada (ex.: camada que só afeta o braço).
* Influência por camada com curva.
* Pré-visualização dos shapes e importação de widgets próprios.
* Exportação direta (FBX/glTF) das animações após o bake.
