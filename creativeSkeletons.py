import maya.api.OpenMaya as om
import maya.api.OpenMayaRender as omr
import maya.api.OpenMayaUI as omui
import maya.cmds as cmds
import runpy
import sys

# connect to the OpenMaya API 2.0
maya_useNewAPI = True

class creativeLocNode(omui.MPxLocatorNode):
    ''' Custom Locator containing viewport rendering privileges. '''
    TYPE_ID = om.MTypeId(0x0007f7f8)
    TYPE_NAME = "cLocator"
    DRAW_CLASSIFICATION = "drawdb/geometry/cLocator"
    DRAW_REGISTRANT_ID = "creativeLocNode"

    def __init__(self):
        ''' Gathers an instance of the inherited class and initialize it's methods & properties. '''
        super(creativeLocNode, self).__init__()

    @classmethod
    def creator(cls):
        ''' Required method that tells maya which & what object will be instantiated. '''
        return creativeLocNode()
    
    @classmethod
    def initialize(cls):
        ''' Required method that tells maya to initialize the internal contents of the node type. '''
        pass

    def getShapeSelectionMask(self):
        ''' Overriden method to support interactive object selection in Viewport 2.0 '''
        selectionType=om.MSelectionMask.kSelectNurbsCurves
        return om.MSelectionMask(selectionType)

    def getComponentSelectionMask(self):
        ''' Overriden method to support interactive component selection in Viewport 2.0 '''
        selectionMaskObj=om.MSelectionMask()
        selectionMaskObj.addMask(om.MSelectionMask.kSelectCVs)
        return selectionMaskObj

    def isBounded(self):
        return True
    
    def boundingBox(self):
        ''' Dynamically calculates the bounding box based on the local position and scale.'''
        locObject=self.thisMObject()
        dependFn=om.MFnDependencyNode(locObject)

        # read local position (x, y, z)
        # findPlug() returns MPlug which contains the asFloat() method
        xLocalPos=dependFn.findPlug('localPositionX', False).asFloat()
        yLocalPos=dependFn.findPlug('localPositionY', False).asFloat()
        zLocalPos=dependFn.findPlug('localPositionZ', False).asFloat()       

        # read local scale (x, y, z)
        # findPlug() returns MPlug which contains the asFloat() method
        xLocalScale=dependFn.findPlug('localScaleX', False).asFloat()
        yLocalScale=dependFn.findPlug('localScaleY', False).asFloat()
        zLocalScale=dependFn.findPlug('localScaleZ', False).asFloat()       

        # calculate corners positions and return built bounding box 
        base=2 # base size
        minPos=om.MPoint(xLocalPos-(base*xLocalScale), yLocalPos-(base*yLocalScale), zLocalPos-(base*zLocalScale))
        maxPos=om.MPoint(xLocalPos+(base*xLocalScale), yLocalPos+(base*yLocalScale), zLocalPos+(base*zLocalScale))
        boundingBoxObj=om.MBoundingBox(minPos, maxPos)
        return boundingBoxObj

class creativeLocData(om.MUserData):
    ''' Custom data container to pass plug/attributes for when the node gets drawn. '''
    def __init__(self):
        super(creativeLocData, self).__init__()
        self.localPosition = om.MPoint(0, 0, 0)
        self.localScale = om.MVector(1, 1, 1)

class creativeLocDrawOverride(omr.MPxDrawOverride):
    ''' Manages how the node will behave and be updated once it's drawn into Viewport 2.0 '''
    NAME = "creativeLocDrawOverride"

    def __init__(self, obj):
        super(creativeLocDrawOverride, self).__init__(obj, None, False)

    # grab data from the node and pack it into MUserData
    def prepareForDraw(self, objPath, cameraPath, frameContext, oldData):
        ''' 
        Handles the initial draw state of the node. 
        Returns the constructed data so the node can be drawn. 
        '''
        # gather or create the node's draw data
        data = oldData if isinstance(oldData, creativeLocData) else creativeLocData()

        # access node attributes
        node=objPath.node()
        dependFn=om.MFnDependencyNode(node)

        # query and store the localPosition and localScale plug values 
        data.localPosition = om.MPoint(dependFn.findPlug('localPositionX', False).asFloat(),
                                       dependFn.findPlug('localPositionY', False).asFloat(),
                                       dependFn.findPlug('localPositionZ', False).asFloat()) 
        
        data.localScale = om.MVector(dependFn.findPlug('localScaleX', False).asFloat(),
                                     dependFn.findPlug('localScaleY', False).asFloat(),
                                     dependFn.findPlug('localScaleZ', False).asFloat()) 

        return data

    def supportedDrawAPIs(self):
        return omr.MRenderer.kAllDevices
    
    def hasUIDrawables(self):
        return True
    
    def addUIDrawables(self, objPath, drawManager, frameContext, data):
        '''
        Handles how the node object will visually drawn in Viewport 2.0
        This method will only be called when hasUIDrawables() is overridden to return True.
        '''
        if not data:
            return
        
        drawManager.beginDrawable()
        drawManager.beginDrawInXray() # Xray module used to always render the locator in front

        # track the viewport display status of the locator 
        locState = omr.MGeometryUtilities.displayStatus(objPath)

        # locator selection tracker
        is_selected = False
        # kActive is to track if it's selected within a selection group; kLead is to track if it's the only or last selection  
        if locState == omr.MGeometryUtilities.kActive or locState == omr.MGeometryUtilities.kLead:
            is_selected = True

        # define color array before drawing
        highlightColor = om.MColor((0.85, 0.9, 0.55, 1.0))
        xColor=om.MColor((1.0, 0.0, 0.0, 1.0)) if not is_selected else highlightColor
        yColor=om.MColor((0.0, 1.0, 0.0, 1.0)) if not is_selected else highlightColor
        zColor=om.MColor((0.0, 0.0, 1.0, 1.0)) if not is_selected else highlightColor

        # build axis locator points
        origin = data.localPosition
        length = 1.5
        xEndPos=origin + om.MVector((length * data.localScale.x), 0, 0)
        yEndPos=origin + om.MVector(0, (length * data.localScale.y), 0)
        zEndPos=origin + om.MVector(0, 0, (length * data.localScale.z))

        # draw red x-axis line
        drawManager.setColor(xColor) 
        drawManager.line(origin, xEndPos)

        # draw green y-axis line
        drawManager.setColor(yColor)
        drawManager.line(origin, yEndPos)

        # draw blue z-axis line
        drawManager.setColor(zColor)
        drawManager.line(origin, zEndPos)

        drawManager.endDrawInXray()
        drawManager.endDrawable()

    @classmethod
    def creator(cls, obj):
        return creativeLocDrawOverride(obj)

    @classmethod
    def draw(context, data):
        ''' Calls to draw the node object. '''
        return

def initializePlugin(plugin):
    vendor="David Martinez"
    ver="0.1.0"

    pluginFn=om.MFnPlugin(plugin, vendor, ver)
    try:
        pluginFn.registerNode(creativeLocNode.TYPE_NAME, 
                               creativeLocNode.TYPE_ID, 
                               creativeLocNode.creator,
                               creativeLocNode.initialize, 
                               om.MPxNode.kLocatorNode, 
                               creativeLocNode.DRAW_CLASSIFICATION)
    except:
        om.MGlobal(f'Failed to register node: {creativeLocNode.TYPE_NAME}')

    try:
        omr.MDrawRegistry.registerDrawOverrideCreator(creativeLocNode.DRAW_CLASSIFICATION, 
                                                      creativeLocNode.DRAW_REGISTRANT_ID,
                                                      creativeLocDrawOverride.creator)
    except:
        om.MGlobal(f'Failed to register draw override: {creativeLocDrawOverride.NAME}')

    pluginPath=pluginFn.loadPath() # change to pluginFn.loadPath() for public release
    if pluginPath not in sys.path:
        sys.path.append(pluginPath)

    print(f'Running creativeSkeletons from: {pluginPath}')
    runpy.run_module('creativeSkeletons', run_name="__main__")
    
def uninitializePlugin(plugin):
    pluginFn=om.MFnPlugin(plugin)
    try:
        omr.MDrawRegistry.deregisterDrawOverrideCreator(creativeLocNode.DRAW_CLASSIFICATION, 
                                                        creativeLocNode.DRAW_REGISTRANT_ID)
    except:
        om.MGlobal(f'Failed to deregister draw override: {creativeLocDrawOverride.NAME}')

    try:
        pluginFn.deregisterNode(creativeLocNode.TYPE_ID)
    except:
        om.MGlobal(f'Failed to deregister node: {creativeLocNode.TYPE_NAME}')
    if cmds.menu('creativeSkeletonsMenu', exists=True):
        cmds.deleteUI('creativeSkeletonsMenu', menu=True)

# testing and debugging purposes
# if __name__ == "__main__":
#     cmds.file(new=True, force=True)
#     plugin_name = "creativeSkeletons.py"
#     cmds.evalDeferred('if cmds.pluginInfo("{0}", q=True, loaded=True): cmds.unloadPlugin("{0}")'.format(plugin_name))
#     cmds.evalDeferred('if not cmds.pluginInfo("{0}", q=True, loaded=True): cmds.loadPlugin("{0}")'.format(plugin_name))

#     cmds.evalDeferred('cmds.polyCube(w=20, h=20, d=20)')
#     cmds.evalDeferred('cmds.createNode("cLocator")')
#     cmds.evalDeferred('cmds.scale(10,10,10,"transform1")')