bl_info = {
    "name": "Python Module Manager (PIP)",
    "author": "ambi",
    "version": (1, 0, 7),
    "blender": (2, 80, 0),
    "location": "Here",
    "description": "Manage Python modules inside Blender with PIP",
    "warning": "",
    "wiki_url": "",
    "support": "COMMUNITY",
    "tracker_url": "https://github.com/amb/blender_pip/issues",
    "category": "Development",
}

__version__ = ".".join(map(str, bl_info["version"]))

#   how-to-uninstall-a-package-installed-with-pip-install-user/56948334#56948334
import sys
import subprocess
import bpy
from pathlib import Path
import os


if bpy.app.version < (2, 91, 0):
    python_bin = bpy.app.binary_path_python
else:
    python_bin = sys.executable

TEXT_OUTPUT = []
ERROR_OUTPUT = []


def create_pth_startup_file(startup_path, pth_path):
    """
    Creates a file in Blender's startup scripts folder,
    that adds a path to sitedirs to process .pth files on Blender startup.
    startup_path: the path where to create the startup file
    pth_path: the path to add to site packages on startup
    """
    startup_path = Path(startup_path)
    startup_path.mkdir(parents=True, exist_ok=True)  # startup folder might not exist
    file_path = startup_path / "blender_pth_startup.py"

    # TODO read in a text file of paths, or a .pth file
    # so we can add multiple paths in there.
    if not file_path.exists():
        with open(file_path, "w") as f:
            text = f"""
# ======== this file was generated by the blender_pip addon ========
# it enables support for editable pip installs to the modules folder

import site
site.addsitedir(r'{pth_path}')

def register():  # empty method to prevent warning on Blender startup
    pass
"""
            f.write(text)

    import site
    site.addsitedir(pth_path)


def run_pip_command(self, *cmds, cols=False, run_module="pip"):
    """Run PIP process with user spec commands"""
    global ERROR_OUTPUT
    global TEXT_OUTPUT

    cmds = [c for c in cmds if c is not None]
    
    # copy the sys.paths to PYTHONPATH to pass to subprocess, for pip to use
    paths = os.environ.get("PYTHONPATH", "").split(os.pathsep)
    new_paths = [p for p in sys.path if p not in paths]
    paths += new_paths
    joined_paths = os.pathsep.join(paths)
    if joined_paths:
        os.environ["PYTHONPATH"] = joined_paths

    # TODO: make this function only run pip commands, make separate function to run other modules
    # Choose where to save Python modules
    # if bpy.context.scene.pip_modules_home and MODULES_FOLDER.exists() and run_module == "pip":
    #     cmds = ["--root", MODULES_FOLDER] + cmds
    #     command = [python_bin, "-m", run_module, *cmds]
    # else:
    #     command = [python_bin, "-m", run_module, *cmds]
    command = [python_bin, "-m", run_module, *cmds]

    print(command)
    output = subprocess.run(
        command, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    if output.stderr:
        if "WARNING" not in output.stderr[:20]:
            # Don't display error popup when PIP complains it's not the latest and greatest
            self.report({"ERROR"}, "Error happened. Check console")
        print(">>> ERROR")
        print(output.returncode)
        print(output.stderr)
        ERROR_OUTPUT = save_text(output.stderr)
    else:
        ERROR_OUTPUT = []

    if output.stdout:
        TEXT_OUTPUT = save_text(output.stdout, cols=cols)
    else:
        TEXT_OUTPUT = []


def save_text(text, cols=False):
    """Parse input text string into a 2D list"""
    out = []
    for i in text.split("\n"):
        if len(i) <= 1:
            continue
        subs = i.split()
        parts = []
        if cols:
            for s in subs:
                parts.append(s)
        else:
            parts.append(" ".join(subs))
        out.append(parts)
    return out


class PMM_OT_PIPCommand(bpy.types.Operator):
    bl_idname = "pmm.pip_command"
    bl_label = "Run a pip command"
    bl_description = "run a pip command"

    def execute(self, context):
        target_path = Path(python_bin).parent.parent / "lib" / "site-packages"
        run_pip_command(
            self,
            *bpy.context.scene.pip_module_name.split(" "),  # todo this might break with spaces in folder names
            "--target",
            str(target_path),
        )
        return {"FINISHED"}


class PMM_OT_PIPInstall(bpy.types.Operator):
    bl_idname = "pmm.pip_install"
    bl_label = "Install packages"
    bl_description = "Install PIP packages"

    def execute(self, context):
        user_scripts_path = Path(bpy.utils.script_path_user())
        args = bpy.context.scene.pip_module_name.split(" ")  # todo this might break with spaces in folder names
        modules_path = user_scripts_path / "addons/modules"
        startup_path = user_scripts_path / "startup"

        # check if any editable installs in args
        for arg in args:
            if arg == "--editable" or arg == "-e":
                # todo handle target installs to other folders
                # TODO check if site packages folders in Blender also need to be added.

                create_pth_startup_file(startup_path=startup_path, pth_path=modules_path)
                break
        
        # todo site packages
        run_pip_command(self, "install", *args, "--target", modules_path)
        return {"FINISHED"}


class PMM_OT_PIPRemove(bpy.types.Operator):
    bl_idname = "pmm.pip_remove"
    bl_label = "Remove packages"
    bl_description = "Remove PIP packages"

    def execute(self, context):
        args = bpy.context.scene.pip_module_name.split(" ")   # todo this might break with spaces in folder names
        run_pip_command(self, "uninstall", *args, "-y")
        return {"FINISHED"}


class PMM_OT_ClearText(bpy.types.Operator):
    bl_idname = "pmm.pip_cleartext"
    bl_label = "Clear text"
    bl_description = "Clear text output"

    def execute(self, context):
        global TEXT_OUTPUT
        TEXT_OUTPUT = []
        global ERROR_OUTPUT
        ERROR_OUTPUT = []
        return {"FINISHED"}


class PMM_OT_PIPList(bpy.types.Operator):
    bl_idname = "pmm.pip_list"
    bl_label = "List packages"
    bl_description = "List installed PIP packages"

    def execute(self, context):
        run_pip_command(self, "list", cols=True)
        return {"FINISHED"}


class PMM_OT_EnsurePIP(bpy.types.Operator):
    bl_idname = "pmm.ensure_pip"
    bl_label = "Ensure PIP"
    bl_description = "Try to ensure PIP exists"

    def execute(self, context):
        run_pip_command(self, "--default-pip", run_module="ensurepip")
        return {"FINISHED"}


class PMM_OT_UpgradePIP(bpy.types.Operator):
    bl_idname = "pmm.upgrade_pip"
    bl_label = "Upgrade PIP"
    bl_description = "Upgrade PIP"

    def execute(self, context):
        run_pip_command(self, "install", "--upgrade", "pip")
        return {"FINISHED"}


class PMM_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    def draw(self, context):
        layout = self.layout
        row = layout.row()

        row = layout.row()
        row.operator(PMM_OT_EnsurePIP.bl_idname, text="Ensure PIP")
        row.operator(PMM_OT_UpgradePIP.bl_idname, text="Upgrade PIP")
        row.operator(PMM_OT_PIPList.bl_idname, text="List")

        row = layout.row()
        row.prop(bpy.context.scene, "pip_module_name", text="Module name(s)")
        row.operator(PMM_OT_PIPInstall.bl_idname, text="Install")
        row.operator(PMM_OT_PIPRemove.bl_idname, text="Remove")
        row.operator(PMM_OT_PIPCommand.bl_idname, text="Command")

        if TEXT_OUTPUT != []:
            row = layout.row(align=True)
            box = row.box()
            box = box.column(align=True)
            for i in TEXT_OUTPUT:
                row = box.row()
                for s in i:
                    col = row.column()
                    col.label(text=s)
            row = layout.row()

        if ERROR_OUTPUT != []:
            # row = layout.row(align=True)
            # row.label(text="Error messages:")
            row = layout.row(align=True)
            box = row.box()
            box = box.column(align=True)
            for i in ERROR_OUTPUT:
                row = box.row()
                for s in i:
                    col = row.column()
                    col.label(text=s)
            row = layout.row()

        if TEXT_OUTPUT != [] or ERROR_OUTPUT != []:
            row.operator(PMM_OT_ClearText.bl_idname, text="Clear output text")


classes = (
    PMM_AddonPreferences,
    PMM_OT_EnsurePIP,
    PMM_OT_UpgradePIP,
    PMM_OT_PIPList,
    PMM_OT_PIPInstall,
    PMM_OT_PIPRemove,
    PMM_OT_ClearText,
    PMM_OT_PIPCommand,
)


def register():
    for c in classes:
        bpy.utils.register_class(c)

    bpy.types.Scene.pip_modules_home = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.pip_advanced_toggle = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.pip_module_name = bpy.props.StringProperty()


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

    del bpy.types.Scene.pip_modules_home
    del bpy.types.Scene.pip_advanced_toggle
    del bpy.types.Scene.pip_module_name
