import maya.cmds as mc

WINDOW_ID="creativeMatch01"

class creativeMatch():
    def __init__(self):
        
        self.fk_controls={"arm":["_shoulder_fk_ctrl", "_elbow_fk_ctrl", "_wrist_fk_ctrl"],
                          "leg":["_hip_fk_ctrl", "_knee_fk_ctrl", "_ankle_fk_ctrl", "_ball_fk_ctrl"]}
        
        self.ik_controls={"arm":["_elbow_ik_ctrl", "_wrist_ik_ctrl"],
                          "leg":["_knee_ik_ctrl", "_foot_ik_ctrl"]}

        self.fk_ctrl=None
        self.ik_ctrl=None
        
        if mc.window(WINDOW_ID, exists=True):
            mc.deleteUI(WINDOW_ID, window=True)

        self.mainWindow=mc.window(WINDOW_ID, title="creativeMatch", widthHeight=(300,200))
        
        self.mainLayout=mc.formLayout(self.mainWindow)
        leftFKArmButton=mc.button(label="Match FK Left Arm", command=self.fk_match)
        rightFKArmButton=mc.button(label="Match FK Right Arm", command=lambda args:self.fk_match(side='right'))
        
        mc.formLayout(self.mainLayout, edit=True, attachForm=[[leftFKArmButton, "top", 10], [leftFKArmButton, "left", 5],
                                                              [rightFKArmButton, "top", 10], [rightFKArmButton, "left", 5]],
                                                attachControl=[[rightFKArmButton, "left", 10, leftFKArmButton]])
        
        mc.showWindow()
        
    def check_selection(self, *args):
        ctrl=mc.ls(selection=True)
        
        if len(ctrl)>1:
            mc.warning("Select only one ctrl for limb")
            return
        if "ctrl" in ctrl[0]:
            if "fk" in ctrl[0]:
                self.fk_ctrl=ctrl[0]
                self.fk_match()
            if "ik" in ctrl[0]:
                self.ik_ctrl=ctrl[0]
    
    def fk_match(self, *args, limb:str="arm", side:str="left"):

        controlsToMatch=[side+ctrl for ctrl in self.fk_controls.get(limb)]
        for ctrl in controlsToMatch:
            if mc.objExists(ctrl):
                mc.setAttr(f"{side}_{limb}_settings_ctrl.IK", 1)
                jnt_match=ctrl.replace("fk_ctrl", "jnt")
                mc.matchTransform(ctrl, jnt_match)
                mc.setAttr(f"{side}_{limb}_settings_ctrl.IK", 0)
    