# A collection of absolutely minimal stubs to mimic
# some Odemis functionality.

import random

print('USING ODEMIS STUBS - ONLY FOR TESTING - NOT FOR USE ON ACTUAL SECOM DEVICE')

class focus_position:
    value = {"z" : 0.0}


class stage_position:
    value = {"x" : 0.0, "y" : 0.0}


class component:
    role = None
    def __init__(self, role):
        self.role = role


class axis:
    range = (-999.0, 999.0)


class focus_component(component):
    position = focus_position()
    axes = { "z": axis }

    def __init__(self, role):
        component.__init__(self, role)

    def set_position(self, z):
        self.position.value["z"] = z


class stage_component(component):
    position = stage_position()
    axes = { "x": axis, "y": axis }

    def __init__(self, role):
        component.__init__(self, role)


class model:
    @staticmethod
    def getComponent(role):
        if role == "focus":
            return focus_component(role)
        else:
            if role == "stage":
                return stage_component(role)
            else:
                return component(role)


class align:
    def AutoFocus(det, emt, focuser, good_focus, rng_focus, method):
        z = random.uniform(rng_focus[0], rng_focus[1])
        lvl = 999  # arbitrary focus level number
        focuser.set_position(z)
        return autofocus_future(z, lvl)

    class autofocus:
        MTD_BINARY = 0


class future:
    def cancel(self):
        pass

    def result(self):
        pass


class autofocus_future(future):
    foc_pos = None
    fm_final = None

    def __init__(self, foc_pos, fm_final):
        self.foc_pos = foc_pos
        self.fm_final = fm_final
        future.__init__(self)

    def result(self, t):
        return self.foc_pos, self.fm_final