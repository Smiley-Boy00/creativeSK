from PySide6 import QtCore, QtWidgets

class wrapLay(QtWidgets.QWidget):
    ''' A wrapper class for commonly used Qt Layouts, gets the layout if it already exists. '''
    def __init__(self, parentUI):
        ''' Initializes the QWidget methods, parented to the called UI. '''
        super(wrapLay, self).__init__(parent=parentUI)
        
    def create_or_get_verticalLayout(self, layoutID:str, 
                                     parentWidget:QtWidgets.QWidget, 
                                     parentLayout:QtWidgets.QBoxLayout|QtWidgets.QGridLayout|None=None,
                                     spacing=5, contentMargins:tuple[int,int,int,int]=(0,0,0,0)):
        ''' Returns a built or obtained QVBoxLayout based on the layoutID. '''

        boxLayout=self.findChild(QtWidgets.QVBoxLayout, layoutID)
        if not boxLayout:
            boxLayout=QtWidgets.QVBoxLayout(parentWidget)
            boxLayout.setObjectName(layoutID)
            if parentLayout:
                parentLayout.addLayout(boxLayout)
        boxLayout.setSpacing(spacing)
        boxLayout.setContentsMargins(*contentMargins)
        
        return boxLayout

    def create_or_get_horizontalLayout(self, layoutID:str, 
                                       parentWidget:QtWidgets.QWidget, 
                                       parentLayout:QtWidgets.QBoxLayout|QtWidgets.QGridLayout|None=None,
                                       spacing=5, contentMargins:tuple[int,int,int,int]=(0,0,0,0)):
        ''' Returns a built or obtained QHBoxLayout based on the layoutID. '''

        boxLayout=self.findChild(QtWidgets.QHBoxLayout, layoutID)
        if not boxLayout:
            boxLayout=QtWidgets.QHBoxLayout(parentWidget)
            boxLayout.setObjectName(layoutID)
            if parentLayout:
                parentLayout.addLayout(boxLayout)
        boxLayout.setSpacing(spacing)
        boxLayout.setContentsMargins(*contentMargins)
        
        return boxLayout

    def create_or_get_gridLayout(self, layoutID:str, 
                                 parentWidget:QtWidgets.QWidget, 
                                 parentLayout:QtWidgets.QBoxLayout|QtWidgets.QGridLayout|None=None,
                                 contentMargins:tuple[float,float,float,float]=(0,0,0,0)):
        ''' Returns a built or obtained QGridLayout based on the layoutID. '''

        gridLayout=self.findChild(QtWidgets.QGridLayout, layoutID)
        if not gridLayout:
            gridLayout=QtWidgets.QGridLayout(parentWidget)
            gridLayout.setObjectName(layoutID)
            if parentLayout:
                parentLayout.addLayout(gridLayout)
        
        gridLayout.setContentsMargins(*contentMargins)

        return gridLayout
    
class collapsibleFrame(QtWidgets.QWidget):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        
        self.toggle_button = QtWidgets.QToolButton()
        self.toggle_button.setText(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.toggle_button.setStyleSheet("QToolButton { border: none; }")
        self.toggle_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(QtCore.Qt.RightArrow)
        self.toggle_button.clicked.connect(self.on_toggle)
        
        self.content_area = QtWidgets.QFrame()
        self.content_area.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.content_area.setVisible(False)
        
        self.content_layout = QtWidgets.QVBoxLayout()
        self.content_area.setLayout(self.content_layout)
        
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(self.toggle_button)
        main_layout.addWidget(self.content_area)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
    
    def on_toggle(self):
        if self.toggle_button.isChecked():
            self.toggle_button.setArrowType(QtCore.Qt.DownArrow)
            self.content_area.setVisible(True)
        else:
            self.toggle_button.setArrowType(QtCore.Qt.RightArrow)
            self.content_area.setVisible(False)
    
    def addWidget(self, widget):
        self.content_layout.addWidget(widget)

    def addLayout(self, layout):
        self.content_layout.addLayout(layout)