from creativeSkeletons import creativeUI
import maya.cmds as mc
import importlib

def run_creativeUI(*args):
    importlib.reload(creativeUI)
    skeletonUI=creativeUI.creativeUI()
    skeletonUI.show_window()

creativeSkeletonsMenu = mc.menu('creativeSkeletonsMenu', label = 'Creative Skeletons', parent = 'MayaWindow', tearOff = True)

mc.menuItem(label='Skeleton Builder', command = run_creativeUI, parent = creativeSkeletonsMenu)

