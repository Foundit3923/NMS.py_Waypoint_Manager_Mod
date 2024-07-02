
import logging
import ctypes
import pprint

import nmspy.memutils as memutils
from nmspy.data.cpptypes import std
from nmspy.data import common, engine, enums as nms_enums
import nmspy.data.function_hooks as hooks
import nmspy.hooking as hooking
from nmspy.hooking import disable, main_loop
from nmspy.memutils import map_struct
import nmspy.data.structs as nms_structs
from nmspy.mod_loader import NMSMod
from nmspy.calling import call_function
import nmspy.data.local_types as lt
import nmspy.common as nms
from nmspy.mod_loader import ModState
from dataclasses import dataclass

"""class Vector3f(ctypes.Structure):
    x: float
    y: float
    z: float

    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
        ("z", ctypes.c_float),
        ("_padding", ctypes.c_byte * 0x4),
    ]

    def __str__(self) -> str:
        return f"<{self.x, self.y, self.z}>"""

""" def print_struct(struct: ctypes.Structure, depth: int = 0):
    for field_name, field_type in struct._fields_:
        if isinstance(field_type, ctypes.Structure):
            logging.info("  " * depth + field_name + ":")
            print_struct(field_type, depth + 1)
        else:
            if not field_name.startswith("_"): #for fear of mangling
                logging.info("  " * depth + f"{field_name}: {getattr(struct, field_name)}")
            else:
                # See if we have a non-private version of the field.
                if hasattr(struct, field_name[1:]):
                    logging.info("  " * depth + f"{field_name}: {getattr(struct, field_name[1:])}") """

class State_Vars(ModState):
    def __init__(self, binoc_arg=None, pEnv_arg=None):
        self.binoculars: binoc_arg
        self.playerEnv: pEnv_arg

def print_struct(struct: ctypes.Structure, max_depth=5):
    depth = 0
    stack = [iter(struct._fields_)]
    while stack:
        if len(stack) > max_depth:
            logging.info("Max recursion depth exceeded")
        try:
            name: str
            name, type_ = next(stack[-1])
        except StopIteration:
            stack.pop(-1)
            depth -= 1
            continue
        if isinstance(type_, ctypes.Structure):
            logging.info(" " * depth + name + ":")
            stack.append(iter(type_._fields_))
            dpeth += 1
            continue
        #check for public versions of private fields
        name = name.removeprefix('_')
        if hasattr(struct, name):
            attr = getattr(struct, name)
            logging.info(" " * depth + f"{name}:{attr}")

class waypoint_manager(NMSMod):
    __author__ = "foundit"
    __description__ = "Place markers at stored waypoints of places you've been"
    __version__ = "0.1"
    __NMSPY_required_version__ = "0.6.0"

    state = State_Vars()

    def __init__(self):
        super().__init__()
        self.text: str = "mm"
        self.should_print = True
        self.Binoculars = ctypes.Structure

    @property
    def _text(self):
        return self.text.encode()
    
    #@hooking.on_key_pressed(".")
    #def compare_models(self):
    #    try:
    #        logging.info(". pressed")
    #        logging.info("compare Binocular structures")
    #        address = ctypes.addressof(self.state.binoculars)
    #        logging.info(f'ctypes.addressof(self.state.binoculars): ' + str(address))
    #        address = ctypes.addressof(self.Binoculars)
    #        logging.info(f'ctypes.addressof(self.Binoculars): ' + str(address))
    #        markerModel = self.state.binoculars.MarkerModel
    #        logging.info(f'self.state.binoculars.MarkerModel: ' + str(markerModel))
    #        markerModel = self.Binoculars.MarkerModel
    #        logging.info(f'self.Binoculars.MarkerModel: ' + str(markerModel))
    #        lookupInt = self.state.binoculars.MarkerModel.lookupInt
    #        logging.info(f'self.state.binoculars.MarkerModel.lookupInt: ' + str(lookupInt))
    #        lookupInt = self.Binoculars.MarkerModel.lookupInt
    #        logging.info(f'self.Binoculars.MarkerModel.lookupInt: ' + str(lookupInt))
    #    except Exception as e:
    #        logging.exception(e)

    @hooks.cGcBinoculars.SetMarker.after
    def checkSetMarker(self, this):
        try:
            logging.info("Binoc SetMarker event triggered")
            logging.info(f'memutils: ' + memutils.pprint_mem(this + 2000, 0x10))
            #logging.info(f'binocs: '+str(self.binoculars))
            logging.info(f'this(cGcBinoculars):   ' + str(this))
            logging.info(f'print_struct(MarkerModel.lookupInt): ')
            self.Binoculars = map_struct(this, nms_structs.cGcBinoculars)
            logging.info(f'self.MarkerModel: ' + str(self.Binoculars.MarkerModel))

            #logging.info("compare Binocular structures")
            #address = ctypes.addressof(self.state.binoculars)
            #logging.info(f'ctypes.addressof(self.state.binoculars): ' + str(address))
            #address = ctypes.addressof(self.Binoculars)
            #logging.info(f'ctypes.addressof(self.Binoculars): ' + str(address))
            #markerModel = self.state.binoculars.MarkerModel
            #logging.info(f'self.state.binoculars.MarkerModel: ' + str(markerModel))
            #markerModel = self.Binoculars.MarkerModel
            #logging.info(f'self.Binoculars.MarkerModel: ' + str(markerModel))
            #lookupInt = self.state.binoculars.MarkerModel.lookupInt
            #logging.info(f'self.state.binoculars.MarkerModel.lookupInt: ' + str(lookupInt))
            #lookupInt = self.Binoculars.MarkerModel.lookupInt
            #logging.info(f'self.Binoculars.MarkerModel.lookupInt: ' + str(lookupInt))
#
            #logging.info(f'Updating self.state.binoculars')
            #self.state.binoculars = self.Binoculars #map_struct(this, nms_structs.cGcBinoculars)
            #address = ctypes.addressof(self.state.binoculars)
            #logging.info(f'ctypes.addressof(self.state.binoculars): ' + str(address))            
            #markerModel = self.state.binoculars.MarkerModel
            #logging.info(f'self.state.binoculars.MarkerModel: ' + str(markerModel))
            #lookupInt = self.state.binoculars.MarkerModel.lookupInt
            #logging.info(f'self.state.binoculars.MarkerModel.lookupInt: ' + str(lookupInt))
        except Exception as e:
            logging.exception(e)

    @hooking.on_key_pressed("o")
    def get_position(self):
        try:
            logging.info(f'Output')
            logging.info(ctypes.addressof(nms.GcApplication.data.contents.Simulation) - ctypes.addressof(nms.GcApplication.data.contents))
            logging.info(f'Pressed o: ')
            position = self.state.playerEnv.mPlayerTM
            position_matrix = position.matrix
            position_matrix_string = ','.join(str(item) for item in position_matrix)
            logging.info(f'position matrix:')
            logging.info(position_matrix_string)
            logging.info(f'positoin __str__')
            logging.info(str(position))
        except Exception as e:
            logging.exception(e)

    @hooking.on_key_pressed("n")
    def place_marker(self):
        logging.info(f'Place marker with code')
        #can't consistently place markers
        #was considerably more easy after dying
        #all markers now have the same lookupInt and address
        #only the binocular placed marker moves when 'i' is pressed
        #when each new marker is placed the last one glows
        #this mirrors how the binocular placed markers act when a new one is place
        #the only difference is that with binocular placed markers the old one goes away when it glows
        #the code placed ones do not
        #Seems that code placed markers are not stored correctly
        try:
            #call_function("Engine::RequestRemoveNode", self.MarkerModel)
            address = ctypes.addressof(self.state.binoculars)
            logging.info(f'ctypes.addressof(self.state.binoculars): ' + str(address))
            offset = ctypes.addressof(self.state.binoculars)
            logging.info(f'binoculars offset: ' + str(offset))
            ptr = ctypes.c_ulonglong(offset)
            logging.info(f'binoculars ptr: ' + str(ptr))
            call_function("cGcBinoculars::SetMarker", ctypes.addressof(ptr))
        except Exception as e:
            logging.exception(e)

    @hooking.on_key_pressed("/")
    def remove_marker(self):
        try:
            logging.info("/ pressed")
            logging.info("Remove requested node")
            engine.RequestRemoveNode(self.state.binoculars.MarkerModel)
            #call_function("Engine::RequestRemoveNode", self.MarkerModel)
        except Exception as e:
            logging.exception(e)

    @hooking.on_key_pressed("space")
    def activate_marker(self):
        try:
            logging.info(", pressed")
            logging.info("Activate requested node")
            engine.SetNodeActivation(self.state.binoculars.MarkerModel, True)
            #call_function("Engine::RequestRemoveNode", self.MarkerModel)
        except Exception as e:
            logging.exception(e)

    @hooking.on_key_pressed("m")
    def deactivate_marker(self):
        try:
            logging.info("m pressed")
            logging.info("Deactivate requested node")
            #engine.RequestRemoveNode(self.state.binoculars.MarkerModel)
            engine.SetNodeActivation(self.state.binoculars.MarkerModel, False)
            #call_function("Engine::RequestRemoveNode", self.MarkerModel)
        except Exception as e:
            logging.exception(e)


    @hooking.on_state_change("APPVIEW")
    def init_state_var(self):
        logging.info(f'state var set')
        #Isn't set until after save file is fully loaded
        self.state.playerEnv = nms.GcApplication.data.contents.Simulation.environment.playerEnvironment        
        sim_addr = ctypes.addressof(nms.GcApplication.data.contents.Simulation)
        self.state.binoculars = map_struct(sim_addr + 74160 + 6624, nms_structs.cGcBinoculars)

    @hooking.on_key_pressed("i")
    def move_marker(self):
        try:
            logging.info(f'test test test')
            logging.info(f'Pressed I, moving marker: ')
            logging.info(f'self.MarkerModel.lookupInt: ' + str(self.Binoculars.MarkerModel.lookupInt))
            vec = common.Vector3f(3,0,0) #this is not the location we want. This is how much we change each of these values
            call_function("Engine::ShiftAllTransformsForNode", self.Binoculars.MarkerModel.lookupInt, ctypes.addressof(vec))
        except Exception as e:
            logging.exception(e)

    @hooking.on_key_pressed("l")
    def clear_binocular_var(self):
        try:
            logging.info(f'reseting self.state.binoculars')
            self.state.binoculars = None
            sim_addr = ctypes.addressof(nms.GcApplication.data.contents.Simulation)
            self.state.binoculars = map_struct(sim_addr + 74160 + 6624, nms_structs.cGcBinoculars)           
        except Exception as e:
            logging.exception(e)

