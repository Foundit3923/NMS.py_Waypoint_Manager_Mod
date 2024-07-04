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
    chatMan: nms_structs.cGcTextChatManager = None
    chatInp: nms_structs.cGcTextChatInput = None
    inputPort: nms_structs.cTkInputPort = None
    inputPort_ptr: int = 0
    wpDict: dict = field(default_factory = dict)
    _save_fields_ = ("wpDict", )

""" class State_Vars(ModState):
    def __init__(self, binoc_arg=None, pEnv_arg=None, chatMan_arg=None, chatInp_arg=None, wpDict_arg=None):
        self.binoculars = binoc_arg
        self.playerEnv = pEnv_arg
        self.chatMan = chatMan_arg
        self.chatInp = chatInp_arg
        self.wpDict = wpDict_arg """

def print_struct(struct: ctypes.Structure, max_depth=5):
    depth = 0
    stack = [iter(struct._fields_)]
    while stack:
        logging.info(f'depth:' + str(depth))
        if len(stack) > max_depth:
            logging.info("Max recursion depth exceeded")
        try:
            name: str
            name, type_ = next(stack[-1])
            logging.info(f'name: ' + name)
        except StopIteration:
            logging.info(f'stop iteration')
            stack.pop(-1)
            depth -= 1
            continue
        logging.info(f'check if is instance')
        if isinstance(type_, ctypes.Structure):
            logging.info(" " * depth + name + ":")
            stack.append(iter(type_._fields_))
            dpeth += 1
            continue
        #check for public versions of private fields
        name = name.removeprefix('_')
        logging.info(f'checking for attribute')
        if hasattr(struct, name):
            attr = getattr(struct, name)
            logging.info(" " * depth + f"{name}:{attr}")


class waypoint_manager(NMSMod):
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
        self.func_timer = threading.Timer(1, self.moveOnActivation)
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

    def main(self):
        logging.info(f'Main')
        threading.Thread(target=self.printMenuToChat()).start()

#--------------------------------------------------------------------Methods----------------------------------------------------------------------------#

#----------------------------------------------------------Storing and Loading JSON------------------------------------------------------------------#
    def loadJson(self):
        try:
          logging.info(f'Loading dict from local JSON file')
          #logging.info(f'vector = common.Vector3f')
          #vector = common.Vector3f
          logging.info(f'self.state.load("waypoint_data.json")')
          self.state.load("waypoint_data.json")
          #logging.info(f'path = \'E:/Software/No Mans Sky Mods/NMS.py/NMS.py/mods/mod_data/waypoint_manager/data.json\'')
          #path = 'E:/Software/No Mans Sky Mods/NMS.py/NMS.py/mods/mod_data/waypoint_manager/data.json'
          #path = os.path.dirname(os.path.abspath(__file__))
          #logging.info(f'f = open(path)')
          #f = open(path)
          #logging.info(f'with open(path) as f:')
          #with open(path + '/data.json', "r", encoding='utf-8-sig') as f:
          #    logging.info(f.read())
          #    logging.info(type(f))
          #    logging.info(type(f.read()))
          #    logging.info(f'data = json.loads(f.read())')
          #    data = json.loads(f.read())
          #logging.info(f'data = json.load(f)')
          #data = json.load(f)
          #logging.info({data})
          #logging.info(f'for key in data:')
          #for key in data:
          #    logging.info(f'Key: {key}')
          #    logging.info(f'vector.x = data[key][\'x\']')
          #    vector.x = data[key]['x']
          #    logging.info(f'vector.y = data[key][\'y\']')
          #    vector.y = data[key]['y']
          #    logging.info(f'vector.z = data[key][\'z\']')
          #    vector.z = data[key]['z']
          #    logging.info(f'self.state.wpDict[key] = vector')
          #    self.state.wpDict[key] = vector    
          #logging.info(f'\n')
        except FileNotFoundError:
            logging.info(f'self.updateJson()')
            self.updateJson()

    def updateJson(self):
        try:
          logging.info(f'Save waypoint locations to local file')
          #path = 'E:/Software/No Mans Sky Mods/NMS.py/NMS.py/mods/mod_data/waypoint_manager/data.json'
          #ModState._save_fields_ = self.state.wpDict
          logging.info(f'self.state.save(\'waypoint_data.json\')')
          self.state.save('waypoint_data.json')
          logging.info(f'dict saved to waypoint_data.json')
          #with open(path, 'w') as outfile:
          #  logging.info(f'File exists')
          #  json.dump(self.state.wpDict, outfile)
          #  logging.info(f'\n')
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

    """
    Need: Commands, user prompt, menu, 

    Commands: 
    `>` indicates a command. Is used to start the waypoint interface

    user prompt:
    Enter the coresponding number and press `ENTER`

    Menu:
    1) Save location\n
    2) Choose location\n
    3) Choose last saved location

    Save Location:
    prompt: Enter a name/description

    Choose Location:
    prompt: Enter the coresponding number and press `ENTER`

    1) lots of gold\n
    2) nice vista\n
    3) gravity orbs\n


    Sort by proximity:
    get user location: player_pos = self.state.playerEnv.mPlayerTM.pos.__json__()
    location_name = ""
    for location_name in self.waypoint_dict:
        player_pos = self.state.playerEnv.mPlayerTM.pos
        dest_pos = self.waypoint_dict[location_name]

        a = abs(player_pos.x - dest_pos.x)
        b = abs(player_pos.y - dest_pos.y)

        c = math.sqrt(a ** 2 + b ** 2)
        self.waypoint_proximity_dict[location_name] = c

    """

    def closeInterface(self):
        prompt = "Closing interface due to inactivity"
        self.outputToChat(prompt)
        self.interface_flag.clear()
        self.main()

    """ def userInputActivity(self):
        logging.info(f'waiting for user input activity')
        start = time.time()
        end = start + 30
        logging.info(f'self.user_input: ' + self.user_input)
        while(time.time() <= end):
            time.sleep(1)
            #difference = time.time() - start
            #if(difference == 0 or difference == 10 or difference == 20 or difference == 30):
            #    logging.info(f'waiting for input: ' + self.user_input )
            #    logging.info(f'time check: ' + str(difference) )
            #logging.info(f'waiting for input: ' + self.user_input )
            if(self.user_input): 
                logging.info(f'Returning True. User input: ' + self.user_input)
                return True
            #logging.info(f'self.user_input_event: ' + self.user_input_event.is_set())
        logging.info(f'Close interface, return false')
        return False """
    
    """ def extractFirstInt(self):
        start = 0
        input = self.user_input
        while start < len(input) and not input[start].isdigit():
            start += 1
        end = start
        while start < len(input) and input[start].isdigit():
            end += 1
        if not input[start:end]:
            return None
        return input[start:end] """
    
    def sanitizeInput(self, input: str, source):
        logging.info(f'Sanitizing input: ' + self.user_input)
        #match = self.extractFirstInt()
        #match = re.search(r"\d", self.user_input)
        #match = re.search("1", self.user_input, 1)
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
            #self.choose_flag = True
            self.func_input_flag = "choose"
            self.chooseLocation()
        location = self.waypoint_options_dict[int(cleaned_input)]
        self.placeWaypointFromInterface(location)

    def chooseLocation(self):
        #self.choose_flag = True
        self.func_input_flag = "choose"
        logging.info(f'Choose location')
        self.user_input = ""
        prompt = "Enter the coresponding number and press `ENTER`\n"
        options = self.buildWaypointOptionsPrompt()
        prompt = prompt + options
        self.outputToChat(prompt)
    
    def saveLocation(self):
        #self.saveLoc_flag = True
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
            #self.menu_flag = True
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
                #self.menu_flag = True
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
            self.node_active.clear()
            #self.state.inputPort.SetButton(lt.eInputButton.EInputButton_KeyF)
            #logging.info(f'{self.state.inputPort.actionStates.miActionSetContinuity}')
            #for i in range(100):
            #    self.state.inputPort.SetButton(lt.eInputButton.EInputButton_KeyF)
            #    if i == 20:
            #        self.state.inputPort.SetButton(lt.eInputButton.EInputButton_KeyE)
            #self.f_key.clear()    
            #self.press_f() 
            #logging.info(f'self.f_key.is_set() = ' + str(self.f_key.is_set()))
            #if(self.f_key.is_set()):
            #    self.generateWaypoint()           
            self.start_pressing = True
            self.moveOnActivationFromInterface(0, location)     
            logging.info(f'\n')
        except Exception as e:
            logging.exception(e)

    def moveWaypoint(self, location):
        try:
            logging.info(f'Moving marker')
            destination_vector = common.Vector3f()
            node_vector = common.Vector3f()
            destination_pos = self.state.wpDict[location]
            destination_vector = self.repackVector3f(destination_pos)
            logging.info(f'destination_vector: ' + destination_vector.__str__())
            node_matrix = self.getNodeMatrix()
            node_vector = node_matrix.pos
            logging.info(f'node_vector: ' + node_vector.__str__())
            transformation_vector = destination_vector - node_vector
            logging.info(transformation_vector.__str__())
            self.moveWaypointToDestination(transformation_vector)
            logging.info(f'\n')
        except Exception as e:
                logging.exception(e)
    
    def getNodeMatrix(self):
        node_matrix = engine.GetNodeAbsoluteTransMatrix(self.state.binoculars.MarkerModel)
        return node_matrix

    def repackVector3f(self, dict_a):
        vector = common.Vector3f()
        vector.x = dict_a['x']
        vector.y = dict_a['y']
        vector.z = dict_a['z']
        return vector
    
    def getNodeActivation(self):
        try:
                self.node_active = call_function("Engine::GetNodeActivation", self.state.binoculars.MarkerModel.lookupInt)
        except Exception as e:
                logging.exception(e)  
    
    def checkIsActive(self, isActive):
        try:
           if isActive.ready():
               return True
           return False
        except Exception as e:
                logging.exception(e)       
       
    def toggleActivation(self):
        try:
            logging.info(f'Toggle node activation')
            node_active = call_function("Engine::GetNodeActivation", self.state.binoculars.MarkerModel.lookupInt)
            #logging.info(f'node_active: ' + str(node_active))
            if(node_active):
                self.node_active.clear()
                engine.SetNodeActivation(self.state.binoculars.MarkerModel, node_active)
            else:            
                self.node_active.set()
                engine.SetNodeActivation(self.state.binoculars.MarkerModel, node_active)
            logging.info(f'\n')
        except Exception as e:
                logging.exception(e)

    """ def fkey_state(self):
        logging.info("f_key_state: " + str(self.f_key.is_set()))
        wait(lambda: keyboard.on_press_key('f'))
        return self.f_key.is_set()
     """
    def press_f(self):
        logging.info(f'press the f key')
        self.state.inputPort.SetButton(lt.eInputButton.EInputButton_KeyF)
        #keyboard.press('f')
        self.f_key.set()
        logging.info(f'self.f_key.set() = ' + str(self.f_key.is_set()))

    def generateWaypoint(self):
        try:
            logging.info(f'Generate marker via visor')
            time.sleep(.05)
            keyboard.press('e')
            time.sleep(.05)
            keyboard.release('e')
            keyboard.release('f')
            self.f_key.clear()
            logging.info(f'\n')
        except Exception as e:
            logging.exception(e)

    def moveWaypointToDestination(self, transformation_vector):
        try:
            logging.info(f'Move waypoint to destination')
            call_function("Engine::ShiftAllTransformsForNode", self.state.binoculars.MarkerModel.lookupInt, ctypes.addressof(transformation_vector))
            logging.info(f'\n')
        except Exception as e:
                logging.exception(e)
    
    def getActivationState(self):
        return call_function("Engine::GetNodeActivation", self.state.binoculars.MarkerModel.lookupInt)
    
    def processMoveNode(self):
        location = 'first'
        self.moveWaypoint(location)    

    def moveOnActivation(self, count):
        logging.info(f'move on activation')
        if(self.node_active.is_set()):
            logging.info(f'self.node_active is active')
            self.toggleActivation()
            time.sleep(1)            
            self.processMoveNode()
            self.toggleActivation()
        else:
            logging.info(f'self.node_active is not set')
            if(count < 50):
                count = count + 1
                t = threading.Timer(1, self.moveOnActivation, [count])
                t.start()

    def moveOnActivationFromInterface(self, count, location):
        logging.info(f'move on activation')
        if(self.node_active.is_set()):
            logging.info(f'self.node_active is active')
            self.toggleActivation()
            time.sleep(1)            
            self.moveWaypoint(location)
            self.toggleActivation()
        else:
            logging.info(f'self.node_active is not set')
            if(count < 50):
                count = count + 1
                t = threading.Timer(1, self.moveOnActivation, [count,location])
                t.start()                 

#--------------------------------------------------------------------Hooks and Functions Capture and Place Waypoints----------------------------------------------------------------------------#
    
    @property
    def _text(self):
        return self.text.encode()
    
    @main_loop.before
    def main_game_loop(self):
        if self.start_pressing:
            if self.counter < 100:
                #logging.info(f'{self.counter}')
                self.state.inputPort.SetButton(lt.eInputButton.EInputButton_KeyF)
                self.counter += 1
            else:
                self.start_pressing = False
                self.counter = 0

    """ @hooking.on_key_pressed("m")
    def placeWaypoint(self):
        try:
            logging.info(f'Place Waypoint')
            self.node_active.clear()
            self.f_key.clear()    
            self.press_f() 
            logging.info(f'self.f_key.is_set() = ' + str(self.f_key.is_set()))
            if(self.f_key.is_set()):
                self.generateWaypoint()             
            self.moveOnActivation(0)     
            logging.info(f'\n')
        except Exception as e:
            logging.exception(e)

    @hooking.on_key_pressed("u")
    def createWaypoint(self):
        try:
            logging.info(f'Create Waypoint')
            logging.info(f'Waypoint location: ' + self.state.playerEnv.mPlayerTM.pos.__str__())
            self.storeLocation("first")
            logging.info(f'\n')
        except Exception as e:
            logging.exception(e) """

    @hooks.cGcBinoculars.SetMarker.after
    def checkSetMarker(self, this):
        try:
            logging.info(f'SetMarker event detected')
            binoculars = map_struct(this, nms_structs.cGcBinoculars)
            self.marker_lookup = binoculars.MarkerModel.lookupInt
            self.should_log = True
            hooks.cGcBinoculars.SetMarker.original(this)
            self.should_log = False
            self.node_active.set()
            logging.info(f'\n')
        except Exception as e:
            logging.exception(e)

    @hooks.Engine.GetNodeAbsoluteTransMatrix.before
    def modify_node_transform(self, node, absMat):
        if node == self.marker_lookup and self.should_log:
            logging.info("Need to override the passed in absMat")

    """ @hooks.cTkInputPort.GetMousePosition.after
    def captureInputPort(self, this):
        logging.info(f'cTkInputPort*: {this}')
        self.state.inputPort = this
        if self.state.inputPort == None:
            logging.info(f'cTkInputPort*: {this}')
            self.state.inputPort = this

    @hooks.cTkInputPort.Update.after
    def captureInputPort(self, this):
        logging.info(f'cTkInputPort*: {this}')
        self.state.inputPort = this
        if self.state.inputPort == None:
            logging.info(f'cTkInputPort*: {this}')
            self.state.inputPort = this """

    """ @hooks.cTkInputPort.SetButton.after
    def capture_key(self, this, leIndex):
        logging.info(f"cTkInputPort*: {this}")
        logging.info(f"leIndex: {leIndex}")
        logging.info(f"EInputButton_KeyF: {lt.eInputButton.EInputButton_KeyF}")
        IP = map_struct(this, nms_structs.cTkInputPort)
        if leIndex == lt.eInputButton.EInputButton_KeyF:
            logging.info("F pressed!")
            #self.state.inputPort.SetButton(lt.eInputButton.EInputButton_KeyE)
        if leIndex == lt.eInputButton.EInputButton_KeyE:
            logging.info("E pressed!")
        if self.state.inputPort_ptr != this:
            self.state.inputPort_ptr = this
            self.state.inputPort = map_struct(this, nms_structs.cTkInputPort)
            port = self.state.inputPort.port
            buttons = self.state.inputPort.buttons
            buttonsPrev = self.state.inputPort.buttonsPrev
            logging.info(f'InputPort.port: {port}')
            logging.info(f'InputPort.buttons: {buttons}')
            logging.info(f'InputPort.buttonsPrev: {buttonsPrev}')
        else:    
            logging.info(f'InputPort.port: {IP.port}')
            logging.info(f'InputPort.buttons: {IP.buttons}')
            logging.info(f'InputPort.buttonsPrev: {IP.buttonsPrev}') """
    
    """ @hooks.cTkInputPort.SetButton.before
    def capture_key(self, this, leIndex):
        IP = map_struct(this, nms_structs.cTkInputPort)
        logging.info(f"leIndex: {leIndex}")
        if leIndex == 102:
            logging.info("F pressed!")
            logging.info(f'Prev == Current: {IP.buttons == IP.buttonsPrev}')
        if leIndex == lt.eInputButton.EInputButton_KeyF:
            logging.info("eButton_F pressed!")
            #logging.info(f'Prev == Current: {IP.buttons == IP.buttonsPrev}')
            hooks.cTkInputPort.SetButton.original(this, 102) """
    
    @hooks.cTkInputPort.SetButton
    def capture_key(self, this, leIndex):
        IP = map_struct(this, nms_structs.cTkInputPort)
        logging.info(f"leIndex: {leIndex}")
        if leIndex == 102:
            logging.info("F pressed!")
            logging.info(f'Prev == Current: {IP.buttons.ones() == IP.buttonsPrev.one()}')
            hooks.cTkInputPort.SetButton.original(this, 102)
        elif leIndex == 70:
            logging.info("Not F pressed! :[")
            hooks.cTkInputPort.SetButton.original(this, 102)
        elif leIndex != 102:
            logging.info("all other buttons")
            hooks.cTkInputPort.SetButton.original(this, leIndex)


        


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
            

    """ @hooking.on_key_pressed("i")
    def startInterface(self):
        threading.Thread(target=self.main()) """

    """ @hooking.on_key_pressed("j")
    def resetValues(self):
        logging.info(f'self.user_input = ""')
        self.user_input = ""
        logging.info(f'self.user_input_event.clear()')
        self.user_input_event.clear()
        logging.info(f'self.interface_flag.clear()')
        self.interface_flag.clear() """

    """ @hooking.on_key_pressed("o")
    def parseText(self):
        logging.info("\n")
        logging.info("***********  TextChatInput  ***********")
        input_text = common.cTkFixedString[1023]()
        input_text.set(self.state.chatInp.inputTextDisplayString.__str__())
        static_inp_s = common.cTkFixedString[1023]()
        static_inp_s_ptr = ctypes.addressof(static_inp_s)
        call_function("cGcTextChatInput::ParseTextForCommands", self.state.chatInp, static_inp_s_ptr)
        logging.info("\n")

    @hooking.on_key_pressed("space")
    def say(self):
      logging.info(f'Space key pressed')
      static_s = common.cTkFixedString[1023]()
      message = "Hello World\n /enter"
      static_s.set(message)
      static_s_ptr = ctypes.addressof(static_s)
      call_function("cGcTextChatManager::Say", self.state.chatMan, static_s_ptr, False, overload="cGcTextChatManager *, const cTkFixedString<1023,char> *, bool")
      self.text = f"{self.state.value}" """
