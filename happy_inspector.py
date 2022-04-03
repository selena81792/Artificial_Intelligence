import json
import logging
import os
import random
import socket
from enum import Enum
from logging.handlers import RotatingFileHandler
from collections import Counter
import math

import protocol

host = "localhost"
port = 12000
# HEADERSIZE = 10

"""
set up inspector logging
"""
inspector_logger = logging.getLogger()
inspector_logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    "%(asctime)s :: %(levelname)s :: %(message)s", "%H:%M:%S")
# file
if os.path.exists("./logs/inspector.log"):
    os.remove("./logs/inspector.log")
file_handler = RotatingFileHandler('./logs/inspector.log', 'a', 1000000, 1)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
inspector_logger.addHandler(file_handler)
# stream
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.WARNING)
inspector_logger.addHandler(stream_handler)


class Color(Enum):
    WHITE = "white"
    RED = "red"
    BLACK = "black"
    PURPLE = "purple"
    GREY = "grey"
    BROWN = "brown"
    BLUE = "blue"
    PINK = "pink"

class PlayerPos():
    color = ""
    position = 0
    suspect =  False
    isAlone = False

    def __init__(self, clr, pos, sus):
        self.color = clr
        self.position = pos
        self.suspect = sus

class StateDirection(Enum):
    STAY = 0
    SEPARATE = 1
    REGROUP = 2


listPlayerSuspect = []
listPlayer = []

class Player():


    number_alone = 0
    number_not_alone = 0
    number_suspect = 0
    how_many_change_state = 0
    state = StateDirection.REGROUP
    selected_color = ""
    selected_character = PlayerPos("", 0, False)
   
    def __init__(self):

        self.end = False
        # self.old_question = ""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def connect(self):
        self.socket.connect((host, port))

    def reset(self):
        self.socket.close()

    def answer(self, question):
        # work
        data = question["data"]
        game_state = question["game state"]
        
        # analyze the question and the game state to give the right answer
        response_index = self.analyze_question(question, data, game_state)

        # log
        inspector_logger.debug("|\n|")
        inspector_logger.debug("inspector answers")
        inspector_logger.debug(f"question type ----- {question['question type']}")
        inspector_logger.debug(f"data -------------- {data}")
        inspector_logger.debug(f"game data ----- {question['game state']}")
        inspector_logger.debug(f"response index ---- {response_index}")
        inspector_logger.debug(f"response ---------- {data[response_index]}")
        return response_index

    def how_many_suspect_change_state(self, state, data):
        if (state == StateDirection.SEPARATE):
            self.how_many_change_state = math.ceil((self.number_not_alone - self.number_alone) / 2)
            return self.chooseCharacter_separate(data)
        if (state == StateDirection.REGROUP):
            self.how_many_change_state = math.ceil((self.number_alone - self.number_not_alone) / 2)
            return self.chooseCharacter_regroup(data)
        else:
            return self.chooseCharacter_stay(data)
            
    # decide in which direction our AI will go : either separate suspect from groups, regroup suspects, or keep same state (suspects in group and alone at the same position)
    def do_we_separate(self, game_state):
        listPlayer.clear()
        listPlayerSuspect.clear()
        for d in game_state["characters"]:
            listPlayer.append(PlayerPos(d['color'], d['position'], d['suspect']))
        index = 0
        for player in listPlayer:
            # check if the character is alone or not
            if (([character.position for character in listPlayer].count(player.position) == 1) or game_state["shadow"] == player.position):
                if (player.suspect):
                    self.number_alone += 1
                listPlayer[index].isAlone = True
            if (player.suspect):
                listPlayerSuspect.append(listPlayer[index])
            index += 1
        self.number_suspect = len(listPlayerSuspect)
        self.number_not_alone = self.number_suspect - self.number_alone
        if (self.number_not_alone > self.number_alone):
            return StateDirection.SEPARATE
        if (self.number_alone > self.number_not_alone):
            return StateDirection.REGROUP
        else:
            return StateDirection.STAY

    # we choose our color depending og the state for our AI (separate, regroup, stay)
    def chooseCharacter_separate(self, data: list):
        index = 0
        if any(d['color'] == 'white' for d in data):
            index = next((index for (index, d) in enumerate(data) if d["color"] == "white"), None)
            return index
        if any(d['color'] == 'purple' for d in data):
            index = next((index for (index, d) in enumerate(data) if d["color"] == "purple"), None)
            pos = data[index]["position"]
            if ([character.position for character in listPlayer].count(pos) == 1):
                return index
        if any(d['color'] == 'brown' for d in data):
            index = next((index for (index, d) in enumerate(data) if d["color"] == "brown"), None)
            pos = data[index]["position"]
            if ([character.position for character in listPlayer].count(pos) == 3):
                for player in listPlayer:
                    if (player.color != "brown" and player.position == pos and player.suspect == True):
                        return index
        if any(d['color'] == 'grey' for d in data):
            index = next((index for (index, d) in enumerate(data) if d["color"] == "grey"), None)
            return index
        if any(d['color'] == 'pink' for d in data):
            index = next((index for (index, d) in enumerate(data) if d["color"] == "pink"), None)
            return index
        if any(d['color'] == 'black' for d in data):
            index = next((index for (index, d) in enumerate(data) if d["color"] == "black"), None)
            return index
        return random.randint(0, len(data)-1)


    def chooseCharacter_regroup(self, data: list):
        index = 0
        if any(d['color'] == 'black' for d in data):
            index = next((index for (index, d) in enumerate(data) if d["color"] == "black"), None)
            return index
        if any(d['color'] == 'purple' for d in data):
            index = next((index for (index, d) in enumerate(data) if d["color"] == "purple"), None)
            pos = data[index]["position"]
            if ([character.position for character in listPlayer].count(pos) > 1):
                return index
        if any(d['color'] == 'brown' for d in data):
            index = next((index for (index, d) in enumerate(data) if d["color"] == "brown"), None)
            pos = data[index]["position"]
            if ([character.position for character in listPlayer].count(pos) > 1):
                for player in listPlayer:
                    if (player.color != "brown" and player.position == pos and player.suspect == False):
                        return index
        if any(d['color'] == 'pink' for d in data):
            index = next((index for (index, d) in enumerate(data) if d["color"] == "pink"), None)
            return index
        if any(d['color'] == 'white' for d in data):
            index = next((index for (index, d) in enumerate(data) if d["color"] == "white"), None)
            return index
        if any(d['color'] == 'grey' for d in data):
            index = next((index for (index, d) in enumerate(data) if d["color"] == "grey"), None)
            return index
        return random.randint(0, len(data)-1)


    def chooseCharacter_stay(self, data: list):
        index = 0
        if any(d['color'] == 'blue' for d in data):
            index = next((index for (index, d) in enumerate(data) if d["color"] == "blue"), None)
            return index
        if any(d['color'] == 'purple' for d in data):
            index = next((index for (index, d) in enumerate(data) if d["color"] == "purple"), None)
            return index
        if any(d['color'] == 'pink' for d in data):
            index = next((index for (index, d) in enumerate(data) if d["color"] == "pink"), None)
            return index
        if any(d['color'] == 'grey' for d in data):
            index = next((index for (index, d) in enumerate(data) if d["color"] == "grey"), None)
            return index
        if any(d['color'] == 'brown' for d in data):
            index = next((index for (index, d) in enumerate(data) if d["color"] == "brown"), None)
            return index
        if any(d['color'] == 'black' for d in data):
            index = next((index for (index, d) in enumerate(data) if d["color"] == "black"), None)
            return index

    def select_character(self, question, data: list, game_state):
        if (len(data) == 1):
            self.selected_color = data[0]["color"]
            return 0
        index = next((index for (index, d) in enumerate(data) if d["color"] == "red"), None)
        self.do_we_separate(game_state)
        if (index != None):
            self.selected_color = "red"
            return index
        state = self.do_we_separate(game_state)
        index = self.how_many_suspect_change_state(state, data)
        self.selected_color = data[index]["color"]
        self.selected_character = next((x for x in listPlayer if x.color == self.selected_color), None)
        return index
        

    def get_room_with_less_people(self, data):
        players = 9
        room = 0
        for pos in data:
            nb_in_room = [player.position for player in listPlayer].count(pos)
            if (players > nb_in_room):
                players = nb_in_room
                room = pos
        return room

    # we choose our position depending on the state of the AI (separate, regroup, or stay)
    def choosePosition_separate(self, data):
        goToPos = -1
        character = next((x for x in listPlayer if x.color == self.selected_color), None)
        if (character.suspect == True):
            for pos in data:
                nb_in_room = [player.position for player in listPlayer].count(pos)
                if ((nb_in_room == 0 and character.color != Color.WHITE.value) or (nb_in_room > 0 and character.color == Color.WHITE.value)):
                    goToPos = pos       
            if (goToPos == -1):
                goToPos = self.get_room_with_less_people(data)
        else:
            for pos in data:
                nb_in_room = [player.position for player in listPlayerSuspect].count(pos)
                if ((nb_in_room == 0 and character.color != Color.WHITE.value) or (nb_in_room > 1 and character.color == Color.WHITE.value)):
                    goToPos = pos       
            if (goToPos == -1):
                goToPos = self.get_room_with_less_people(data)
        self.selected_character.position = goToPos
        if ([character.position for character in listPlayer].count(goToPos) == 0):
            self.selected_character.isAlone = True
        else:
            self.selected_character.isAlone = False
        return data.index(goToPos)
        
    def choosePosition_regroup(self, data):
        goToPos = -1
        character = next((x for x in listPlayer if x.color == self.selected_color), None)
        if (character.suspect == True):
            for pos in data:
                nb_in_room = [player.position for player in listPlayer].count(pos)
                if ((nb_in_room > 0 and character.color != Color.BLACK.value) or (nb_in_room == 0 and character.color == Color.BLACK.value)):
                    goToPos = pos       
            if (goToPos == -1):
                goToPos = self.get_room_with_less_people(data)
        else:
            for pos in data:
                nb_in_room = [player.position for player in listPlayerSuspect].count(pos)
                if ((nb_in_room > 0 and character.color != Color.BLACK.value) or (nb_in_room == 0 and character.color == Color.BLACK.value)):
                    goToPos = pos    
            if (goToPos == -1):
                goToPos = self.get_room_with_less_people(data)
        self.selected_character.position = goToPos
        if ([character.position for character in listPlayer].count(goToPos) == 0):
            self.selected_character.isAlone = True
        else:
            self.selected_character.isAlone = False
        return data.index(goToPos)

    def choosePosition_stay(self, data):
        goToPos = -1
        character = next((x for x in listPlayer if x.color == self.selected_color), None)
        for pos in data:
            nb_in_room = [player.position for player in listPlayer].count(pos)
            if character.isAlone:
                if (nb_in_room == 0):
                    goToPos = pos
            else:
                if (nb_in_room > 1):
                    goToPos = pos

        if (goToPos == -1):
            goToPos = self.get_room_with_less_people(data)
        self.selected_character.position = goToPos
        if ([character.position for character in listPlayer].count(goToPos) == 0):
            self.selected_character.isAlone = True
        else:
            self.selected_character.isAlone = False
        return data.index(goToPos)

    def select_Position(self, data):
        if (self.state == StateDirection.SEPARATE):
            return self.choosePosition_separate(data)
        if (self.state == StateDirection.REGROUP):
            return self.choosePosition_regroup(data)
        else:
            return self.choosePosition_stay(data)

    # we split and analyze every part of the question asked
    def analyze_question(self, question, data, game_state):
        arrayQuestionsType = question['question type'].split()
        index = random.randint(0, len(data)-1)
        if (arrayQuestionsType[0] == "select"):
            if (arrayQuestionsType[1] == "character"):
                index = self.select_character(question, data, game_state)
            elif (arrayQuestionsType[1] == "position"):
                index = self.select_Position(data)
        elif (arrayQuestionsType[0] == "activate"):
            index = self.color_activate(arrayQuestionsType[1])
        else:
            index = self.ask_for_color_power(arrayQuestionsType, arrayQuestionsType[0], data, game_state)
        return index

    # Ensure if I want to activate power or not
    def color_activate(self, color):
        # these colors are not mandatory
        if (color == Color.PURPLE.value):
            if (self.state == StateDirection.SEPARATE):
                if ((self.selected_character.isAlone and self.selected_character.suspect) or self.selected_character.suspect == False and self.selected_character.isAlone == False):
                    return 0
                return 1
            elif (self.state == StateDirection.REGROUP):
                if ((self.selected_character.isAlone and self.selected_character.suspect) or self.selected_character.suspect == False and self.selected_character.isAlone == False):
                    return 1
                return 0
            else:
                return 0

        elif (color == Color.WHITE.value):
            if (self.selected_character.isAlone == False):
                return 1
            else:
                return 0
        elif (color == Color.BLACK.value):
            if (self.state == StateDirection.REGROUP):
                return 1
            return  0
        elif (color == Color.BROWN.value):
            if (self.selected_character.isAlone == False):
                if ((self.state == StateDirection.REGROUP or self.state == StateDirection.STAY) and [player.position for player in listPlayer].count(self.selected_character.position) > 2):
                    return 0
                return 1
            else:
                return 0

    # decide with who purple will exchange his place
    def manage_purple_power(self, data):
        if (self.state == StateDirection.SEPARATE):
            if (self.selected_character.suspect):
                # we look for an alone innocent
                for color in data:
                    character = next((x for x in listPlayer if x.color == color), None)
                    if (character.isAlone and character.suspect == False):
                        return data.index(color)
                character = next((x for x in listPlayer if x.suspect == False))
                return data.index(character.color)
            else:
                # we look for a suspect alone
                for color in data:
                    character = next((x for x in listPlayer if x.color == color), None)
                    if (character.isAlone == False and character.suspect):
                        return data.index(color)
                character = next((x for x in listPlayer if x.suspect == True))
                return data.index(character.color)
        elif (self.state == StateDirection.REGROUP):
            if (self.selected_character.suspect):
                # we look for an innocent in group
                for color in data:
                    character = next((x for x in listPlayer if x.color == color), None)
                    if (character.isAlone == False and character.suspect == False):
                        return data.index(color)
                character = next((x for x in listPlayer if x.isAlone == True))
                return data.index(character.color)
            else:
                # we look for a suspect alone
                for color in data:
                    character = next((x for x in listPlayer if x.color == color), None)
                    if (character.isAlone == True and character.suspect):
                        return data.index(color)
                character = next((x for x in listPlayer if x.isAlone == False))
                return data.index(character.color)

    # To get details for asked power
    # and decide how power will be used 
    def ask_for_color_power(self, arrayQuestionsType, color, data, game_state):
        if (color == Color.PURPLE.value):
            return self.manage_purple_power(data)
        elif (color == Color.BLUE.value):
            if (arrayQuestionsType[3] == "room"):
                pass
            elif (arrayQuestionsType[3] == "exit"):
                pass
        elif (color == Color.BROWN.value):
            if (self.state == StateDirection.SEPARATE):
                # wee look for an innoncent
                for color in data:
                    character = next((x for x in listPlayer if x.color == color), None)
                    if (character.suspect == False):
                        return data.index(color)
                character = next((x for x in listPlayer if x.suspect == True))
                return data.index(character.color)
            else:
                return 0
        elif (color == Color.GREY.value):
            if (self.state == StateDirection.SEPARATE):
                for pos in data:
                    # we look for a suspect alone
                    character = next((x for x in listPlayer if x.position == pos), None)
                    if (character.isAlone == False and character.suspect):
                        return data.index(pos)
                character = next((x for x in listPlayer if x.suspect == True), None)
                return data.index(character.position)
            else:
                for pos in data:
                    # we look for a suspect alone
                    character = next((x for x in listPlayer if x.position == pos), None)
                    if (character != None and character.isAlone == True and character.suspect):
                        return data.index(pos)
                character = next((x for x in listPlayer if x.suspect == True and game_state["shadow"] != x.position), None)
                return data.index(character.position)
        elif (color == Color.WHITE.value):
            # moves the players in same room
            return self.define_white_power_data(arrayQuestionsType[4], data)
        return random.randint(0, len(data)-1)

    # the white power moves players in adjacent rooms depending on the state
    def define_white_power_data(self, character, data):
        self.selected_color = character
        if (self.state == StateDirection.SEPARATE):
            return self.choosePosition_separate(data)
        elif (self.state == StateDirection.REGROUP):
            return self.choosePosition_regroup(data)
        else:
            return self.choosePosition_stay(data)

    def handle_json(self, data):
        data = json.loads(data)
        response = self.answer(data)
        # send back to server
        bytes_data = json.dumps(response).encode("utf-8")
        protocol.send_json(self.socket, bytes_data)

    def run(self):

        self.connect()

        while self.end is not True:
            received_message = protocol.receive_json(self.socket)
            if received_message:
                self.handle_json(received_message)
            else:
                print("no message, finished learning")
                self.end = True

p = Player()

p.run()