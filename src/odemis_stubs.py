# A collection of absolutely minimal stubs to mimic
# some Odemis functionality.

import random

print('USING ODEMIS STUBS - ONLY FOR TESTING - NOT FOR USE ON ACTUAL SECOM DEVICE')

MTD_BINARY = "stub_autofocus_method_binary"

class focuser_position:
    value = {"z" : 0.0}


class component:
    role = None
    def __init__(self, role):
        self.role = role


class focuser_component(component):
    position = focuser_position()

    def __init__(self, role):
        super().__init__(role)

    def set_position(self, z):
        self.position.value["z"] = z


class model:
    def getComponent(role):
        if role == "focus":
            return focuser_component(role)
        else:
            return component(role)


class align:
    class autofocus:
        MTD_BINARY = 0
        def AutoFocus(det, emt, focuser, good_focus, rng_focus, method):
            z = random.uniform(rng_focus[0], rng_focus[1])
            lvl = 666 # TODO: realistic focus level number
            focuser.set_position(z)
            return autofocus_future(z, lvl)


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
        super().__init__()

    def result(self, t):
        return self.foc_pos, self.fm_final