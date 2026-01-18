from PySide6 import QtCore, QtWidgets

class wrapWid(QtWidgets.QWidget):
    ''' A wrapper class for commonly used Qt Widgets, gets the widget if it already exists. '''
    def __init__(self, parentUI):
        ''' Initializes the QWidget methods, parented to the called UI. '''
        super(wrapWid, self).__init__(parent=parentUI)

    def create_or_show_button(self, widgetID:str, label:str,
                        parentLayout:QtWidgets.QBoxLayout|QtWidgets.QGridLayout,
                        enabled:bool=True, visible:bool=True,
                        margins:tuple[int,int,int,int]=(0,0,0,0), 
                        gridSet:tuple[int,int]=(0,0), clickedCmd=None):
        ''' Returns a built or obtained QPushButton widget based on the widgetID. '''

        buttonWidget=self.findChild(QtWidgets.QPushButton, widgetID)
        if not buttonWidget:
            buttonWidget=QtWidgets.QPushButton(label)
            buttonWidget.setObjectName(widgetID)
            if clickedCmd:
                buttonWidget.clicked.connect(clickedCmd)

        buttonWidget.setContentsMargins(*margins)
        if not visible:
            buttonWidget.hide()
        buttonWidget.setEnabled(enabled)
        if isinstance(parentLayout, QtWidgets.QGridLayout):
            parentLayout.addWidget(buttonWidget, gridSet[0], gridSet[1])
        else:
            parentLayout.addWidget(buttonWidget)
        return buttonWidget

    def create_or_show_arrowButton(self, widgetID:str, 
                                   parentLayout:QtWidgets.QBoxLayout|QtWidgets.QGridLayout,
                                   direction:str='left', enabled:bool=True, visible:bool=True, 
                                   iconSize:QtCore.QSize=QtCore.QSize(15,15),
                                   styleSheet:str='', gridSet:tuple[int,int]=(0,0)):
        ''' Returns a built or obtained QToolButton as an arrow widget based on the widgetID. '''
        arrow_types={'left':QtCore.Qt.LeftArrow, 'right':QtCore.Qt.RightArrow,
                     'up':QtCore.Qt.UpArrow, 'down':QtCore.Qt.DownArrow}
        if not arrow_types.get(direction):
            raise ValueError(f'{direction} is not a valid arrow direction, use: ["left", "right", "up", "down"]')
        arrowButtonWidget=self.findChild(QtWidgets.QToolButton, widgetID)
        if not arrowButtonWidget:
            arrowButtonWidget=QtWidgets.QToolButton()
            arrowButtonWidget.setObjectName(widgetID)
            arrowButtonWidget.setArrowType(arrow_types.get(direction))
            arrowButtonWidget.setIconSize(iconSize)
            if styleSheet:
                arrowButtonWidget.setStyleSheet(styleSheet)

        if not visible:
            arrowButtonWidget.hide()
        arrowButtonWidget.setEnabled(enabled)
        if isinstance(parentLayout, QtWidgets.QGridLayout):
            parentLayout.addWidget(arrowButtonWidget, gridSet[0], gridSet[1])
        else:
            parentLayout.addWidget(arrowButtonWidget)
        return arrowButtonWidget

    def create_or_show_numField(self, widgetID:str, parentLayout:QtWidgets.QBoxLayout|QtWidgets.QGridLayout,
                                type='int', label:str='', numVal:int|float=0, minVal:int|float=0, maxVal:int|float=10,
                                enabled:bool=True, visible:bool=True, width=50,
                                margins:tuple[int,int,int,int]=(0,0,0,0), 
                                gridSet:tuple[int,int]=(0,0), align=None):
        ''' Returns a built or obtained QSpinBox or QDoubleSpinBox widget based on the widgetID. '''

        available_type=['int', 'float']
        if type not in available_type:
            raise ValueError(f'{type} is not a valid Num Field type, use: {available_type}')
        if type=='int':
            numField=QtWidgets.QSpinBox
        else:
            numField=QtWidgets.QDoubleSpinBox
        fieldWidget=self.findChild(numField, widgetID)
        if not fieldWidget:
            fieldWidget=numField()
            fieldWidget.setObjectName(widgetID)

        fieldWidget.setMinimum(minVal)
        fieldWidget.setMaximum(maxVal)
        fieldWidget.setValue(numVal)
        fieldWidget.setMinimumWidth(width)
        fieldWidget.setContentsMargins(*margins)
        if align:
            fieldWidget.setAlignment(align)
        if not visible:
            fieldWidget.hide()
        fieldWidget.setEnabled(enabled)
        formLayout=QtWidgets.QFormLayout()
        formLayout.addRow(label, fieldWidget)
        if isinstance(parentLayout, QtWidgets.QGridLayout):
            parentLayout.addLayout(formLayout, gridSet[0], gridSet[1])
        else:
            parentLayout.addLayout(formLayout)
            
        return fieldWidget

    def create_or_show_textField(self, widgetID:str, label:str,
                                 parentLayout:QtWidgets.QBoxLayout|QtWidgets.QGridLayout, 
                                 placeholderText:str='', enabled:bool=True, visible:bool=True, 
                                 margins:tuple[int,int,int,int]=(0,0,0,0), 
                                 gridSet:tuple[int,int]=(0,0), align=None):
        ''' Returns a built or obtained QLineEdit widget based on the widgetID. '''
        
        fieldWidget=self.findChild(QtWidgets.QLineEdit, widgetID)
        if not fieldWidget:
            fieldWidget=QtWidgets.QLineEdit()
            fieldWidget.setObjectName(widgetID)

        fieldWidget.setPlaceholderText(placeholderText)
        fieldWidget.setContentsMargins(*margins)
        if align:
            fieldWidget.setAlignment(align)
        if not visible:
            fieldWidget.hide()
        fieldWidget.setEnabled(enabled)
        formLayout=QtWidgets.QFormLayout()
        formLayout.addRow(label, fieldWidget)
        if isinstance(parentLayout, QtWidgets.QGridLayout):
            parentLayout.addLayout(formLayout, gridSet[0], gridSet[1])
        else:
            parentLayout.addLayout(formLayout)
        return fieldWidget

    def create_or_show_checkbox(self, widgetID:str, label:str,
                                 parentLayout:QtWidgets.QBoxLayout|QtWidgets.QGridLayout,
                                 enabled:bool=True, visible:bool=True, value:bool=False, 
                                 gridSet:tuple[int,int]=(0,0), align=None,
                                 clickedCmd=None):
        ''' Returns a built or obtained QCheckBox widget based on the widgetID. '''
        
        checkboxWidget=self.findChild(QtWidgets.QCheckBox, widgetID)
        if not checkboxWidget:
            checkboxWidget=QtWidgets.QCheckBox(label)
            checkboxWidget.setObjectName(widgetID)
            if clickedCmd:
                checkboxWidget.clicked.connect(clickedCmd)

        if not visible:
            checkboxWidget.hide()
        checkboxWidget.setChecked(value)
        checkboxWidget.setEnabled(enabled)
        if isinstance(parentLayout, QtWidgets.QGridLayout):
            if align:
                parentLayout.addWidget(checkboxWidget, gridSet[0], gridSet[1], align)
            else:
                parentLayout.addWidget(checkboxWidget, gridSet[0], gridSet[1])
        else:
            parentLayout.addWidget(checkboxWidget)
        return checkboxWidget

    def create_or_show_radialButton(self, widgetID:str, label:str,
                                    parentLayout:QtWidgets.QBoxLayout|QtWidgets.QGridLayout,
                                    enabled:bool=True, visible:bool=True, value:bool=False, 
                                    gridSet:tuple[int,int]=(0,0), align=None,
                                    clickedCmd=None):
        ''' Returns a built or obtained QCheckBox widget based on the widgetID. '''
        
        radioButtonWidget=self.findChild(QtWidgets.QRadioButton, widgetID)
        if not radioButtonWidget:
            radioButtonWidget=QtWidgets.QRadioButton(label)
            radioButtonWidget.setObjectName(widgetID)
            if clickedCmd:
                radioButtonWidget.clicked.connect(clickedCmd)

        if not visible:
            radioButtonWidget.hide()
        radioButtonWidget.setChecked(value)
        radioButtonWidget.setEnabled(enabled)
        if isinstance(parentLayout, QtWidgets.QGridLayout):
            if align:
                parentLayout.addWidget(radioButtonWidget, gridSet[0], gridSet[1], align)
            else:
                parentLayout.addWidget(radioButtonWidget, gridSet[0], gridSet[1])
        else:
            parentLayout.addWidget(radioButtonWidget)
        return radioButtonWidget

    def create_or_show_slider(self, widgetID:str, 
                        parentLayout:QtWidgets.QBoxLayout|QtWidgets.QGridLayout,
                        orientation:QtCore.Qt.Horizontal|QtCore.Qt.Vertical,
                        interval:int=1, value:int=0, minVal:int=0, maxVal:int=10,
                        enabled:bool=True, visible:bool=True, width=50,
                        gridSet:tuple[int,int]=(0,0), align=None):
        ''' Returns a built or obtained QSlider widget based on the widgetID. '''
        
        sliderWidget=self.findChild(QtWidgets.QSlider, widgetID)
        if not sliderWidget:
            sliderWidget=QtWidgets.QSlider(orientation)
            sliderWidget.setObjectName(widgetID)

        sliderWidget.setMinimum(minVal)
        sliderWidget.setMaximum(maxVal)
        sliderWidget.setTickInterval(interval)
        sliderWidget.setValue(value)
        sliderWidget.setMinimumWidth(width)
        if not visible:
            sliderWidget.hide()
        sliderWidget.setEnabled(enabled)
        if isinstance(parentLayout, QtWidgets.QGridLayout):
            if align:
                parentLayout.addWidget(sliderWidget, gridSet[0], gridSet[1], align)
            else:
                parentLayout.addWidget(sliderWidget, gridSet[0], gridSet[1])
        else:
            parentLayout.addWidget(sliderWidget)
        return sliderWidget

    def create_or_show_label(self, widgetID:str, label:str,
                             parentLayout:QtWidgets.QBoxLayout|QtWidgets.QGridLayout,
                             enabled:bool=True, visible:bool=True,
                             gridSet:tuple[int,int]=(0,0), align=False):
        labelWidget=self.findChild(QtWidgets.QLabel, widgetID)
        if not labelWidget:
            labelWidget=QtWidgets.QLabel(label)
            labelWidget.setObjectName(widgetID)
        if align:
            labelWidget.setAlignment(align)
        if not visible:
            labelWidget.hide()
        labelWidget.setEnabled(enabled)
        if isinstance(parentLayout, QtWidgets.QGridLayout):
            parentLayout.addWidget(labelWidget, gridSet[0], gridSet[1])
        else:
            parentLayout.addWidget(labelWidget)