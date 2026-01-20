from PySide6 import QtCore, QtWidgets

class wrapLay():
    ''' A wrapper class for commonly used Qt Layouts, gets the layout if it already exists. '''
    def __init__(self, parentUI:QtWidgets.QWidget):
        ''' Initializes the QWidget methods, parented to the called UI. '''
        self.parentUI=parentUI
        
    def create_or_get_verticalLayout(self, layoutID:str,  
                                     parentWidget:QtWidgets.QWidget|None=None,
                                     parentLayout:QtWidgets.QBoxLayout|QtWidgets.QGridLayout|None=None,
                                     spacing=5, contentMargins:tuple[int,int,int,int]=(0,0,0,0)):
        ''' Returns a built or obtained QVBoxLayout based on the layoutID. '''
        if not parentWidget:
            parentWidget=self.parentUI

        boxLayout=parentWidget.findChild(QtWidgets.QVBoxLayout, layoutID)
        if not boxLayout:
            boxLayout=QtWidgets.QVBoxLayout(parentWidget)
            boxLayout.setObjectName(layoutID)
            if parentLayout:
                parentLayout.addLayout(boxLayout)
        boxLayout.setSpacing(spacing)
        boxLayout.setContentsMargins(*contentMargins)
        
        return boxLayout

    def create_or_get_horizontalLayout(self, layoutID:str,
                                       parentWidget:QtWidgets.QWidget|None=None,
                                       parentLayout:QtWidgets.QBoxLayout|QtWidgets.QGridLayout|None=None,
                                       spacing=5, contentMargins:tuple[int,int,int,int]=(0,0,0,0)):
        ''' Returns a built or obtained QHBoxLayout based on the layoutID. '''
        if not parentWidget:
            parentWidget=self.parentUI

        boxLayout=parentWidget.findChild(QtWidgets.QHBoxLayout, layoutID)
        if not boxLayout:
            boxLayout=QtWidgets.QHBoxLayout(parentWidget)
            boxLayout.setObjectName(layoutID)
            if parentLayout:
                parentLayout.addLayout(boxLayout)
        boxLayout.setSpacing(spacing)
        boxLayout.setContentsMargins(*contentMargins)
        
        return boxLayout

    def create_or_get_gridLayout(self, layoutID:str, 
                                 parentWidget:QtWidgets.QWidget|None=None,
                                 parentLayout:QtWidgets.QBoxLayout|QtWidgets.QGridLayout|None=None,
                                 contentMargins:tuple[float,float,float,float]=(0,0,0,0)):
        ''' Returns a built or obtained QGridLayout based on the layoutID. '''
        if not parentWidget:
            parentWidget=self.parentUI

        gridLayout=parentWidget.findChild(QtWidgets.QGridLayout, layoutID)
        if not gridLayout:
            gridLayout=QtWidgets.QGridLayout(parentWidget)
            gridLayout.setObjectName(layoutID)
            if parentLayout:
                parentLayout.addLayout(gridLayout)
        
        gridLayout.setContentsMargins(*contentMargins)

        return gridLayout
    
class collapsibleFrame(QtWidgets.QWidget):
    toggled = QtCore.Signal(bool)
    def __init__(self, parentUI:QtWidgets.QWidget, expanded:bool=True, title=""):
        super().__init__(parentUI)
        
        self._expanded = expanded

        # --- Header button (click anywhere on the header)
        self.header_btn = QtWidgets.QToolButton()
        self.header_btn.setText(title)
        self.header_btn.setCheckable(True)
        self.header_btn.setChecked(expanded)
        self.header_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.header_btn.setArrowType(QtCore.Qt.DownArrow if expanded else QtCore.Qt.RightArrow)
        self.header_btn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.header_btn.setAutoRaise(True)

        # --- Content area (put any layout/widgets inside)
        self.content_widget = QtWidgets.QWidget()
        self.content_layout = QtWidgets.QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(12, 6, 6, 6)  # small indent like Maya
        self.content_layout.setSpacing(4)
        self.content_widget.setVisible(expanded)

        # --- Main layout
        main = QtWidgets.QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)
        main.addWidget(self.header_btn)
        main.addWidget(self.content_widget)

        self.header_btn.clicked.connect(self.set_expanded)

    def set_expanded(self, expanded:bool):
        self._expanded = bool(expanded)
        self.content_widget.setVisible(self._expanded)
        if self._expanded:
            self.header_btn.setArrowType(QtCore.Qt.DownArrow)
        else:
            self.header_btn.setArrowType(QtCore.Qt.RightArrow)
        self.toggled.emit(self._expanded)

    def is_expanded(self) -> bool:
        return self._expanded
    
