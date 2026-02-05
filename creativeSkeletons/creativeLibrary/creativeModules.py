import maya.api.OpenMaya as om
import maya.cmds as cmds
from pathlib import Path
import json
import os

# maya modules dependent functions
def createLocator(name:str, 
                  prefix:str|None=None, suffix:str|None=None,
                  locScale:float=5):
    ''' 
    Creates a cluster object from the provided selection list and
    constrains a newly created locator to the cluster position. 
    Returns the locator transform name. 
    '''
    if prefix:
        # add prefix string to locator 
        name=prefix+name
    if suffix:
        # add suffix string to locator
        name+=suffix
    # create custom locator and obtain its transform node
    locShp=cmds.createNode('cLocator', name=f'{name}_loc_shp')
    locTrn=cmds.listRelatives(locShp, parent=True)[0]
    # set locator's local scale
    scaleID=['localScaleX', 'localScaleY', 'localScaleZ']
    for id in scaleID:
        cmds.setAttr(f'{locShp}.{id}', locScale)
    # store full name in ID 
    locObjID=name
    # rename locator's transform
    cmds.rename(locTrn, locObjID)
    cmds.select(clear=True)
    return locObjID

def clusterLocParent(selectionLs:list, clusterName:str, locObj:str):
    ''' 
    Creates single cluster based on the selection list to point constrain a locator to it.
    Deletes cluster after constraint.
    '''
    # use flatten flag to store selection values a sequential list (i.e. vtx[], vtx[], vtx[])
    dataSelection=cmds.ls(selectionLs, flatten=True)
    if not dataSelection:
        return None
    clusterObj=cmds.cluster(dataSelection, name=f'{clusterName}_cls')
    # constrain locator to cluster position then delete constraint
    cmds.pointConstraint(clusterObj, locObj)
    cmds.delete(clusterObj)

def buildJointChain(startVector:om.MPoint, endVector:om.MPoint, 
                    jntNames:list=['start', 'end'],
                    jntNums:int=2, parentJnt=None, 
                    orientJoint:str='xyz', secAxisOrient:str='yup', 
                    rotationOrder:str='xyz', jntsRad:float=3,
                    prefix:str|None=None, suffix:str|None=None,
                    overrideColor:int|None=None):
    ''' Creates a joint chain between two provided locator positions. '''
    # verify that the script doesn't create a single joint, must be a two joint chain at minimum
    if jntNums < 2:
        cmds.warning('Number of Joints cannot be lesser than 1')
        return

    cmds.select(clear=True)
    # select parent joint if provided to connect the new joint chain to it
    if parentJnt:
        cmds.select(parentJnt)
    
    createdJnts=[]
    for n in range(jntNums):
        jntName=jntNames[n]

        if n==0 and cmds.objExists(jntName):
             cmds.select(jntName)
             createdJnts.append(jntName)
        else:
            # obtain interpolation ratio
            ratio=float(n) / (jntNums - 1)

            # use lerp formula to find joint (x,y,z) position: [initialPosition+(totalDistance)*percentageTraveled]
            jntPos=[startVector.x + (endVector.x-startVector.x) * ratio,
                    startVector.y + (endVector.y-startVector.y) * ratio,
                    startVector.z + (endVector.z-startVector.z) * ratio]

            if prefix:
                # add prefix string to joint
                jntName=prefix+jntName
            if suffix:
                # add suffix string to joint
                jntName+=suffix

            # create joint at calculated position with numbered naming convention
            newJnt=cmds.joint(name=jntName, p=jntPos, rad=jntsRad)
            createdJnts.append(newJnt)

    # obtain start and end joint names
    startJnt, endJnt = createdJnts[0], createdJnts[-1]
    # set joint orientation for the entire chain except
    cmds.joint(startJnt, edit=True, orientJoint=orientJoint, 
               secondaryAxisOrient=secAxisOrient, rotationOrder=rotationOrder, children=True)
    # zero out the rotation of the very last joint so it aligns with the world or parent
    cmds.joint(endJnt, edit=True, orientJoint='none', children=True)
    
    cmds.select(clear=True)

    if overrideColor:
        cmds.setAttr(f'{startJnt}.overrideEnabled', True)
        cmds.setAttr(f'{startJnt}.overrideColor', overrideColor)
    return createdJnts

def aimLocators(locStartName:str, locEndName:str,
                aimVector:list=[1,0,0], upVector:list=[0,1,0],
                worldUpVector:list=[0,1,0]):
    ''' 
    Sets aim constraints between two locators.
    Locators aim at each other to simulate parent/child joint orientation relationship.
    '''
    # get locator parent & aim constraints, delete each if any exists
    startConstraints=[]
    if cmds.listRelatives(locStartName, type='parentConstraint'):
        startConstraints.append(*cmds.listRelatives(locStartName, type='parentConstraint'))
    if cmds.listRelatives(locStartName, type='aimConstraint'):
        startConstraints.append(*cmds.listRelatives(locStartName, type='aimConstraint'))
    if startConstraints:
        for constraint in startConstraints:
            cmds.delete(constraint)

    # get locator parent & aim constraints, delete each if any exists
    endConstraints=[]
    if cmds.listRelatives(locEndName, type='parentConstraint'):
        endConstraints.append(cmds.listRelatives(locEndName, type='parentConstraint'))
    if cmds.listRelatives(locEndName, type='aimConstraint'):
        endConstraints.append(cmds.listRelatives(locEndName, type='aimConstraint'))
    if endConstraints:
        for constraint in endConstraints:
            cmds.delete(constraint)

    # make start locator aim at end locator
    cmds.aimConstraint(locEndName, locStartName, aim=aimVector, u=upVector, wu=worldUpVector)
    # create negative aim vector for end locator to aim at start locator
    negAimVector=[val*(-1) for val in aimVector]
    cmds.aimConstraint(locStartName, locEndName, aim=negAimVector, u=upVector, wu=worldUpVector)

def jointLocParent(jntName:str, locName:str):
    ''' 
    Constrains a locator to a joint using parent constraint.
    Deletes any relevant constraints before applying new ones.
    '''
    # get locator & joint constraints, delete each if any exists
    locConstraints=cmds.listRelatives(locName, type='aimConstraint')
    jntConstraints=cmds.listRelatives(jntName, type='parentConstraint')
    if jntConstraints:
        print(jntConstraints)
        for constraint in jntConstraints:
            cmds.delete(constraint)
    if locConstraints:
        for constraint in locConstraints:
            cmds.delete(constraint)
    
    cmds.parentConstraint(jntName, locName)

def mirrorJoints(mirrorAxis:str='YZ', mirrorFunc:str='Behavior',
                 search:str='', replace:str='', includeLocators:bool=False):
    ''' 
    Sets up joint mirroring based on provided axis and function. 
    Returns a list of the newly created mirrored joint chain.
    '''
    mirrorAxisVal, mirrorFuncVal = ('XY','XZ','YZ'), ('Behavior', 'Orientation')
    if mirrorAxis not in mirrorAxisVal or mirrorFunc not in mirrorFuncVal:
        raise ValueError('Wrong value given for mirrorAxis or mirrorFunc')
    
    jntSelection=cmds.ls(selection=True, type='joint')
    if not jntSelection:
        return None

    searchReplace=(search, replace)

    if mirrorAxis=='XY':
        cmds.mirrorJoint(mxy=True, mb=True, sr=searchReplace) if mirrorFunc == 'Behavior' else cmds.mirrorJoint(mxy=True, mb=False, sr=searchReplace)
    elif mirrorAxis=='XZ':
        cmds.mirrorJoint(mxz=True, mb=True, sr=searchReplace) if mirrorFunc == 'Behavior' else cmds.mirrorJoint(mxz=True, mb=False, sr=searchReplace)
    else:
        cmds.mirrorJoint(myz=True, mb=True, sr=searchReplace) if mirrorFunc == 'Behavior' else cmds.mirrorJoint(myz=True, mb=False, sr=searchReplace)
    
    cmds.select(hi=True)
    mirroredChain=cmds.ls(selection=True, type='joint')
    
    if includeLocators:
        mirroredSet={}
        # select joint hierarchy
        cmds.select(jntSelection, hi=True)
        jntChain=cmds.ls(selection=True, type='joint')
        for i, jnt in enumerate(jntChain):
            constraints=cmds.listConnections(jnt, type='parentConstraint')
            for constraint in constraints:
                node=cmds.listConnections(constraint)[0]
                nodeShp=cmds.listRelatives(node, type='shape')[0]
                if cmds.nodeType(nodeShp)=='cLocator' or cmds.nodeType(nodeShp)=='locator':
                    mirroredSet[mirroredChain[i]]=[node.replace(search, replace), cmds.getAttr(f'{nodeShp}.localScaleX')]
                    break
        print(mirroredSet)
        if mirroredSet:
            # create each mirrored locator
            for jnt in mirroredSet:
                locName=mirroredSet.get(jnt)[0]
                locScale=mirroredSet.get(jnt)[1]
                createLocator(locName, locScale=locScale)
                jointLocParent(jnt, locName)
    
    return mirroredChain

def getCurveRotation(childJoints:list):
    ''' Finds the control's orientation based on the joint children. '''
    if len(childJoints) < 2: # joint has only one child
        # get the absolute values of the joint's position/location
        childJointPos = (abs(cmds.getAttr(childJoints[0] + '.translateX')),
                         abs(cmds.getAttr(childJoints[0] + '.translateY')),
                         abs(cmds.getAttr(childJoints[0] + '.translateZ')))
        
        # analyze the max translation value and set the rotation axis for the controller curve 
        jointLength = max(childJointPos)
        if childJointPos.index(jointLength) == 0:
            # curve rotation in x-axis
            curveRotation = (0, 0, 90)
        if childJointPos.index(jointLength) == 1:
            # no curve rotation, y-axis
            curveRotation = (0, 0, 0)
        if childJointPos.index(jointLength) == 2:
            # curve rotation in z-axis
            curveRotation = (90, 0, 0)
    
    else: # joint has multiple children
        # get list comprehension of each axis absolute position value for each child joint
        childJointPosX = [abs(cmds.getAttr(jnt + '.translateX')) for jnt in childJoints]
        childJointPosY = [abs(cmds.getAttr(jnt + '.translateY')) for jnt in childJoints]
        childJointPosZ = [abs(cmds.getAttr(jnt + '.translateZ')) for jnt in childJoints]
        
        # get the absolute values of the joint's position/location based on the sum divided by the amount of all child joints
        childJointPos = [sum(childJointPosX)/len(childJointPosX),
                         sum(childJointPosY)/len(childJointPosY),
                         sum(childJointPosZ)/len(childJointPosZ)]
        
        # analyze the max translation value and set the rotation axis for the controller curve 
        jointLength = max(childJointPos)
        if childJointPos.index(jointLength) == 0:
            # curve rotation in x-axis
            curveRotation = (0, 0, 90)
        if childJointPos.index(jointLength) == 1:
            # no curve rotation, y-axis
            curveRotation = (0, 0, 0)
        if childJointPos.index(jointLength) == 2:
            # curve rotation in z-axis
            curveRotation = (90, 0, 0)

    # check if length is 0 
    if jointLength < 0.1:
        jointLength = 1.0
        
    return curveRotation

def savePositions(vertSelectionList:list, setName:str):
    '''
    Returns a position set created from the vertex selection. 
    Selection list should only include vertex set.
    '''
    vertSelectionSet={}
    vertPositions=getVertPositions(vertSelectionList)
    vertSelectionSet[setName]=vertPositions
    return vertSelectionSet

def getVertPositions(selection:list):
    ''' Returns a list of each vertex position values from the provided selection. '''
    # use flatten flag to place the proper position values for each selected vert
    verts=cmds.ls(selection, flatten=True)
    # verify that the selection is not lower than 0 vertices before proceeding
    if len(verts) <= 0:
        return None
    else:
        verts_pos=[]
        for vert in verts:
            if '.vtx' not in vert:
                cmds.warning('selection set can only include vertices')
                return
            # get the specific 'x', 'y' or 'z' position values and store them
            vert_pos=cmds.xform(vert, q=True, ws=True, t=True)
            verts_pos.append(vert_pos)
        # sort from highest to least value of each every item using the direction position value 
        verts_pos.sort(key=lambda position: position)
        # verts_pos.sort()
        return verts_pos

def getRootJoints() -> list:
    ''' Returns a list of root joints found in the current scene. '''
    scene_joints=cmds.ls(type='joint')

    if not scene_joints:
        print("No joints found")
        
    root_joints=[]
    for joint in scene_joints:
        # if joint has no parent or parent is not a joint, store root joint
        parent_jnt=cmds.listRelatives(joint, parent=True, fullPath=True)
        if not parent_jnt or cmds.nodeType(parent_jnt[0]) != 'joint':
            root_joints.append(joint)

    return root_joints

def selectRootJnt(root_jnt:str, contains_list:bool=False, jnts:list=[]) -> None:
    ''' 
    Checks root joint exists and selects it.
    Contains_list must be True to deselect provided joint list.
    '''
    if contains_list:
        for jnt in jnts:
            if cmds.objExists(jnt):
                cmds.select(jnt, deselect=True)
    else:
        cmds.warning('Must provide a joint list to deselect.')

    if not cmds.objExists(root_jnt):
        print('Nothing Selected')
    else:
        cmds.select(root_jnt, add=True)
        print(f'{root_jnt} Selected')

def getUnusedJoints(root_jtns:list):
    unbinded_jnts={}
    for root_jnt in root_jtns:
        if cmds.nodeType(root_jnt) != 'joint':
            continue
        if not cmds.objExists(root_jnt):
            continue

        hierarchy=cmds.listRelatives(root_jnt, allDescendents=True, type='joint', fullPath=True)

        hierarchy.append(root_jnt)

        unused_jnts = []

        for jnt in hierarchy:
            is_bound=False
            connections=cmds.listConnections(f'{jnt}.worldMatrix[0]', type='skinCluster')

            if connections:
                is_bound=True

            if not is_bound:
                unused_jnts.append(jnt)
        unbinded_jnts[root_jnt]=unused_jnts

    return unbinded_jnts

def bindUnusedJoints(root_jnts_data:dict):
    for root_jnt in root_jnts_data:
        connections=cmds.listConnections(f'{root_jnt}.worldMatrix[0]', type='skinCluster')
        print(connections)
    
    for unbinded_joint in root_jnts_data.get(root_jnt):
        for connected_cluster in connections:
            cmds.skinCluster(connected_cluster, edit=True, 
                           addInfluence=unbinded_joint, 
                           weight=0.0, lockWeights=False)
            
def getSkinnedMeshes(selection:list) -> list:
        ''' Returns a list of skinned meshes from the provided selection. '''
        skinned_meshes=[]

        for mesh in selection:
            # if item is a mesh, get shape nodes
            shapes = cmds.listRelatives(mesh, shapes=True, fullPath=True)
            if shapes:
                for shape in shapes:
                    if cmds.nodeType(shape) == 'mesh':
                        # find skin cluster connection
                        clusters = cmds.ls(cmds.listConnections(shape, type='skinCluster'), 
                                        type='skinCluster')
                    
                        if clusters:
                            skinned_meshes.append(mesh)
                            break # stop checking other shapes if one is skinned

        return skinned_meshes

def delNonDeformHistory(mesh_sl:list) -> None:
    ''' Deletes non-deformer history of the provided selection list. '''
    for obj in mesh_sl:
        if cmds.nodeType(obj) != 'mesh':
            continue
        # deletes the non-derformer history of the selected mesh
        cmds.bakePartialHistory(obj, prePostDeformers=True)

def moveToOrigin(mesh) -> None:
    ''' Moves the provided mesh to the world origin (0,0,0) using its rotate pivot. '''
    cmds.move(0,0,0, mesh, rotatePivotRelative = True)

def placeObjBack(values, mesh) -> None:
    ''' Moves the provided mesh back to its original position using provided values. '''
    cmds.move(values[0],
            values[1],
            values[2], mesh, absolute=True)    

# data handling related functions
def saveData(path:str, file_name:str, data) -> None:
    ''' Saves data into a json file: must include a path to store data. '''
    if not file_name.endswith('.json'):
        file_name+='.json'

    with open(os.path.join(path, file_name), 'w') as file:
        json.dump(data, file, indent=4, sort_keys=True)

def loadData(path:str, file_name:str) -> dict:
    ''' Loads a path data (dictionary) from a json file. '''
    with open(os.path.join(path, file_name), 'r') as file:
        stored_data = json.load(file)

    return stored_data

# directory related functions
def getDocumentsFolder() -> str:
    ''' Finds the documents path inside the user's home directory. '''
    documents_path = os.path.join(str(Path.home()), 'Documents')
    return documents_path

def pathExists(file_path: str) -> bool:
    ''' Checks if a path or file path exists. '''
    if os.path.exists(file_path):
        return True
    
    else:
        return False
