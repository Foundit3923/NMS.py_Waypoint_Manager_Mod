#made by Foundit
#Version: 0.2
import logging
import ctypes
#import pprint
import keyboard
import time, threading
import json
import pprint
#import datetime
from waiting import wait, TimeoutExpired
import re
import os

import nmspy.memutils as memutils
from nmspy.data.cpptypes import std
from nmspy.data import common, enums as nms_enums
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
import nmspy.data.engine as engine
import nmspy.data.structs as nms_structs
from dataclasses import dataclass, field

@dataclass
class State_Vars(ModState):
    binoculars: nms_structs.cGcBinoculars = None
    playerEnv: nms_structs.cGcPlayerEnvironment = None
    player: nms_structs.cGcPlayer = None
    chatMan: nms_structs.cGcTextChatManager = None
    chatInp: nms_structs.cGcTextChatInput = None
    inputPort: nms_structs.cTkInputPort = None
    """ inputPort_1: nms_structs.cTkInputPort = None
    inputPort_2: nms_structs.cTkInputPort = None """
    inputPort_ptr: int = 0
    """ lastInputPort_ptr: int = 0
    inputPort_ptr_1: int = 0
    inputPort_ptr_2: int = 0 """
    wpDict: dict = field(default_factory = dict)
    _save_fields_ = ("wpDict", )

class key_press(NMSMod):
    __author__ = "foundit"
    __description__ = "Place markers at stored waypoints of places you've been"
    __version__ = "0.2"
    __NMSPY_required_version__ = "0.6.0"

    state = State_Vars()

#--------------------------------------------------------------------Init----------------------------------------------------------------------------#

    def __init__(self):
        super().__init__()
        self.text: str = "mm"
        self.node_active = threading.Event()
        #self.waypoint_dict = {}
        self.waypoint_options_dict = {}
        self.waypoint_proximity_dict = {}
        self.max_option_num = 0
        #self.func_timer = threading.Timer(1, self.moveOnActivation)
        self.f_key = threading.Event()
        self.fixed_str_ptr = common.cTkFixedString[1023]()
        self.marker_lookup = None
        self.should_log = False
        self.user_input = None
        self.func_input_flag = None
        self.user_input_event = threading.Event()
        self.interface_flag = threading.Event()
        self.start_pressing = False
        self.counter = 0
        self.port = 0
        self.port_ptr_flag = False
        self.set_waypoint_flag = False
        self.updateScan_flag = False
        self.print = True
        self.buttoninput_flag = False
        self.humanbuttoninput_flag = False

    @hooking.on_state_change("APPVIEW")
    def init_state_var(self):
        try:
            self.loadJson()
        except Exception as e:
            logging.exception(e)
        #Isn't set until after save file is fully loaded
        self.state.playerEnv = nms.GcApplication.data.contents.Simulation.environment.playerEnvironment        
        sim_addr = ctypes.addressof(nms.GcApplication.data.contents.Simulation)
        self.state.binoculars = map_struct(sim_addr + 74160 + 6624, nms_structs.cGcBinoculars)
        logging.info(f'state var set')
        logging.info(f'\n')

#--------------------------------------------------------------------Methods----------------------------------------------------------------------------#

#----------------------------------------------------------Storing and Loading JSON------------------------------------------------------------------#
    def loadJson(self):
        try:
          logging.info(f'Loading dict from local JSON file')
          logging.info(f'self.state.load("waypoint_data.json")')
          self.state.load("waypoint_data.json")
        except FileNotFoundError:
            logging.info(f'self.updateJson()')
            self.updateJson()

    def updateJson(self):
        try:
          logging.info(f'Save waypoint locations to local file')
          logging.info(f'self.state.save(\'waypoint_data.json\')')
          self.state.save('waypoint_data.json')
          logging.info(f'dict saved to waypoint_data.json')
        except Exception as e:
                logging.exception(e)

    def storeLocation(self, name):
        try:
          logging.info(f'Save waypoint location to dictionary, then update JSON')
          self.state.wpDict[name] = self.state.playerEnv.mPlayerTM.pos.__json__()
          self.updateJson()
          logging.info(f'\n')
          return dict
        except Exception as e:
                logging.exception(e) 

    def printDict(self):
        logging.info(self.state.wpDict)
#----------------------------------------------------------Text Interface----------------------------------------------------------------#

    def closeInterface(self):
        prompt = "Closing interface due to inactivity"
        self.outputToChat(prompt)
        self.interface_flag.clear()
        self.main()

    def sanitizeInput(self, input: str, source):
        logging.info(f'Sanitizing input: ' + self.user_input)
        PATT = re.compile("(\d).*")
        if match := PATT.match(self.user_input):
            logging.info(f"Found: {match.group(1)}")
        cleaned_input = "EMPTY"
        if(match):
            cleaned_input = match.group(1)
        return cleaned_input
    
    def buildWaypointOptionsPrompt(self):
        logging.info(f'Building waypoint options prompt')
        try:
            self.waypoint_options_dict = {}
            self.max_option_num = 0
            prompt = ""
            count = 0
            location_name = ""
            if(self.state.wpDict):
                for location_name in self.state.wpDict:
                    self.waypoint_options_dict[count] = location_name
                    prompt = prompt + f"{count}) {location_name}\n"
                    logging.info(f'prompt: ' + prompt)
                    count = count + 1
            else:
                prompt = prompt + "No saved waypoints."
            self.max_option_num = count
            return prompt
        except Exception as e:
                logging.exception(e)
        
            
    def cleanLocationInput(self):
        cleaned_input = self.sanitizeInput(self.user_input, "chooseLocation")
        if(cleaned_input == "EMPTY"):
            output = "That is not a valid option. Please try again"
            self.outputToChat(output)
            self.func_input_flag = "choose"
            self.chooseLocation()
        location = self.waypoint_options_dict[int(cleaned_input)]
        self.placeWaypointFromInterface(location)

    def chooseLocation(self):
        self.func_input_flag = "choose"
        logging.info(f'Choose location')
        self.user_input = ""
        prompt = "Enter the coresponding number and press `ENTER`\n"
        options = self.buildWaypointOptionsPrompt()
        prompt = prompt + options
        self.outputToChat(prompt)
    
    def saveLocation(self):
        self.func_input_flag = "saveLoc"
        logging.info("Saving Location")
        self.user_input = ""
        prompt = "Enter a name/description\n"     
        self.outputToChat(prompt)  

    def evalMenuInput(self):
        cleaned_input = self.sanitizeInput(self.user_input, "menu")
        logging.info(f'cleaned_input: ' + cleaned_input)
        if(cleaned_input == "EMPTY"):
            output = "That is not a valid option. Please try again"
            self.outputToChat(output)
            self.func_input_flag = "menu"
            self.printMenuToChat()            
        match str(cleaned_input):
            case "1":
                 self.saveLocation()
            case "2":
                 self.chooseLocation()
            case _:
                output = "That is not a valid option. Please try again"
                self.outputToChat(output)
                self.func_input_flag = "menu"
                self.printMenuToChat()

    def printMenuToChat(self):
        logging.info("Printing menu to Chat")
        menu = "Enter the coresponding number and press `ENTER`\n1) Save location\n2) Choose location\n"
        self.outputToChat(menu)
            

    def outputToChat(self, output):
        static_s = common.cTkFixedString[1023]()
        static_s.set(output)
        static_s_ptr = ctypes.addressof(static_s)
        call_function("cGcTextChatManager::Say", self.state.chatMan, static_s_ptr, False, overload="cGcTextChatManager *, const cTkFixedString<1023,char> *, bool")

#----------------------------------------------------------Moving Waypoint------------------------------------------------------------------#

    def placeWaypointFromInterface(self, location):
        try:
            logging.info(f'Place Waypoint from interface')
            self.press_f()                          
            #self.start_pressing = True
            logging.info(f'\n')
        except Exception as e:
            logging.exception(e)

    def press_f(self):
        logging.info(f'press the f key')
        #self.state.inputPort.SetButton(lt.eInputButton.EInputButton_KeyF)
        keyboard.press('f')
        self.f_key.set()
        logging.info(f'self.f_key.set() = ' + str(self.f_key.is_set()))

#--------------------------------------------------------------------Hooks and Functions Capture and Place Waypoints----------------------------------------------------------------------------#
 
    """ @main_loop.after
    def main_game_loop(self):
        if self.start_pressing:
            if self.counter == 0:
                logging.info(f'keyboard.press(f)')
                keyboard.press('f')
            if self.counter < 100:
                logging.info(f'self.counter: {self.counter}')
                #self.state.inputPort.SetButton(lt.eInputButton.EInputButton_KeyF)
                if self.counter == 60:
                    logging.info('keyboard.press(e)')
                    keyboard.press('e')
                    #self.state.inputPort.SetButton(lt.eInputButton.EInputButton_KeyE) #End when GetButtonINPut is called for 22
                self.counter += 1
            else:
                keyboard.release('e')
                #keyboard.release('f')
                self.start_pressing = False
                self.counter = 0 """
#--------------------------------------------------------------------Hooks and Functions to Read and Write with Chat----------------------------------------------------------------------------#

    @hooks.cGcTextChatManager.Construct.after
    def managerConstruct(self, this):
        logging.info("\n")
        logging.info(f"***********  TextChatManager constructed at 0x{this:X}  ***********")
        self.state.chatMan = this
        logging.info("\n")

    @hooks.cGcTextChatInput.Construct.after
    def inputConstruct(self, this):
        logging.info("\n")
        logging.info(f"***********  TextChatInput constructed at 0x{this:X}  ***********")
        self.state.chatInp = this
        logging.info("\n")
    
    @hooks.cGcTextChatInput.ParseTextForCommands
    def parseCommands(self, this, lMessageText):
        logging.info(f'ParseTextForCommands event detected')
        text = map_struct(lMessageText, common.cTkFixedString[1023])
        logging.info(f"ParseTextForCommands called with {str(text)}")
        self.user_input = str(text)
        logging.info(f'Function input flag: {self.func_input_flag}')
        if str(text) == '>':
            #self.menu_flag = True
            self.func_input_flag = "menu"
            self.user_input = ""
            self.printMenuToChat()
        else:
            match self.func_input_flag:
                case "menu":
                    #self.menu_flag = False
                    self.func_input_flag = None
                    self.evalMenuInput()
                case "saveLoc":
                    #self.saveLoc_flag = False   
                    self.func_input_flag = None         
                    self.storeLocation(self.user_input)
                case "choose":
                    #self.choose_flag = False
                    self.func_input_flag = None
                    self.cleanLocationInput()
                case _:
                    logging.info(f'Detected input text: ' + str(text))
                    #self.user_input = str(text)

    @hooking.on_key_pressed("space")
    def createWaypoint(self):
        keyboard.press('f')
