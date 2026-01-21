from .creativeLibrary import creativeModules as md
from .wrapperQt import wrapperWidgets, wrapperLayouts
from PySide6 import QtCore, QtGui, QtWidgets
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from shiboken6 import wrapInstance, isValid
import maya.api.OpenMaya as om2
import maya.OpenMayaUI as omui
import maya.cmds as mc
import os

# development only
import importlib
importlib.reload(md)
importlib.reload(wrapperWidgets)
importlib.reload(wrapperLayouts)

ORIGINAL_WIDTH=385
ORIGINAL_HEIGHT=110
WINDOW_ID='creativeUIWindow'

@QtCore.Slot()
def tester():
    print('This is a test')

def maya_main_window():
    mayaPtr=omui.MQtUtil.mainWindow()
    return wrapInstance(int(mayaPtr), QtWidgets.QWidget)

def show_creativeUI_widget(dock:bool=False, workspaceName:str='CreativeSkeletonsWorkspace'):
    
    if dock: # WIP to allow window to be dockable, currently works but window & widgets don't get resized  
        if mc.workspaceControl(workspaceName, query=True, exists=True):
            mc.deleteUI(workspaceName)

        ctrl=mc.workspaceControl(workspaceName, label='Creative Skeletons',
                                    dockToMainWindow=('right', 1), retain=False)
        
        qtCrtl=wrapInstance(int(omui.MQtUtil.findControl(ctrl)), QtWidgets.QWidget)
        layout=qtCrtl.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(qtCrtl)
            layout.setContentsMargins(0,0,0,0)

        windowInstance=creativeUI(parent=qtCrtl)
        layout.addWidget(windowInstance)
        return windowInstance
    else:
        mayaWindow=maya_main_window()
        # find any/all existing instances of the window & delete them
        outdatedWin=mayaWindow.findChildren(QtWidgets.QWidget, WINDOW_ID)
        if outdatedWin:
            for winToDel in outdatedWin:
                winToDel.setObjectName(f'outdated_{WINDOW_ID}')
                winToDel.close()
                winToDel.deleteLater()
        windowInstance=creativeUI()
        windowInstance.setWindowFlag(QtCore.Qt.WindowType.Window)
        windowInstance.resize(ORIGINAL_WIDTH, ORIGINAL_HEIGHT)
        windowInstance.show()
        return windowInstance

class creativeUI(QtWidgets.QWidget):
    ''' Base Interface class to handle maya skeleton creation with UI elements. '''
    WINDOW_TITLE='creativeSkeletons v0.1'

    def __init__(self, parent=maya_main_window()):
        ''' Initialize the main window Display, set state alongside UI elements & dependencies. '''
        super(creativeUI, self).__init__(parent)
        self.layouts=wrapperLayouts.wrapLay(self) # call layout wrapper instance
        self.widgets=wrapperWidgets.wrapWid(self) # call widget wrapper instance
        # store the directory path for icon file calls
        self.baseDirectory=os.path.dirname(__file__)
        print(self.baseDirectory)
        self.setObjectName(WINDOW_ID)
        # self.setWindowFlags(QtCore.Qt.Window) # normal window (minimize, maximize and exit buttons)
        self.setWindowTitle(self.WINDOW_TITLE)
        # self.resize(ORIGINAL_WIDTH, ORIGINAL_HEIGHT)

        # build vertical layout; attach to window display
        self.mainLayout=self.layouts.create_or_get_verticalLayout('mainLayout', spacing=5, contentMargins=(8,5,8,5))
        # build and set top icon buttons toolset
        self.build_top_buttons_layout()

        # build frame layout and look
        self.cardFrame=QtWidgets.QFrame()
        self.cardFrame.setObjectName('cardFrame')
        self.mainLayout.addWidget(self.cardFrame)
        self.cardLayout=self.layouts.create_or_get_verticalLayout('cardLayout', parentWidget=self.cardFrame, contentMargins=(5,5,5,5))

        # create tracking variables for locator joint creation, alongside layout display states
        self.sortedLocIDs=['none', 'none']
        self.sortedJntIDs=[] # stores joint ID strings in order of creation
        self.locatorSets={}
        self.locatorSetsCopy={} # copy needed for undo/redo operations; allows restoration of deleted locators
        self.locStartName=''
        self.locEndName=''
        self.jntLayoutDisplayed=False
        self.jntMidFields=[] # keeps instance of middle joint name fields for dynamic addition/removal

        # create static immutable ID values & parameters
        self.available_locatorIDs=['locator', 'cLocator'] # locator node types in case custom locators are unavailable
        self.available_sequenceID=['start', 'end']
        self.aimFieldID=['aimFieldX', 'aimFieldY', 'aimFieldZ']
        self.upFieldID=['upFieldX', 'upFieldY', 'upFieldZ']
        self.wupFieldID=['wupFieldX', 'wupFieldY', 'wupFieldZ']
        self.aimWidgetID=['aimCheck', 'aimBtn']

        self.build_main_layout()
        self._apply_style()

    def build_main_layout(self):
        ''' Handles the construction of the main UI layout structure and its elements. '''

        # build aim constraint checkbox & related fields
        aimForm=self.layouts.create_or_get_gridLayout('aimForm', parentWidget=self.cardFrame, parentLayout=self.cardLayout)
        aimForm.setAlignment(QtCore.Qt.AlignHCenter)
        self.mainLayout.addLayout(aimForm)
        self.widgets.create_checkbox(self.aimWidgetID[0], 'Locator Aim Constraint', aimForm, 
                                             clickedCmd=self.checkbox_aim_sequence)
        # initialize aim constraint related fields & buttons, hidden by default
        self.build_aim_layout()

        # build joint orientation & rotation order checkbox & related elements
        orientForm=self.layouts.create_or_get_gridLayout('orientForm', parentWidget=self.cardFrame, parentLayout=self.cardLayout)
        orientForm.setAlignment(QtCore.Qt.AlignHCenter)
        self.mainLayout.addLayout(orientForm)
        self.widgets.create_checkbox('orientCheck', 'Joint Orient | Rotation Order', orientForm, 
                                             clickedCmd=self.checkbox_orient_sequence)
        self.build_orient_layout()

        # build joint chain mirroring checkbox & related elements
        mirrorCheckLayout=self.layouts.create_or_get_verticalLayout('mirrorCheckLayout', 
                                                                    parentWidget=self.cardFrame, parentLayout=self.cardLayout)
        mirrorCheckForm=self.layouts.create_or_get_gridLayout('mirrorCheckForm', parentLayout=mirrorCheckLayout)
        mirrorJntsCheck=self.widgets.create_checkbox('mirrorJntsCheck', 'Mirror Joints', mirrorCheckForm,
                                                     align=QtCore.Qt.AlignHCenter,
                                                     clickedCmd=lambda *args:self.checkbox_mirror_sequence(mirrorJntsCheck.isChecked()))
        self.build_mirror_layout()

        self.widgets.create_label('locPrefixSuffixLabel', 'Locator Prefix and Suffix names:', 
                                  self.cardLayout, align=QtCore.Qt.AlignBottom | QtCore.Qt.AlignHCenter)
        # build fields to set the locator prefix and suffix names
        locPrefixSuffix=self.layouts.create_or_get_gridLayout('locPrefixSuffix', parentWidget=self.cardFrame, parentLayout=self.cardLayout,
                                                              contentMargins=(45,0,45,0))
        locPrefixSuffix.setAlignment(QtCore.Qt.AlignBottom | QtCore.Qt.AlignHCenter)
        self.widgets.create_textField('locPrefixField', locPrefixSuffix,
                                      placeholderText='Locator Prefix')
        self.widgets.create_textField('locSuffixField', locPrefixSuffix, gridSet=(0,1),
                                      placeholderText='Locator Suffix', text='_loc')
        
        # create grid layout for main fields & buttons
        midLayout=self.layouts.create_or_get_gridLayout('midLayout', parentWidget=self.cardFrame, parentLayout=self.cardLayout)
        midLayout.setAlignment(QtCore.Qt.AlignBottom | QtCore.Qt.AlignHCenter)
        startLocCheck=self.widgets.create_checkbox('startLocCheck', 'Select Locator', 
                                                   midLayout, align=QtCore.Qt.AlignHCenter, 
                                                   clickedCmd=lambda args:self.checkbox_loc_sequence(startLocCheck.isChecked()))
        endLocCheck=self.widgets.create_checkbox('endLocCheck', 'Select Locator', midLayout, 
                                                 gridSet=(0,1), align=QtCore.Qt.AlignHCenter,
                                                 clickedCmd=lambda args:self.checkbox_loc_sequence(endLocCheck.isChecked(),
                                                                                                           sequenceID='end'))
        
        # build fields to set the locator names
        self.widgets.create_textField('startLocField', midLayout, gridSet=(1,0),
                                              placeholderText='Start Locator Name', margins=(5,0,5,0))
        self.widgets.create_textField('endLocField', midLayout, gridSet=(1,1),
                                              placeholderText='End Locator Name', margins=(5,0,5,0))

        # build buttons that handles the create or store locator modules 
        self.widgets.create_button('startLocBtn', 'Create Start Locator', midLayout, gridSet=(2,0),
                                           clickedCmd=lambda args:self.locator_btn_clicked())
        self.widgets.create_button('endLocBtn', 'Create End Locator', midLayout, gridSet=(2,1), 
                                           clickedCmd=lambda args:self.locator_btn_clicked('end'))
        
        # create joint chain related layouts, fields & buttons, hidden by default
        parentConstLayout=self.layouts.create_or_get_gridLayout('parentConstLayout', parentWidget=self.cardFrame, parentLayout=self.cardLayout)
        parentConstLayout.setAlignment(QtCore.Qt.AlignHCenter)
        self.widgets.create_checkbox('parentConstCheck', 'Locator to Joint Constraint', parentConstLayout, visible=False)

        # create radio buttons to either set joint parenting methods or create joints without selection
        parentJntLayout=self.layouts.create_or_get_gridLayout('parentJntLayout', parentWidget=self.cardFrame, parentLayout=self.cardLayout)
        startParentCheck=self.widgets.create_radialButton('startParentCheck', 'Start from Selected Joint', 
                                                          parentJntLayout, enabled=False, visible=False,
                                                          align=QtCore.Qt.AlignHCenter)
        continueParentCheck=self.widgets.create_radialButton('continueParentCheck', 'Parent to Selected Joint', 
                                                             parentJntLayout, enabled=False, visible=False,
                                                             align=QtCore.Qt.AlignHCenter, gridSet=(0,1))
        createJntLayout=self.layouts.create_or_get_gridLayout('createJntLayout', parentWidget=self.cardFrame, parentLayout=self.cardLayout)
        createJntCheck=self.widgets.create_radialButton('createJntCheck', 'Create Joint without Selection', 
                                                        createJntLayout, enabled=False, visible=False, value=True,
                                                        align=QtCore.Qt.AlignHCenter)

        self.widgets.create_label('jntPrefixSuffixLabel', 'Joints Prefix and Suffix names:', 
                                  self.cardLayout, visible=False,
                                  align=QtCore.Qt.AlignBottom | QtCore.Qt.AlignHCenter)
        # build fields to set the joints prefix and suffix names
        jntPrefixSuffix=self.layouts.create_or_get_gridLayout('jntPrefixSuffix', parentWidget=self.cardFrame, parentLayout=self.cardLayout,
                                                              contentMargins=(45,0,45,0),)
        self.widgets.create_textField('jntPrefixField', jntPrefixSuffix,
                                              placeholderText='Joints Prefix', visible=False)
        self.widgets.create_textField('jntSuffixField', jntPrefixSuffix, gridSet=(0,1),
                                              placeholderText='Joints Suffix', text='_jnt',
                                              visible=False)

        # build joint name fields layout
        jntNamesLayout=self.layouts.create_or_get_gridLayout('jntNamesLayout', parentWidget=self.cardFrame, parentLayout=self.cardLayout)
        self.widgets.create_textField('jntStartField', jntNamesLayout, 
                                              placeholderText='Starting Joint Name', visible=False)
        self.widgets.create_textField('jntEndField', jntNamesLayout, gridSet=(0,1),
                                              placeholderText='Ending Joint Name', visible=False)
        # set connections to enable/disable starting joint name field based which radio button is selected
        startParentCheck.clicked.connect(lambda args:self.enable_jnt_nameField(False))
        continueParentCheck.clicked.connect(lambda args:self.enable_jnt_nameField(True))
        createJntCheck.clicked.connect(lambda args:self.enable_jnt_nameField(True))

        # build joint count layout with slider and numeric field (SpinBox)
        jntCountLayout=self.layouts.create_or_get_gridLayout('jntCountLayout', parentWidget=self.cardFrame, parentLayout=self.cardLayout)
        jntCountLayout.setAlignment(QtCore.Qt.AlignBottom | QtCore.Qt.AlignHCenter)
        countSliderWidth=300
        jntCountLayout.setColumnMinimumWidth(0, countSliderWidth)
        jntCountSlider=self.widgets.create_slider('jntCountSlider', jntCountLayout, QtCore.Qt.Horizontal,
                                                  align=QtCore.Qt.AlignHCenter, value=2, minVal=2,
                                                  visible=False, enabled=False, width=countSliderWidth)
        jntCountField=self.widgets.create_numField('jntCountField', jntCountLayout, gridSet=(0,1),
                                                   align=QtCore.Qt.AlignHCenter, numVal=2, minVal=2,
                                                   visible=False, enabled=False, width=60)
        # connect slider and spinbox numeric values together; reflects changes together
        jntCountSlider.valueChanged.connect(jntCountField.setValue)
        jntCountField.valueChanged.connect(jntCountSlider.setValue)
        jntCountField.valueChanged.connect(lambda *args: self.add_or_remove_jnt_nameFields(jntCountField.value()))

        # build button tho handle the buildJointChain module and resets UI
        self.widgets.create_button('jntBuilderBtn', 'Create Joint Chain', self.cardLayout, enabled=False,
                                           clickedCmd=self.build_joint_chain)

        self.widgets.create_button('commitBtn', 'Commit Joint Chain Structure', self.cardLayout, 
                                           enabled=False, visible=False, clickedCmd=self.show_dialog_window)
        
        # build undo and redo buttons layout with their default state
        arrowLayout=self.layouts.create_or_get_gridLayout('arrowLayout', parentLayout=self.mainLayout)
        arrowLayout.setVerticalSpacing(10)
        arrowLayout.setAlignment(QtCore.Qt.AlignRight)
        arrowStyleSheet="""QToolButton {
                        border: 1px solid #555555;
                        border-radius: 3px;
                        background-color: #3a3a3a;
                        padding: 3px;}"""
        self.widgets.create_arrowButton('undoArrow', arrowLayout, direction='left',
                                                iconSize=QtCore.QSize(8, 8), styleSheet=arrowStyleSheet,
                                                enabled=False)
        self.widgets.create_arrowButton('redoArrow', arrowLayout, direction='right',
                                                iconSize=QtCore.QSize(8, 8), styleSheet=arrowStyleSheet,
                                                enabled=False, gridSet=(0,1))

        self.resize_layout(layout='card')

    def build_top_buttons_layout(self):
        ''' Handles the construction and display of the top right icon buttons. '''
        iconToolSetLayout=self.layouts.create_or_get_gridLayout('iconToolSetLayout', parentLayout=self.mainLayout)
        iconToolSetLayout.setHorizontalSpacing(2)
        iconToolSetLayout.setAlignment(QtCore.Qt.AlignRight)
        self.mainLayout.addLayout(iconToolSetLayout)
        iconBtnSizes=QtCore.QSize(24,24)

        lraIcon=QtGui.QIcon(os.path.join(self.baseDirectory, 'creativeLibrary', 
                                         'icons/menuIconDisplay_24.png'))
        lraBtn=QtWidgets.QToolButton()
        lraBtn.setIcon(lraIcon)
        lraBtn.setIconSize(iconBtnSizes)
        lraBtn.setAutoRaise(True)
        lraBtn.setFixedSize(24,24)
        lraBtn.clicked.connect(mc.ToggleLocalRotationAxes)

        selectHierIcon=QtGui.QIcon(os.path.join(self.baseDirectory, 
                                                'creativeLibrary' , 'icons/menuIconSelect_24.png'))
        selectHierBtn=QtWidgets.QToolButton()
        selectHierBtn.setIcon(selectHierIcon)
        selectHierBtn.setIconSize(iconBtnSizes)
        selectHierBtn.setAutoRaise(True)
        selectHierBtn.setFixedSize(24,24)
        selectHierBtn.clicked.connect(mc.SelectHierarchy)

        selectHierLraIcon=QtGui.QIcon(os.path.join(self.baseDirectory, 
                                                   'creativeLibrary', 'icons/menuIconSelectDisplay_24.png'))
        selectHierLraBtn=QtWidgets.QToolButton()
        selectHierLraBtn.setIcon(selectHierLraIcon)
        selectHierLraBtn.setIconSize(iconBtnSizes)
        selectHierLraBtn.setAutoRaise(True)
        selectHierLraBtn.setFixedSize(24,24)
        selectHierLraBtn.clicked.connect(mc.SelectHierarchy)
        selectHierLraBtn.clicked.connect(mc.ToggleLocalRotationAxes)

        iconToolSetLayout.addWidget(lraBtn)
        iconToolSetLayout.addWidget(selectHierBtn, 0, 1)
        iconToolSetLayout.addWidget(selectHierLraBtn, 0, 2)

    def build_aim_layout(self):
        ''' Handles the construction of the locator aim constraint layouts & related numeric fields. '''
        # build frame layout and look
        aimFrame=QtWidgets.QFrame()
        aimFrame.setObjectName('aimFrame')
        self.cardLayout.addWidget(aimFrame)
        aimFrameLayout=self.layouts.create_or_get_verticalLayout('aimFrameLayout', parentWidget=aimFrame, 
                                                                 contentMargins=(10,10,10,10))
        # create grid layout to place and align numeric fields
        vectorLayout=self.layouts.create_or_get_gridLayout('vectorLayout', parentWidget=aimFrame, 
                                                           parentLayout=aimFrameLayout)
        vectorLayout.setColumnMinimumWidth(0, 50)

        # create labels and numeric fields relating to each aim constraint parameters
        self.widgets.create_label('aimLabel', 'Aim Vector:', vectorLayout,
                                          visible=False, align=QtCore.Qt.AlignRight)
        self.widgets.create_numField(self.aimFieldID[0], vectorLayout, type='float', 
                                             numVal=1, minVal=-10, enabled=False, visible=False,
                                             gridSet=(0,1))
        self.widgets.create_numField(self.aimFieldID[1], vectorLayout, type='float', 
                                             minVal=-10, enabled=False, visible=False,
                                             gridSet=(0,2))
        self.widgets.create_numField(self.aimFieldID[2], vectorLayout, type='float', 
                                             minVal=-10, enabled=False, visible=False,
                                             gridSet=(0,3))
        
        self.widgets.create_label('upLabel', 'Up Vector:', vectorLayout,
                                          visible=False, align=QtCore.Qt.AlignRight,
                                          gridSet=(1,0))
        self.widgets.create_numField(self.upFieldID[0], vectorLayout, type='float', 
                                             minVal=-10, enabled=False, visible=False, 
                                             gridSet=(1,1))
        self.widgets.create_numField(self.upFieldID[1], vectorLayout, type='float',
                                             numVal=1, minVal=-10, enabled=False, visible=False,
                                             gridSet=(1,2))
        self.widgets.create_numField(self.upFieldID[2], vectorLayout, type='float',
                                             minVal=-10, enabled=False, visible=False,
                                             gridSet=(1,3))
        
        self.widgets.create_label('wupLabel', 'World Up Vector:', vectorLayout,
                                          visible=False, align=QtCore.Qt.AlignRight,
                                          gridSet=(2,0))
        self.widgets.create_numField(self.wupFieldID[0], vectorLayout, type='float',
                                             minVal=-10, enabled=False, visible=False,
                                             gridSet=(2,1))
        self.widgets.create_numField(self.wupFieldID[1], vectorLayout, type='float',
                                             numVal=1, minVal=-10, enabled=False, visible=False,
                                             gridSet=(2,2))
        self.widgets.create_numField(self.wupFieldID[2], vectorLayout, type='float',
                                             minVal=-10, enabled=False, visible=False,
                                             gridSet=(2,3))

        # build button to handle the aimLocators module
        self.widgets.create_button(self.aimWidgetID[1], 'Set Aim Constraint', aimFrameLayout, 
                                           enabled=False, visible=False,
                                           clickedCmd=self.aim_locators)
        aimFrame.setVisible(False)

    def build_orient_layout(self):
        ''' Handles the construction of the joint orientation and rotation order layouts & related elements. '''
        # build frame layout and look
        orientFrame=QtWidgets.QFrame()
        orientFrame.setObjectName('orientFrame')
        self.cardLayout.addWidget(orientFrame)
        orientFrameLayout=self.layouts.create_or_get_verticalLayout('orientFrameLayout', parentWidget=orientFrame, 
                                                                    contentMargins=(10,10,10,10))

        self.widgets.create_label('orientJntLabel', 'Joint Orientation & Secondary Axis:',
                                  orientFrameLayout, visible=False, 
                                  align=QtCore.Qt.AlignHCenter)

        # create layout for joint orientation menus
        orientJntLayout=self.layouts.create_or_get_gridLayout('orientJntLayout', parentWidget=orientFrame, 
                                                              parentLayout=orientFrameLayout)

        # create joint orientation menus with their corresponding option items
        orientJntMenu=QtWidgets.QComboBox()
        orientJntMenu.setObjectName('orientJntMenu')
        orientJntMenu.addItems(['xyz', 'yzx', 'zxy', 'zyx', 'yxz', 'xzy', 'none'])
        orientJntMenu.hide()
        orientJntLayout.addWidget(orientJntMenu)

        secOrientMenu=QtWidgets.QComboBox()
        secOrientMenu.setObjectName('secOrientMenu')
        secOrientMenu.addItems(['xup', 'xdown', 'yup', 'ydown', 'zup', 'zdown', 'none'])
        secOrientMenu.hide()
        orientJntLayout.addWidget(secOrientMenu, 0, 1)

        # create joint orientation related checkboxes and button
        orientCheckLayout=self.layouts.create_or_get_gridLayout('orientCheckLayout', parentWidget=orientFrame, 
                                                                parentLayout=orientFrameLayout)
        self.widgets.create_checkbox('orientChildCheck', 'Orient Children', 
                                             orientCheckLayout, align=QtCore.Qt.AlignHCenter,
                                             enabled=False, visible=False, value=True)

        self.widgets.create_checkbox('orientWorldCheck', 'Orient to World', 
                                             orientCheckLayout, align=QtCore.Qt.AlignHCenter,
                                             enabled=False, visible=False, gridSet=(1,0))
        
        self.widgets.create_button('orientBtn', 'Set Joint Orientation', orientFrameLayout, 
                                           enabled=False, visible=False,
                                           clickedCmd=self.orient_bnt_clicked)

        self.widgets.create_label('rotOrderLabel', 'Joint Rotation Order:',
                                  orientFrameLayout, visible=False,
                                  align=QtCore.Qt.AlignHCenter)

        # create joint rotation order menus with their corresponding option items
        rotOrderLayout=self.layouts.create_or_get_gridLayout('rotOrderLayout', parentWidget=orientFrame, 
                                                             parentLayout=orientFrameLayout)
        rotOrderMenu=QtWidgets.QComboBox()
        rotOrderMenu.setObjectName('rotOrderMenu')
        rotOrderMenu.addItems(['xyz', 'yzx', 'zxy', 'zyx', 'yxz', 'xzy'])
        rotOrderMenu.hide()
        rotOrderLayout.addWidget(rotOrderMenu)
        self.widgets.create_button('rotOrderBtn', 'Set Joint Rotation Order', orientFrameLayout, 
                                   enabled=False, visible=False,
                                   clickedCmd=self.joints_rotOrder)
        orientFrame.setVisible(False)

    def build_mirror_layout(self):
        ''' Handles the construction of the joint mirroring related elements. '''
        # build frame layout and look
        mirrorFrame=QtWidgets.QFrame()
        mirrorFrame.setObjectName('mirrorFrame')
        self.cardLayout.addWidget(mirrorFrame)
        mirrorFrameLayout=self.layouts.create_or_get_verticalLayout('mirrorFrameLayout', parentWidget=mirrorFrame, 
                                                                    contentMargins=(10,10,10,10))
        self.widgets.create_label('mirrorLabels', 'Mirror across | Mirror Function', mirrorFrameLayout,
                                          visible=False, align=QtCore.Qt.AlignHCenter)
        mirrorMenuLayout=self.layouts.create_or_get_gridLayout('mirrorMenuLayout', parentWidget=mirrorFrame, 
                                                             parentLayout=mirrorFrameLayout)

        mirrorAxisMenu=QtWidgets.QComboBox()
        mirrorAxisMenu.setObjectName('mirrorAxisMenu')
        mirrorAxisMenu.addItems(['YZ', 'XY', 'XZ'])
        mirrorAxisMenu.setVisible(False)
        mirrorMenuLayout.addWidget(mirrorAxisMenu)

        mirrorFuncMenu=QtWidgets.QComboBox()
        mirrorFuncMenu.setObjectName('mirrorFuncMenu')
        mirrorFuncMenu.addItems(['Behavior', 'Orientation'])
        mirrorFuncMenu.setVisible(False)
        mirrorMenuLayout.addWidget(mirrorFuncMenu, 0, 1)

        self.widgets.create_label('replaceLabels', 'Replacement Names', mirrorFrameLayout,
                                          visible=False, align=QtCore.Qt.AlignHCenter)

        mirrorFieldsLayout=self.layouts.create_or_get_gridLayout('mirrorFieldsLayout', parentWidget=mirrorFrame, 
                                                             parentLayout=mirrorFrameLayout)
        self.widgets.create_textField('searchField', mirrorFieldsLayout, 
                                      label='Search for:', placeholderText='search',
                                      visible=False)
        self.widgets.create_textField('replaceField', mirrorFieldsLayout, gridSet=(0,1),
                                      placeholderText='replace', label='Replace with:', 
                                      visible=False)

        self.widgets.create_button('mirrorJntsBtn', 'Create Mirror Joints', mirrorFrameLayout,
                                   visible=False, clickedCmd=self.mirror_joints)
        mirrorFrame.setVisible(False)

    def add_or_remove_jnt_nameFields(self, fieldAmount:int):
        ''' Handles the cyclical addition/removal of joint name fields based on a count value. '''
        jntNamesLayout=self.findChild(QtWidgets.QGridLayout, 'jntNamesLayout')
        jntEndField=self.findChild(QtWidgets.QLineEdit, 'jntEndField')
        midFields=fieldAmount-2 # there will always be 2 fields for start and end joints
        lastField=fieldAmount
        for field in self.jntMidFields:
            jntNamesLayout.removeWidget(field)
            field.deleteLater()

        self.jntMidFields.clear()

        for fieldNum in range(1, (midFields)+1):
            jntMidField=self.widgets.create_textField(f'jntMidField{fieldNum:02d}', jntNamesLayout, 
                                                              placeholderText=f'Middle {fieldNum:02d} Joint Name',
                                                              gridSet=(0, fieldNum))
            lastField=fieldNum
            self.jntMidFields.append(jntMidField)
        
        # place end joint name field after the last middle joint name field
        jntNamesLayout.addWidget(jntEndField, 0, (lastField+1))    

    def show_or_hide_prefixSuffix_fields(self, fields='loc', hide=False):
        ''' Toggles the locator or joint prefix & suffix fields visibility. '''
        available_fields=['loc', 'jnt']
        if fields not in available_fields:
            raise ValueError(f'{fields} is not available field element, use: {available_fields}')
        # store fields prefix & suffix related fields & elements
        jntPrefixSuffixLabel=self.findChild(QtWidgets.QLabel, 'jntPrefixSuffixLabel')
        jntPrefixField=self.findChild(QtWidgets.QLineEdit, 'jntPrefixField')
        jntSuffixField=self.findChild(QtWidgets.QLineEdit, 'jntSuffixField')
        locPrefixSuffixLabel=self.findChild(QtWidgets.QLabel, 'locPrefixSuffixLabel')
        locPrefixField=self.findChild(QtWidgets.QLineEdit, 'locPrefixField')
        locSuffixField=self.findChild(QtWidgets.QLineEdit, 'locSuffixField')

        if hide:
            if fields=='loc':
                locPrefixSuffixLabel.setVisible(False)
                locPrefixField.setVisible(False)
                locSuffixField.setVisible(False)
            else:
                jntPrefixSuffixLabel.setVisible(False)
                jntPrefixField.setVisible(False)
                jntSuffixField.setVisible(False)

        else:
            if fields=='loc':
                locPrefixSuffixLabel.setVisible(True)
                locPrefixField.setVisible(True)
                locSuffixField.setVisible(True)
            else:
                jntPrefixSuffixLabel.setVisible(True)
                jntPrefixField.setVisible(True)
                jntSuffixField.setVisible(True)
        self.resize_layout(layout='card')

    def show_or_hide_joint_count(self, hideLayout=False, hideButton=False):
        ''' Toggles the joint count layout visibility, handles locator data reset. '''
        # find and store joint related fields, checkboxes & buttons
        jntStartField=self.findChild(QtWidgets.QLineEdit, 'jntStartField')
        jntEndField=self.findChild(QtWidgets.QLineEdit, 'jntEndField')
        jointSlider=self.findChild(QtWidgets.QSlider, 'jntCountSlider')
        jointCount=self.findChild(QtWidgets.QSpinBox, 'jntCountField')
        parentConst=self.findChild(QtWidgets.QCheckBox, 'parentConstCheck')
        continueParent=self.findChild(QtWidgets.QRadioButton, 'continueParentCheck')
        startParent=self.findChild(QtWidgets.QRadioButton, 'startParentCheck')
        createJntCheck=self.findChild(QtWidgets.QRadioButton, 'createJntCheck')
        builderBtn=self.findChild(QtWidgets.QPushButton, 'jntBuilderBtn')
        
        if hideLayout:
            parentConst.setVisible(False)
            parentConst.setDisabled(True)
            startParent.setVisible(False)
            startParent.setDisabled(True)
            continueParent.setVisible(False)
            continueParent.setDisabled(True)
            createJntCheck.setVisible(False)
            createJntCheck.setDisabled(True)
            jntStartField.clear()
            jntStartField.setVisible(False)
            jntEndField.clear()
            jntEndField.setVisible(False)
            if self.jntMidFields:
                for jntMidField in self.jntMidFields:
                    jntMidField.clear()
                    jntMidField.setVisible(False)
            jointCount.setVisible(False)
            jointCount.setDisabled(True)
            jointSlider.setVisible(False)
            jointSlider.setDisabled(True)
            builderBtn.setDisabled(True)
            if hideButton:
                builderBtn.setVisible(False)
            self.show_or_hide_prefixSuffix_fields(fields='jnt', hide=True)

        else:
            parentConst.setVisible(True)
            parentConst.setEnabled(True)
            startParent.setVisible(True)
            startParent.setEnabled(True)
            continueParent.setVisible(True)
            continueParent.setEnabled(True)
            createJntCheck.setVisible(True)
            createJntCheck.setEnabled(True)
            jntStartField.setVisible(True)
            jntEndField.setVisible(True)
            if self.jntMidFields:
                for jntMidField in self.jntMidFields:
                    jntMidField.setVisible(True)
            jointCount.setVisible(True)
            jointCount.setEnabled(True)
            jointSlider.setVisible(True)
            jointSlider.setEnabled(True)
            builderBtn.setEnabled(True)
            self.show_or_hide_prefixSuffix_fields(fields='jnt')
            self.jntLayoutDisplayed=True

        self.resize_layout(layout='card')

    def show_or_hide_commitLayout(self, hide=False):
        ''' Toggles the commit button visibility. '''
        commitBtn=self.findChild(QtWidgets.QPushButton, 'commitBtn')

        if hide:
            commitBtn.setVisible(False)
            commitBtn.setDisabled(True)
        else:
            commitBtn.setVisible(True)
            commitBtn.setEnabled(True)
        self.resize_layout(layout='card')

    def resize_layout(self, layout='main'):
        ''' Forces the main & secondary layout to recompute its original size based on visible elements. '''
        available_layouts=('main', 'card')
        if layout not in available_layouts:
            raise ValueError(f'{layout} is not an available layout, use: {available_layouts}')
        targetLayout=self.mainLayout if layout == 'main' else self.cardLayout

        targetLayout.invalidate()
        targetLayout.activate()

        self.updateGeometry()
        self.adjustSize()

    def delete_data(self):
        ''' Clears the locator and joint tracking properties. '''
        self.sortedLocIDs=['none', 'none']
        self.locatorSets.clear()
        self.sortedJntIDs.clear()

    def locator_btn_clicked(self, sequenceID:str='start'):
        ''' Handles the create or store locator methods based on checkbox state. '''
        if sequenceID not in self.available_sequenceID:
            raise ValueError(f'[{sequenceID}] is not an available sequence, use: [{self.available_sequenceID}]')
        # find and store start & end related fields, checkboxes & buttons
        startBtn=self.findChild(QtWidgets.QPushButton, 'startLocBtn')
        startField=self.findChild(QtWidgets.QLineEdit, 'startLocField')
        startCheck=self.findChild(QtWidgets.QCheckBox, 'startLocCheck')
        endBtn=self.findChild(QtWidgets.QPushButton, 'endLocBtn')
        endField=self.findChild(QtWidgets.QLineEdit, 'endLocField')
        endCheck=self.findChild(QtWidgets.QCheckBox, 'endLocCheck')

        # determine which locator sequence to process (start or end)
        # call the locator method based on checkbox state
        if sequenceID=='start':
            if startCheck.isChecked():
                self.store_locator(startBtn, startField, startCheck)
            else:
                self.build_locator(startBtn, startField, startCheck)  
            
        else:
            if endCheck.isChecked():
                self.store_locator(endBtn, endField, endCheck,
                                   sequenceID='end')
            else:
                self.build_locator(endBtn, endField, endCheck,
                                   sequenceID='end')

    def arrow_btn_clicked(self, arrowID:str, 
                          locBtn:QtWidgets.QPushButton,
                          locField:QtWidgets.QLineEdit,
                          locCheck:QtWidgets.QCheckBox,
                          locObjID, deleteLoc:bool=False,
                          text='Start'):
        ''' 
        Handles the undo and redo operations for locator creation and storage. 
        Parameters are passed to re-enable/disable the locator layout accordingly.
        Undo & Redo signals should be disconnected prior to connecting this method.
        '''
        # find and store arrow button objects
        undoArrow=self.findChild(QtWidgets.QToolButton, 'undoArrow')
        redoArrow=self.findChild(QtWidgets.QToolButton, 'redoArrow')

        if arrowID=='undo':
            if deleteLoc:
                # store a copy of the current locator sets, remove the deleted locator from the copy
                self.locatorSetsCopy=self.locatorSets.copy()
                self.locatorSetsCopy.pop(locObjID)

                mc.undo() # undoes the locator creation set by build_locator method
                self.enable_locBtn(locBtn, locField, locCheck, buttonText=f'Create {text} Locator',
                                   clearField=False)
            else:
                # re-enable locator button, field & checkbox; no locator deletion
                self.enable_locBtn(locBtn, locField, locCheck, buttonText=f'Store {text} Locator',
                                   enableField=False, checkState=True)
            redoArrow.setEnabled(True)
            undoArrow.setDisabled(True)
            # verify if joint chain layout is displayed to hide it again
            if self.jntLayoutDisplayed:
                self.show_or_hide_joint_count(hideLayout=True)
                self.show_or_hide_prefixSuffix_fields() 
                self.jntLayoutDisplayed=False

        elif arrowID=='redo':
            # get locator position data from original locator sets, place the set back into the copy
            locObjPos=self.locatorSets.get(locObjID)
            self.locatorSetsCopy[locObjID]=locObjPos

            # redo the locator creation; if maya has reached the end of its redo stack simply skip to disable UI 
            try:
                mc.redo()
            except(RuntimeError):
                pass

            # disable locator button, field & checkbox again
            self.disable_locBtn(locBtn, locField, locCheck, locObjID)
            undoArrow.setEnabled(True)
            redoArrow.setDisabled(True)
            # check if both locator buttons have been disabled to enable joint chain layout
            self.check_locator_btns_disabled()

    def enable_locBtn(self, locBtn:QtWidgets.QPushButton, 
                      locField:QtWidgets.QLineEdit,
                      locCheck:QtWidgets.QCheckBox,
                      buttonText:str,
                      clearField:bool=True, 
                      enableField:bool=True,
                      checkState:bool=False):
        ''' Re-enables locator button, field & checkbox with optional parameters. '''
        locBtn.setEnabled(True)
        locBtn.setText(buttonText)
        locField.setEnabled(enableField)
        if clearField:
            locField.clear()
        locCheck.setEnabled(True)
        locCheck.setChecked(checkState)

    def disable_locBtn(self, locBtn:QtWidgets.QPushButton, 
                         locField:QtWidgets.QLineEdit,
                         locCheck:QtWidgets.QCheckBox,
                         fieldText=None):
        ''' 
        Disables locator button, field & checkbox, can set new text. 
        Used to indicate that locator has been created/stored.
        '''
        locBtn.setDisabled(True)
        locCheck.setDisabled(True)
        locField.setDisabled(True)
        if fieldText:
            locField.setText(fieldText)

    def check_locator_btns_disabled(self):
        ''' 
        Checks if both locator buttons are disabled to enable and show the joint chain layout. 
        If aim constraint is checked, set up aim constraint between locators.
        '''
        # find and store start & end related buttons
        startBtn=self.findChild(QtWidgets.QPushButton, 'startLocBtn')
        endBtn=self.findChild(QtWidgets.QPushButton, 'endLocBtn')

        if not startBtn.isEnabled() and not endBtn.isEnabled():
            if self.findChild(QtWidgets.QCheckBox, self.aimWidgetID[0]).isChecked():
                self.aim_locators()
            self.show_or_hide_joint_count()
            self.show_or_hide_prefixSuffix_fields(hide=True)

    def checkbox_loc_sequence(self, checked:bool, sequenceID:str='start'):
        ''' Switches the information displayed for each locator layout: create or select locator. '''
        if sequenceID not in self.available_sequenceID:
            raise ValueError(f'[{sequenceID}] is not an available sequence, use: [{self.available_sequenceID}]')
        # find and store start & end related fields & buttons
        startBtn=self.findChild(QtWidgets.QPushButton, 'startLocBtn')
        startField=self.findChild(QtWidgets.QLineEdit, 'startLocField')
        endBtn=self.findChild(QtWidgets.QPushButton, 'endLocBtn')
        endField=self.findChild(QtWidgets.QLineEdit, 'endLocField')
        
        # determine which locator sequence to process (start or end)
        # enable/disable fields and change button text based on checkbox state
        if checked:
            if sequenceID=='start':
                self.locStartName=startField.text() # store name value in case user decides to uncheck selection option
                startField.setDisabled(True) 
                startField.clear()
                startField.setPlaceholderText('Select Start Locator')
                startBtn.setText('Store Start Locator')
            else:
                self.locEndName=endField.text() # store name value in case user decides to uncheck selection option
                endField.setDisabled(True)
                endField.clear() 
                endField.setPlaceholderText('Select End Locator')
                endBtn.setText('Store End Locator') 
        else:
            if sequenceID=='start':
                startField.setEnabled(True)
                startField.setText(self.locStartName) # restore previous name value
                startField.setPlaceholderText('Start Locator Name')
                startBtn.setText('Create Start Locator')
            else:
                endField.setEnabled(True)
                endField.setText(self.locEndName) # restore previous name value
                endField.setPlaceholderText('End Locator Name')
                endBtn.setText('Create End Locator')

    def checkbox_aim_sequence(self, checked:bool):
        ''' Shows or hides the aim constraint numeric fields based on checkbox state. '''
        # store all aim constraint related field IDs and label objects in a single list
        fieldIDs=[*self.aimFieldID, *self.upFieldID, *self.wupFieldID]
        # store label objects for easy visibility toggling
        labelObjs=[self.findChild(QtWidgets.QLabel, 'aimLabel'),
                   self.findChild(QtWidgets.QLabel, 'upLabel'),
                   self.findChild(QtWidgets.QLabel, 'wupLabel')]
        if checked:
            # show and enable aim constraint layout elements
            self.findChild(QtWidgets.QFrame, 'aimFrame').setVisible(True)
            for label in labelObjs:
                label.setVisible(True)
            for field in fieldIDs:
                self.findChild(QtWidgets.QDoubleSpinBox, field).setVisible(True)
                self.findChild(QtWidgets.QDoubleSpinBox, field).setEnabled(True)
            self.findChild(QtWidgets.QPushButton, self.aimWidgetID[1]).setVisible(True)
            self.findChild(QtWidgets.QPushButton, self.aimWidgetID[1]).setEnabled(True)
        else:
            # hide and disable aim constraint layout elements, recompute main layout size
            self.findChild(QtWidgets.QFrame, 'aimFrame').setVisible(False)
            for label in labelObjs:
                label.setVisible(False)
            for field in fieldIDs:
                self.findChild(QtWidgets.QDoubleSpinBox, field).setVisible(False)
                self.findChild(QtWidgets.QDoubleSpinBox, field).setDisabled(True)
            self.findChild(QtWidgets.QPushButton, self.aimWidgetID[1]).setVisible(False)
            self.findChild(QtWidgets.QPushButton, self.aimWidgetID[1]).setDisabled(True)
        self.resize_layout(layout='card')

    def checkbox_orient_sequence(self, checked:bool):
        ''' Shows or hides the joint orientation & rotation order menus based on checkbox state. '''
        # find and store joint orientation related layout & its child widgets
        orientFrame=self.findChild(QtWidgets.QFrame, 'orientFrame')
        orientJntLabel=self.findChild(QtWidgets.QLabel, 'orientJntLabel')
        orientChildCheck=self.findChild(QtWidgets.QCheckBox, 'orientChildCheck')
        orientWorldCheck=self.findChild(QtWidgets.QCheckBox, 'orientWorldCheck')
        orientJntBtn=self.findChild(QtWidgets.QPushButton, 'orientBtn')
        orientJntMenu=self.findChild(QtWidgets.QComboBox, 'orientJntMenu')
        secOrientMenu=self.findChild(QtWidgets.QComboBox, 'secOrientMenu')
        rotOrderLabel=self.findChild(QtWidgets.QLabel, 'rotOrderLabel')
        rotOrderMenu=self.findChild(QtWidgets.QComboBox, 'rotOrderMenu')
        rotOrderBtn=self.findChild(QtWidgets.QPushButton, 'rotOrderBtn')

        if checked:
            orientFrame.setVisible(True)

            orientJntLabel.setVisible(True)
            orientChildCheck.setVisible(True)
            orientChildCheck.setEnabled(True)
            orientWorldCheck.setVisible(True)
            orientWorldCheck.setEnabled(True)

            orientJntMenu.setVisible(True)
            secOrientMenu.setVisible(True)
            orientJntBtn.setVisible(True)
            orientJntBtn.setEnabled(True)
            rotOrderLabel.setVisible(True)
            rotOrderMenu.setVisible(True)
            rotOrderBtn.setVisible(True)
            rotOrderBtn.setEnabled(True)
        else:
            orientFrame.setVisible(False)

            orientJntLabel.setVisible(False)
            orientChildCheck.setVisible(False)
            orientChildCheck.setDisabled(True)
            orientWorldCheck.setVisible(False)
            orientWorldCheck.setDisabled(True)

            orientJntMenu.setVisible(False)
            secOrientMenu.setVisible(False)
            orientJntBtn.setVisible(False)
            orientJntBtn.setDisabled(True)
            rotOrderLabel.setVisible(False)
            rotOrderMenu.setVisible(False)
            rotOrderBtn.setVisible(False)
            rotOrderBtn.setDisabled(True)

        self.resize_layout(layout='card')

    def checkbox_mirror_sequence(self, checked:bool):
        ''' Shows or hides the joint mirroring related fields based on checkbox state. '''
        mirrorFrame=self.findChild(QtWidgets.QFrame, 'mirrorFrame')
        mirrorLabel=self.findChild(QtWidgets.QLabel, 'mirrorLabels')
        mirrorAxisMenu=self.findChild(QtWidgets.QComboBox, 'mirrorAxisMenu')
        mirrorFuncMenu=self.findChild(QtWidgets.QComboBox, 'mirrorFuncMenu')
        replaceLabels=self.findChild(QtWidgets.QLabel, 'replaceLabels')
        searchFieldForm=self.findChild(QtWidgets.QFormLayout, 'searchFieldForm')
        replaceFieldForm=self.findChild(QtWidgets.QFormLayout, 'replaceFieldForm')
        mirrorJntsBtn=self.findChild(QtWidgets.QPushButton, 'mirrorJntsBtn')

        if checked:
            mirrorFrame.setVisible(True)

            mirrorLabel.setVisible(True)
            mirrorAxisMenu.setVisible(True)
            mirrorFuncMenu.setVisible(True)
            replaceLabels.setVisible(True)
            searchFieldForm.setRowVisible(0, True)
            replaceFieldForm.setRowVisible(0, True)
            mirrorJntsBtn.setVisible(True)
        else:
            mirrorFrame.setVisible(False)

            mirrorLabel.setVisible(False)
            mirrorAxisMenu.setVisible(False)
            mirrorFuncMenu.setVisible(False)
            replaceLabels.setVisible(False)
            searchFieldForm.setRowVisible(0, False)
            replaceFieldForm.setRowVisible(0, False)
            mirrorJntsBtn.setVisible(False)

        self.resize_layout(layout='card')

    def enable_jnt_nameField(self, value:bool=True):
        ''' Enables or disables the starting joint name field based on bool value for radio buttons. '''
        jntStartField=self.findChild(QtWidgets.QLineEdit, 'jntStartField')
        if value:
            jntStartField.setPlaceholderText('Starting Joint Name')
            jntStartField.setEnabled(True)
        else:
            jntStartField.setPlaceholderText('Select Starting Joint')
            jntStartField.setDisabled(True)

    def build_locator(self, locBtn:QtWidgets.QPushButton, 
                         locField:QtWidgets.QLineEdit,
                         locCheck:QtWidgets.QCheckBox,
                         sequenceID='start'):
        ''' 
        Handles the buildLocator module to create a locator on the user's selection (mesh, faces, edges or vertices). 
        If a locObjID is passed, finds it's stored position and rebuilds the locator.
        Disables the locator button, field & checkbox upon creation.
        '''
        if sequenceID not in self.available_sequenceID:
            raise ValueError(f'[{sequenceID}] is not an available sequence, use: [{self.available_sequenceID}]')
        # open undo chunk for locator creation
        mc.undoInfo(openChunk=True, chunkName="creativeUI: build_locator")
        try:
            print('Build Locator')
            mc.selectPriority(locator=2, polymesh=1) # set selection priority to locator over mesh

            # create a new locator from selection with user error handling
            locatorName=locField.text()
            if not locatorName:
                mc.warning('Please add a name for your Locator.')
                return
            locPrefix=self.findChild(QtWidgets.QLineEdit, 'locPrefixField').text()
            locSuffix=self.findChild(QtWidgets.QLineEdit, 'locSuffixField').text()
            locObjPos=mc.polyListComponentConversion(mc.ls(selection=True), toVertex=True)
            if not locObjPos:
                mc.warning('No Selection made.')
                return
            locObjID=md.createLocator(locatorName, prefix=locPrefix, suffix=locSuffix)
            md.clusterLocParent(locObjPos, locatorName, locObjID)

            # store locator ID based on the sequence provided 
            if sequenceID=='start':
                self.sortedLocIDs[0]=locObjID
                textID='Start'
            else:
                self.sortedLocIDs[1]=locObjID
                textID='End'
            # store locator ID and position data set for undo/redo operations
            self.locatorSets[locObjID]=locObjPos
            # set locator field text to show created locator ID
            locField.setText(locObjID)
            self.disable_locBtn(locBtn, locField, locCheck)

            # check if both locator buttons are disabled to enable joint chain layout
            self.check_locator_btns_disabled()

            # undo and redo arrow button connections; avoids ghost stacking
            undoArrow, redoArrow = self._reset_arrow_connections()
            undoArrow.setEnabled(True)
            redoArrow.setDisabled(True)

            # connect arrow buttons to handle undo/redo operations
            undoArrow.clicked.connect(lambda args:self.arrow_btn_clicked('undo',
                                                                        locBtn,
                                                                        locField,
                                                                        locCheck,
                                                                        locObjID, text=textID,
                                                                        deleteLoc=True))
            redoArrow.clicked.connect(lambda args:self.arrow_btn_clicked('redo',
                                                                         locBtn,
                                                                         locField,
                                                                         locCheck,
                                                                         locObjID, text=textID))

        finally:
            # close undo chunk for maya stack
            mc.undoInfo(closeChunk=True)

    def store_locator(self, locBtn:QtWidgets.QPushButton, 
                      locField:QtWidgets.QLineEdit,
                      locCheck:QtWidgets.QCheckBox,
                      locObjID=None,
                      sequenceID='start'):
        ''' 
        Handles the storeLocator module to store an existing locator as the user's selection.
        If a locObjID is passed, uses that locator ID instead of the user's selection.
        Disables the locator button, field & checkbox upon storage.
        '''

        if not locObjID:
            # get user's selection and validate that it is a locator
            locSelection=mc.ls(selection=True)
            if not locSelection:
                mc.warning('Please select your locator.')
                return

            if len(locSelection)>1:
                mc.warning('Selection must be only one locator.')
                return
                
            locType=mc.nodeType(mc.listRelatives(locSelection[0], s=True)[0])
            if locType not in self.available_locatorIDs:
                mc.warning('Selection must be of type: locator.')
                return
            locObjID=locSelection[0]

        # store locator ID based on the sequence provided 
        if sequenceID=='start':
            self.sortedLocIDs[0]=locObjID
            textID='Start'
        else:
            self.sortedLocIDs[1]=locObjID
            textID='End'
        # stored locators don't require position data; position data is only needed for created locators
        self.locatorSets[locObjID]=None
        # set locator field text to show stored locator ID
        locField.setText(locObjID)
        self.disable_locBtn(locBtn, locField, locCheck)

        # check if both locator buttons are disabled to enable joint chain layout
        self.check_locator_btns_disabled()

        # undo and redo arrow button connections; avoids ghost stacking
        undoArrow, redoArrow = self._reset_arrow_connections()
        undoArrow.setEnabled(True)
        redoArrow.setDisabled(True)

        # connect arrow buttons to handle undo/redo operations
        undoArrow.clicked.connect(lambda args:self.arrow_btn_clicked('undo',
                                                                    locBtn,
                                                                    locField,
                                                                    locCheck, 
                                                                    locObjID, text=textID))
        redoArrow.clicked.connect(lambda args:self.arrow_btn_clicked('redo',
                                                                    locBtn,
                                                                    locField,
                                                                    locCheck,
                                                                    locObjID, text=textID))
        mc.select(clear=True)

    def aim_locators(self):
        ''' Sets up an aim constraint between two locators based on aim constraint numeric fields. '''
        
        # store value set for corresponding aim constraint flag
        aimVector=[self.findChild(QtWidgets.QDoubleSpinBox, self.aimFieldID[0]).value(),
                   self.findChild(QtWidgets.QDoubleSpinBox, self.aimFieldID[1]).value(),
                   self.findChild(QtWidgets.QDoubleSpinBox, self.aimFieldID[2]).value()]
        
        upVector=[self.findChild(QtWidgets.QDoubleSpinBox, self.upFieldID[0]).value(),
                  self.findChild(QtWidgets.QDoubleSpinBox, self.upFieldID[1]).value(),
                  self.findChild(QtWidgets.QDoubleSpinBox, self.upFieldID[2]).value()]
        
        wupVector=[self.findChild(QtWidgets.QDoubleSpinBox, self.wupFieldID[0]).value(),
                   self.findChild(QtWidgets.QDoubleSpinBox, self.wupFieldID[1]).value(),
                   self.findChild(QtWidgets.QDoubleSpinBox, self.wupFieldID[2]).value()]
        
        # check if locators were created or stored via selection
        if self.sortedLocIDs[0] == 'none' or self.sortedLocIDs[1] == 'none':
            # aim constraint setup via user selection
            locatorSelection=mc.ls(selection=True)
            if not locatorSelection:
                mc.warning('No locator selection made.')
                return
            # validate that exactly two locators have been selected
            startLocShp=mc.nodeType(mc.listRelatives(locatorSelection[0], s=True)[0])
            endLocShp=mc.nodeType(mc.listRelatives(locatorSelection[1], s=True)[0])
            if startLocShp not in self.available_locatorIDs or endLocShp not in self.available_locatorIDs: 
                mc.warning('Selection must only be two Locators for aim constraint setup.')
                return
            else:
                selStartLoc, selEndLoc = locatorSelection[0], locatorSelection[1]
                mc.aimConstraint(selEndLoc, selStartLoc, aim=aimVector, u=upVector, wu=wupVector)
                # create negative aim vector for end locator to aim at start locator
                negAimVector=[val*(-1) for val in aimVector]
                mc.aimConstraint(selStartLoc, selEndLoc, aim=negAimVector, u=upVector, wu=wupVector)
        else:
            # aim constraint setup via created/stored locators
            md.aimLocators(self.sortedLocIDs[0], self.sortedLocIDs[1], 
                           aimVector=aimVector, upVector=upVector, worldUpVector=wupVector)

    def orient_bnt_clicked(self):
        ''' Queries joint orientation checkbox values and calls orient_joints method. '''
        jointSelection=mc.ls(selection=True, type='joint')
        if not jointSelection:
            mc.warning('No Joint selection made.')
            return
        orientChildrenVal=self.findChild(QtWidgets.QCheckBox, 'orientChildCheck').isChecked()
        orientWorldVal=self.findChild(QtWidgets.QCheckBox, 'orientWorldCheck').isChecked()
        self.orient_joints(jointSelection, 
                           orientChildrenVal, orientWorldVal)

    def orient_joints(self, jointSelection, 
                      children:bool=True, jntToWorld:bool=False):
        ''' Orients selected joints with user provided settings. '''
        if jntToWorld:
            mc.joint(jointSelection, edit=True,
                     orientJoint='none', children=children)
        else:
            orientJoint=self.findChild(QtWidgets.QComboBox, 'orientJntMenu').currentText()
            secAxis=self.findChild(QtWidgets.QComboBox, 'secOrientMenu').currentText()
            mc.joint(jointSelection, edit=True, 
                     orientJoint=orientJoint, secondaryAxisOrient=secAxis, children=children)
        
    def joints_rotOrder(self):
        ''' Sets the rotation order for the selected joints based on user menu selection. '''
        jointSelection=mc.ls(selection=True, type='joint')
        if not jointSelection:
            mc.warning('No Joint selection made.')
            return
        rotOrder=self.findChild(QtWidgets.QComboBox, 'rotOrderMenu').currentText()
        mc.joint(jointSelection, edit=True, rotationOrder=rotOrder, children=True)

    def mirror_joints(self):
        ''' Handles the mirrorJoints module to mirror selected joints based on user settings. '''
        mirrorAxisVal=self.findChild(QtWidgets.QComboBox, 'mirrorAxisMenu').currentText()
        mirrorFuncVal=self.findChild(QtWidgets.QComboBox, 'mirrorFuncMenu').currentText()
        searchFieldVal=self.findChild(QtWidgets.QLineEdit, 'searchField').text()
        replaceFieldVal=self.findChild(QtWidgets.QLineEdit, 'replaceField').text()

        mirroredJnts=md.mirrorJoints(mirrorAxis=mirrorAxisVal, mirrorFunc=mirrorFuncVal,
                                     search=searchFieldVal, replace=replaceFieldVal)
        if not mirroredJnts:
            mc.warning('No Joint selection made.')
            return
        
        return mirroredJnts

    def build_joint_chain(self):
        ''' Handles the buildJointChain module to create a joint chain between the two created locators. '''
        # find and store joint chain related fields
        jointCount=self.findChild(QtWidgets.QSpinBox, 'jntCountField')
        orientCheck=self.findChild(QtWidgets.QCheckBox, 'orientCheck')
        jntStartField=self.findChild(QtWidgets.QLineEdit, 'jntStartField')
        jntEndField=self.findChild(QtWidgets.QLineEdit, 'jntEndField')
        startParentCheck=self.findChild(QtWidgets.QRadioButton, 'startParentCheck')
        continueParentCheck=self.findChild(QtWidgets.QRadioButton, 'continueParentCheck')

        if startParentCheck.isChecked():
            # get starting joint name from user selection
            startJntName=mc.ls(selection=True, type='joint')
            # validate that only a single joint has been selected
            if not startJntName or len(startJntName) !=1 or mc.objectType(startJntName[0]) != 'joint':
                mc.warning('Please select only one Joint to be the starting Joint.')
                return
            startJntName=startJntName[0]
        else:
            startJntName=jntStartField.text()
            # validate that user has provided a start joint name before continuing
            if not startJntName:
                mc.warning('Please set a name for the Start Joint.')
                return
        # validate that user has provided an end joint name before continuing
        endJntName=jntEndField.text()
        if not endJntName:
            mc.warning('Please set a name for the End Joint.')
            return

        if self.jntMidFields:
            # get the text values of each created middle joint field and store it 
            midJntNames=[]
            # validate that middle fields contain text value
            for jntMidField in self.jntMidFields:
                midJntName=jntMidField.text()
                if not midJntName:
                    mc.warning('Please set a name for each of the Middle Joints')
                    return
                midJntNames.append(midJntName)
            # store middle names in between the start and end name items
            jntNames=[startJntName, *midJntNames, endJntName]
        else:
            jntNames=[startJntName, endJntName]

        if continueParentCheck.isChecked():
            # get parent joint from user selection
            parentJnt=mc.ls(selection=True, type='joint')
            # validate that only a single joint has been selected
            if not parentJnt or len(parentJnt) !=1 or mc.objectType(parentJnt[0]) != 'joint':
                mc.warning('Please select only one joint to parent.')
                return
            parentJnt=parentJnt[0]
        else:
            parentJnt=None

        # query the world space position of both locators
        startLocPos=mc.xform(self.sortedLocIDs[0], query=True, ws=True, t=True)
        endLocPos=mc.xform(self.sortedLocIDs[1], query=True, ws=True, t=True)
        # convert to MPoint values
        startLocPoint=om2.MPoint(startLocPos)
        endLocPoint=om2.MPoint(endLocPos)
        overrideTempColor=4

        jntPrefix=self.findChild(QtWidgets.QLineEdit, 'jntPrefixField').text()
        jntSuffix=self.findChild(QtWidgets.QLineEdit, 'jntSuffixField').text()
        if orientCheck.isChecked():
            orientJoint=self.findChild(QtWidgets.QComboBox, 'orientJntMenu').currentText()
            secAxis=self.findChild(QtWidgets.QComboBox, 'secOrientMenu').currentText()
            rotOrder=self.findChild(QtWidgets.QComboBox, 'rotOrderMenu').currentText()
            # build joint chain with orientation and rotation order settings
            joints=md.buildJointChain(startLocPoint, endLocPoint, jntNames=jntNames,
                                      jntNums=jointCount.value(), parentJnt=parentJnt,
                                      orientJoint=orientJoint, secAxisOrient=secAxis,
                                      rotationOrder=rotOrder, 
                                      prefix=jntPrefix, suffix=jntSuffix,
                                      overrideColor=overrideTempColor)
        else:
            # build joint chain in the direction of the start and end locators
            joints=md.buildJointChain(startLocPoint, endLocPoint, jntNames=jntNames,
                                      jntNums=jointCount.value(), parentJnt=parentJnt,
                                      prefix=jntPrefix, suffix=jntSuffix,
                                      overrideColor=overrideTempColor)
        self.sortedJntIDs=joints
        print('Joint Chain Built')

        # set up parent constraint from locator to joint if checkbox has been checked
        parentConstrain=self.findChild(QtWidgets.QCheckBox, 'parentConstCheck')
        if parentConstrain.isChecked():
            mc.parentConstraint(self.sortedLocIDs[0], self.sortedJntIDs[0]) # type: ignore
            mc.parentConstraint(self.sortedLocIDs[1], self.sortedJntIDs[-1]) # type: ignore
        
        # swap the joint builder button for the commit button
        self.show_or_hide_joint_count(hideLayout=True, hideButton=True)
        self.show_or_hide_commitLayout()
        
        # disconnect restart undo/redo commands to avoid ghost stacking
        undoArrow = self._reset_arrow_connections()[0]
        undoArrow.setDisabled(True)
        
    def commit_jnt_structure(self):
        ''' 
        Start and End Joint create a parent constraint to their respective Locator.
        Should only be called as the last step in Joint builder as it resets UI and data. 
        '''
        # validate joints and locators exists
        if self.sortedLocIDs[0] == 'none' or self.sortedLocIDs[1] == 'none':
            raise KeyError('Cannot commit structure: locator ID data is insufficient, missing or has been deleted.')
        if len(self.sortedJntIDs) < 2:
            raise KeyError('Cannot commit structure: joint ID data is insufficient, missing or has been deleted.')
        # create parent constraint from start and end locators to their respective joints
        md.jointLocParent(self.sortedJntIDs[0], self.sortedLocIDs[0]) # type: ignore
        md.jointLocParent(self.sortedJntIDs[-1], self.sortedLocIDs[-1]) # type: ignore

        # zero out starting joint transformation values (translate, rotate, scale, normal)
        mc.makeIdentity(self.sortedJntIDs[0], apply=True,
                        translate=True, rotate=True, scale=True)
        
        # store orientation and rotation order settings based on menus, other wise they are left as default      
        orientJoint=self.findChild(QtWidgets.QComboBox, 'orientJntMenu').currentText()
        secAxis=self.findChild(QtWidgets.QComboBox, 'secOrientMenu').currentText()
        rotOrder=self.findChild(QtWidgets.QComboBox, 'rotOrderMenu').currentText()
        print((orientJoint, secAxis, rotOrder))

        mc.joint(self.sortedJntIDs, edit=True, orientJoint=orientJoint,
                 secondaryAxisOrient=secAxis, rotationOrder=rotOrder, children=True)
        
        # make end joint orient to world and have same orientation as previous/parent joint
        mc.joint(self.sortedJntIDs[-1], edit=True, orientJoint='none', children=True)

        mirrorCheck=self.findChild(QtWidgets.QCheckBox, 'mirrorJntsCheck')
        if mirrorCheck.isChecked():
            # mirror the joint chain with user settings
            mc.select(self.sortedJntIDs[0])
            mirroredJnts=self.mirror_joints()
            print(mirroredJnts)
            mirrorLoc1=md.createLocator(mirroredJnts[0], suffix='_loc')

            mirrorLoc2=md.createLocator(mirroredJnts[-1], suffix='_loc')

            md.jointLocParent(mirroredJnts[0], mirrorLoc1)
            md.jointLocParent(mirroredJnts[-1], mirrorLoc2)
            mc.select(clear=True)

        # reset UI to initial state and clear data
        self.close_dialog_window()

        self.delete_data()
        self.show_or_hide_commitLayout(hide=True)
        self.enable_locBtn(self.findChild(QtWidgets.QPushButton, 'startLocBtn'), 
                           self.findChild(QtWidgets.QLineEdit, 'startLocField'), 
                           self.findChild(QtWidgets.QCheckBox, 'startLocCheck'),
                           buttonText='Create Start Locator')
        self.enable_locBtn(self.findChild(QtWidgets.QPushButton, 'endLocBtn'), 
                           self.findChild(QtWidgets.QLineEdit, 'endLocField'), 
                           self.findChild(QtWidgets.QCheckBox, 'endLocCheck'),
                           buttonText='Create End Locator')
        jntBuilderBtn=self.findChild(QtWidgets.QPushButton, 'jntBuilderBtn')
        jntBuilderBtn.setVisible(True)
        jntBuilderBtn.setDisabled(True)
        self.show_or_hide_prefixSuffix_fields()

    def show_dialog_window(self):
        ''' 
        Creates and shows dialog window to confirm or continue editing joint structure.
        Window is used as pre-check in case user doesn't want to commit yet.
        '''
        # close the dialog window in-case an previous instance already exists
        self.close_dialog_window()
        # build dialog window with a vertical layout 
        dialogWindow=QtWidgets.QDialog(self)
        dialogWindow.setObjectName('dialogWindow')
        dialogWindow.setWindowTitle(self.WINDOW_TITLE)

        dialogLayout=self.layouts.create_or_get_verticalLayout('dialogLayout', dialogWindow, spacing=3, contentMargins=(5,5,5,5))

        infoText='Commit to Joint Structure?\n' \
                'Important: Commit removes parent and aim constraint from Joints and Locators respectively.\n' \
                'Start and End Joint create a parent constraint to their respective Locator.'
        self.widgets.create_label('dialogInfoText', infoText, dialogLayout, align=QtCore.Qt.AlignHCenter)

        # create buttons to confirm or deny process, aligned to the right side of the window
        buttonLayout=self.layouts.create_or_get_gridLayout('buttonLayout', dialogWindow)
        buttonLayout.setAlignment(QtCore.Qt.AlignRight)
        dialogLayout.addLayout(buttonLayout)

        self.widgets.create_button('backBtn', 'Continue Editing', buttonLayout, clickedCmd=self.close_dialog_window)
        self.widgets.create_button('confirmBtn', 'Confirm', buttonLayout, gridSet=(0,1), 
                                           clickedCmd=self.commit_jnt_structure)

        dialogWindow.show()

    def close_dialog_window(self):
        ''' Deletes any existing dialog window instances. '''
        dialogWindows=self.findChildren(QtWidgets.QDialog, 'dialogWindow')
        if dialogWindows:
            for outdated in dialogWindows:
                outdated.close()

    def _apply_style(self):
        mainBG="#222325"
        cardBG="#222325"

        buttonBG="#B4753A"
        buttonPress="#995E26"

        boxBG="#6B6866"
        boxFrame="#8C8886"

        frameColor="#C07733"
        accent="#D7CEC5"
        
        disabledColor="#2C3035"
        disabledText="#5E636A"

        checkIcon=os.path.join(self.baseDirectory, 'creativeLibrary', 
                               'icons', 'menuIconSelect_24.png')
        checkIcon.replace('\\', '/')
        print(checkIcon)
        aim='aimConstraint.png'
        orient='orientJoint.png'

        self.setStyleSheet(f"""
        QWidget#{WINDOW_ID} {{
            background: {mainBG};
            border: 1px solid #3a3d44;
            border-radius: 5px;
        }}
        QFrame#cardFrame {{
            background: {cardBG};
            border: 2px solid #3a3d44;
            border-radius: 10px;
            border-top: 2px solid {frameColor};
            border-bottom: 2px solid {frameColor};
        }}

        QFrame#aimFrame {{
            background: {cardBG};
            border: 2px dashed #3a3d44;
            border-radius: 10px;
            border-top: 2px solid {frameColor};
            border-bottom: 2px solid {frameColor};
        }}
        QFrame#orientFrame {{
            background: {cardBG};
            border: 2px dashed #3a3d44;
            border-radius: 10px;
            border-top: 2px solid {frameColor};
            border-bottom: 2px solid {frameColor};
        }}
        QFrame#mirrorFrame {{
            background: {cardBG};
            border: 2px dashed #3a3d44;
            border-radius: 10px;
            border-top: 2px solid {frameColor};
            border-bottom: 2px solid {frameColor};
        }}

        QLabel {{
            font-size: 13px;
            color: #ffffff;
        }}

        QCheckBox {{
            spacing: 4.5px;
            font-size: 13px;
            color: #FFFFFF;
        }}
        QCheckBox:hover {{
            color: {accent};
        }}
        QCheckBox::indicator {{
            width: 11px;
            height: 11px;
            background-color: {boxBG};
            border-radius: 2px;
            border: 1px solid {frameColor};
        }}
        QCheckBox::indicator:hover {{
            border: 1px solid {accent};
        }}
        QCheckBox::indicator:checked {{
            image: url(:/UVEditorIsolate.png);
        }}

        QRadioButton {{
            spacing: 4.5px;
            font-size: 12px;
            color: #FFFFFF;
        }}
        QRadioButton:hover {{
            color: {accent};
        }}
        QRadioButton::indicator {{
            width: 10px;
            height: 10px;
            background-color: {boxBG};
            border-radius: 5px;
            border: 1px solid {frameColor};
        }}
        QRadioButton::indicator:hover {{
            border: 1px solid {accent};
        }}
        QRadioButton::indicator:checked {{
            width: 10px;
            height: 10px;
            background-color: {accent};
            border-radius: 5px;
            border-color: gray;
        }}

        QLineEdit {{
            font-size: 13px;
            border: 2px solid {boxFrame};
            background: {boxBG};
            border-radius: 12px;
            padding: 6px 10px;
            color: #ffffff;
            selection-background-color: {accent};
        }}
        QLineEdit:focus {{
            border: 2px solid {accent};
        }}
        QLineEdit:disabled {{
            background: {disabledColor};
            border: 2px solid {disabledColor};
            color: {disabledText};
        }}

        QPushButton {{
            font-size: 13px;
            border: 2px solid {frameColor};
            background: {buttonBG};
            border-radius: 8px;
            padding: 7px 12px;
            color: #ffffff;
        }}
        QPushButton:hover {{
            border: 2px solid {accent};
        }}
        QPushButton:pressed {{
            background: {buttonPress};
        }}
        QPushButton:disabled {{
            background: {disabledColor};
            border: 2px solid {disabledColor};
            color: {disabledText};
        }}

        QComboBox {{
            font-size: 13px;
            border: 2px solid {boxFrame};
            background: {boxBG};
            border-radius: 5px;
            color: #ffffff;
        }}
        QComboBox:hover {{
            border: 2px solid {accent};
        }}
        QComboBox:focus {{
            border: 2px solid {accent};
        }}
        QComboBox:disabled {{
            background: {disabledColor};
            border: 2px solid {disabledColor};
            color: {disabledText};
        }}
        QComboBox::down-arrow {{
            width: 8px;
            height: 8px;
            color: #ffffff;
        }}

        QComboBox QAbstractItemView {{
            background: {mainBG};
            color: #ffffff;
            selection-background-color: {buttonBG};
            border: 1px solid #3a3d44;
        }}

        QSpinBox {{
            font-size: 11px;
            border: 1px solid {frameColor};
            background: {boxBG};
            border-radius: 5px;
            color: #ffffff;
            selection-background-color: {buttonBG};
        }}
        QSpinBox:focus {{
            border: 1px solid {accent};
        }}
        QSpinBox:disabled {{
            background: {disabledColor};
            border: 1px solid {disabledColor};
            color: {disabledText};
        }}

        QDoubleSpinBox {{
            font-size: 11px;
            border: 1px solid {frameColor};
            background: {boxBG};
            border-radius: 5px;
            color: #ffffff;
            selection-background-color: {buttonBG};
        }}
        QDoubleSpinBox:focus {{
            border: 1px solid {accent};
        }}
        QDoubleSpinBox:disabled {{
            background: {disabledColor};
            border: 1px solid {disabledColor};
            color: {disabledText};
        }}

        QSlider::groove:horizontal{{
            height: 4px;
            background: #ffffff;
            border-radius: 2px;
        }}
        QSlider::handle:horizontal{{
            width: 16px;
            height: 16px;
            margin: -6px 0;
            background: {buttonBG};
            border: 2px solid {frameColor};
            border-radius: 6px;
        }}
        QSlider::handle:horizontal:hover {{
            border: 2px solid {accent};
        }}
        """)

    def _reset_arrow_connections(self):
        ''' Private method to disconnect undo/redo arrow button signals for repeated use. '''
        undoArrow = self.findChild(QtWidgets.QToolButton, 'undoArrow')
        redoArrow = self.findChild(QtWidgets.QToolButton, 'redoArrow')

        for arrowBtn in (undoArrow, redoArrow):
            try:
                arrowBtn.clicked.disconnect()
            except (RuntimeError, TypeError):
                pass # nothing has been connected

        return undoArrow, redoArrow
    
