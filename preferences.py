"""
Preferências do add-on e atalhos de teclado.
"""

import bpy
from bpy.props import BoolProperty

# Atalhos registrados pelo add-on (removidos no unregister).
_keymaps = []


def get_prefs(context=None):
    context = context or bpy.context
    addon = context.preferences.addons.get(__package__)
    return addon.preferences if addon else None


def _on_guard_toggle(self, _context):
    for _km, kmi in _keymaps:
        if kmi.idname == "animflow.insert_keyframe":
            kmi.active = self.guard_keyframes


class ANIMFLOW_AP_preferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    timeline_in_nla: BoolProperty(
        name="Timeline Controls in the NLA",
        description="Show play, current frame and frame range in the NLA editor header",
        default=True,
    )
    record_in_viewport: BoolProperty(
        name="Recording Indicator in the Viewport",
        description="Show in the 3D Viewport header which part the keys will be recorded into",
        default=True,
    )
    sync_nla_selection: BoolProperty(
        name="Select Tracks in the NLA",
        description=(
            "When bones are selected, select the NLA tracks that have keys of those bones "
            "(native NLA highlight)"
        ),
        default=True,
    )
    guard_keyframes: BoolProperty(
        name="Protect Keyframe Insertion (I Key)",
        description=(
            "In Pose Mode, the I key only inserts keyframes if a part is being recorded. "
            "Off: Blender works as usual"
        ),
        default=False,
        update=_on_guard_toggle,
    )

    def draw(self, _context):
        layout = self.layout
        col = layout.column()
        col.prop(self, "timeline_in_nla")
        col.prop(self, "record_in_viewport")
        col.prop(self, "sync_nla_selection")
        col.prop(self, "guard_keyframes")


def register_keymaps():
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc is None:  # Blender em modo background.
        return
    km = kc.keymaps.new(name="Pose", space_type='EMPTY')
    kmi = km.keymap_items.new("animflow.insert_keyframe", 'I', 'PRESS')
    prefs = get_prefs()
    kmi.active = bool(prefs and prefs.guard_keyframes)
    _keymaps.append((km, kmi))


def unregister_keymaps():
    for km, kmi in _keymaps:
        km.keymap_items.remove(kmi)
    _keymaps.clear()


def register():
    bpy.utils.register_class(ANIMFLOW_AP_preferences)
    register_keymaps()


def unregister():
    unregister_keymaps()
    bpy.utils.unregister_class(ANIMFLOW_AP_preferences)
