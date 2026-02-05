from creativeSkeletons import skeletonBuilderUI
from creativeSkeletons import shapeLibraryUI
import maya.cmds as mc
import importlib

def run_skeletonBuilder(*args):
    importlib.reload(skeletonBuilderUI)
    skeletonBuilderUI.show_skeletonBuilderUI_widget()

def run_shapeLibrary(*args):
    importlib.reload(shapeLibraryUI)
    shapeLibraryUI.show_shapeLibraryUI()

creativeSkeletonsMenu = mc.menu('creativeSkeletonsMenu', label = 'Creative Skeletons', parent = 'MayaWindow', tearOff = True)

mc.menuItem(label='Skeleton Builder', command = run_skeletonBuilder, parent = creativeSkeletonsMenu)

mc.menuItem(label='Shape Library', command = run_shapeLibrary, parent = creativeSkeletonsMenu)