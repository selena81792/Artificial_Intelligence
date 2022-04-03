import json
import logging
import os
import random
import socket
from logging.handlers import RotatingFileHandler

import protocol
import copy

host = "localhost"
port = 12000
# HEADERSIZE = 10

"""
set up fantom logging
"""
fantom_logger = logging.getLogger()
fantom_logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    "%(asctime)s :: %(levelname)s :: %(message)s", "%H:%M:%S")
# file
if os.path.exists("./logs/fantom.log"):
    os.remove("./logs/fantom.log")
file_handler = RotatingFileHandler('./logs/fantom.log', 'a', 1000000, 1)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
fantom_logger.addHandler(file_handler)
# stream
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.WARNING)
fantom_logger.addHandler(stream_handler)

passages = [{1, 4}, {0, 2}, {1, 3}, {2, 7}, {0, 5, 8},
            {4, 6}, {5, 7}, {3, 6, 9}, {4, 9}, {7, 8}]
pink_passages = [{1, 4}, {0, 2, 5, 7}, {1, 3, 6}, {2, 7}, {0, 5, 8, 9},
                 {4, 6, 1, 8}, {5, 7, 2, 9}, {3, 6, 9, 1}, {4, 9, 5},
                 {7, 8, 4, 6}]

def find_character(game_state, color):
    target = {}
    for character in game_state["characters"]:
        if character["color"] == color:
            target = character
            break
    return target

def find_character_pos(game_state, position):
    targets = []
    for character in game_state["characters"]:
        if character["position"] == position:
            targets.append(character)
    return targets

def character_shadow(game_state, color):
    character = find_character(game_state, color)
    return character["position"] == game_state["shadow"]

def character_alone(game_state, color):
    character = find_character(game_state, color)
    nb = len(find_character_pos(game_state, character["position"]))
    return True if nb == 1 else False

def new_positions_loop(possible_positions, passages, initial_pos, current_pos, distance, blocked):
    for pos in passages[current_pos]:
        if pos in possible_positions or pos == initial_pos:
            continue
        if (blocked[0] == current_pos and blocked[1] == pos) or (blocked[0] == pos and blocked[1] == current_pos):      # not possible if blocked
            continue
        possible_positions.append(pos)
        if distance > 1:
            new_positions_loop(possible_positions, passages, initial_pos, pos, distance - 1, blocked)

def new_positions(game_state, color, initial_pos, distance):
    possible_positions = []
    if color == "pink":     # pink character can use secret passages
        new_positions_loop(possible_positions, pink_passages, initial_pos, initial_pos, distance, game_state["blocked"])
    else:                   # normal character cannot use secret passages
        new_positions_loop(possible_positions, passages, initial_pos, initial_pos, distance, game_state["blocked"])
    return possible_positions

def remove_character(game_state, color):
    for character in game_state["active character_cards"]:
        if character["color"] == color:
            game_state["active character_cards"].remove(character)
            break
    return game_state

def update_character(game_state, color, pos, power):
    for character in game_state["characters"]:
        if character["color"] == color:
            character["position"] = pos
            character["power"] = power
    for character in game_state["character_cards"]:
        if character["color"] == color:
            character["position"] = pos
            character["power"] = power
    return game_state

def get_score(game_state):
    score = game_state["position_carlotta"]
    suspects = []
    fantom = find_character(game_state, game_state["fantom"])
    for character in game_state["characters"]:
        if character["suspect"]:
            suspects.append(character)
    if character_alone(game_state, game_state["fantom"]) or character_shadow(game_state, game_state["fantom"]):
        score += 1          # phantom screams
        for suspect in suspects:
            if character_alone(game_state, suspect["color"]):
                score += 1
                continue
            if character_shadow(game_state, suspect["color"]):
                score += 1
    else:
        for suspect in suspects:
            if not character_alone(game_state, suspect["color"]) and not character_shadow(game_state, suspect["color"]):
                score += 1
    return score

def possible_new_blocks(blocked, blue_pos):
    new_blocked = []
    for i in range(len(passages)):
        if i == blue_pos:       # cannot block myself
            continue
        for dest in passages[i]:
            if (dest == blue_pos) or (blocked[0] == i and blocked[1] == dest) or (blocked[0] == dest and blocked[1] == i):
                continue
            if [i, dest] in new_blocked or [dest, i] in new_blocked:
                continue
            new_blocked.append([i, dest])
    return new_blocked

def find_best_move(tree, depth):
    good_choices = []
    max_score = 0
    for branch in tree:
        if branch[depth]["score"] > max_score:
            max_score = branch[depth]["score"]
    for branch in tree:
        if branch[depth]["score"] == max_score:
            good_choices.append(branch)
    return good_choices

def do_turn_characters(game_state, tree, solutions):
    move_character_functions = {
        "red": move_red,
        "pink": move_pink,
        "blue": move_blue,
        "grey": move_grey,
        "black": move_black,
        "white": move_white,
        "purple": move_purple,
        "brown": move_brown,
    }
    for character in game_state["active character_cards"]:
        move_character_functions[character["color"]](game_state, character, tree, solutions)

def do_turn(game_state, my_answer):
    answer = []
    do_turn_characters(game_state, answer, [])
    depth = len(answer[0])
    while depth > 0:
        depth -= 1
        answer = find_best_move(answer, depth)
    my_answer["color"] = answer[0][0]["data"]["color"]
    my_answer["position"] = answer[0][0]["data"]["position"]
    my_answer["power"] = answer[0][0]["data"]["power"]
    my_answer["power_action"] = answer[0][0]["data"]["power_action"]
    return my_answer

def new_move(game_state, tree, solutions, color, power_action):
    depth = len(game_state["active character_cards"])
    info = find_character(game_state, color)
    data = {
        "color": info["color"],
        "suspect": info["suspect"],
        "position": info["position"],
        "power": info["power"],
        "power_action": power_action
    }
    solution = copy.deepcopy(solutions)
    solution.append({"depth": depth, "data": data, "score": get_score(game_state)})
    if depth == 2:
        do_turn_characters(game_state, tree, solution)
    else:
        tree.append(solution)

def move_character(game_state, character, tree, solutions, power):
    color = character["color"]
    position = character["position"]
    distance = len(find_character_pos(game_state, position))     # character can move no. X of steps from room with X people inside
    for pos in new_positions(game_state, color, position, distance):
        t_game_state = copy.deepcopy(game_state)
        t_game_state = update_character(t_game_state, color, pos, power)
        t_game_state = remove_character(t_game_state, color)
        new_move(t_game_state, tree, solutions, color, 0)

def move_red(game_state, character, tree, solutions):    # Raoul De Chagny can draw a card
    move_character(game_state, character, tree, solutions, True)

def move_pink(game_state, character, tree, solutions):   # Meg Giry can use secret passages
    move_character(game_state, character, tree, solutions, False)

def move_blue(game_state, character, tree, solutions):   # Madame Giry can change block
    color = character["color"]
    position = character["position"]
    distance = len(find_character_pos(game_state, position))    # character can move no. X of steps from room with X people inside
    for pos in new_positions(game_state, color, position, distance):
        t_game_state_2 = copy.deepcopy(game_state)
        t_game_state_2 = update_character(t_game_state_2, color, pos, True)
        t_game_state_2 = remove_character(t_game_state_2, color)
        for passage in possible_new_blocks(t_game_state_2["blocked"], pos):
            t_game_state = copy.deepcopy(t_game_state_2)
            t_game_state["blocked"] = passage
            new_move(t_game_state, tree, solutions, color, passage)

def move_grey(game_state, character, tree, solutions):   # Joseph Buquet can move shadow room
    color = character["color"]
    position = character["position"]
    distance = len(find_character_pos(game_state, position))
    for pos in new_positions(game_state, color, position, distance):
        t_game_state_2 = copy.deepcopy(game_state)
        t_game_state_2 = update_character(t_game_state_2, color, pos, True)
        t_game_state_2 = remove_character(t_game_state_2, color)
        for shadow_pos in range(10):        # iterate through all possible new shadow room
            if shadow_pos == t_game_state_2["shadow"]:
                continue
            t_game_state = copy.deepcopy(t_game_state_2)
            t_game_state["shadow"] = shadow_pos
            new_move(t_game_state, tree, solutions, color, t_game_state["shadow"])

def move_black_power(t_game_state, pos):
    blocked = t_game_state["blocked"]
    for neighbour in passages[pos]:
        if (neighbour == blocked[0] and pos == blocked[1]) or (neighbour == blocked[1] and pos == blocked[0]):
            continue
        for character in find_character_pos(t_game_state, neighbour):
            t_game_state = update_character(t_game_state, character["color"], pos, character["power"])
    return t_game_state

def move_black(game_state, character, tree, solutions):  # Christine Daae can attract others
    color = character["color"]
    position = character["position"]
    distance = len(find_character_pos(game_state, position))
    for pos in new_positions(game_state, color, position, distance):
        for power in range(2):
            t_game_state = copy.deepcopy(game_state)
            if power == 0:
                t_game_state = update_character(t_game_state, color, pos, False)
            else:
                t_game_state = update_character(t_game_state, color, pos, True)
                t_game_state = move_black_power(t_game_state, pos)
            t_game_state = remove_character(t_game_state, color)
            new_move(t_game_state, tree, solutions, color, 0)

def move_white(game_state, character, tree, solutions):  # M. Moncharmin can force others to leave
    move_character(game_state, character, tree, solutions, False)

def move_purple(game_state, character, tree, solutions):     # M. Richard can swap position with other character
    move_character(game_state, character, tree, solutions, False)

def move_brown(game_state, character, tree, solutions):  # The Persian can take a character with him to move
    move_character(game_state, character, tree, solutions, False)

def respond(question, data, game_state, my_answer):
    response_index = 0
    if question["question type"] == "select character":
        my_answer = do_turn(game_state, my_answer)
        for character in data:
            if character["color"] == my_answer["color"]:
                response_index = data.index(character)
                break
    elif question["question type"] == "select position":
        response_index = data.index(my_answer["position"])
    elif question["question type"] == "activate " + my_answer["color"] + " power":
        if my_answer["power"]:
            response_index = 1
        else:
            response_index = 0
    elif question["question type"] == "blue character power room":
        response_index = data.index(my_answer["power_action"][0])
    elif question["question type"] == "blue character power exit":
        response_index = data.index(my_answer["power_action"][1])
    else:
        response_index = data.index(my_answer["power_action"])
    return response_index

class Player():

    def __init__(self):

        self.end = False
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def connect(self):
        self.socket.connect((host, port))

    def reset(self):
        self.socket.close()

    def answer(self, question, my_answer):
        # work
        data = question["data"]
        game_state = question["game state"]
        response_index = respond(question, data, game_state, my_answer)
        # log
        fantom_logger.debug("|\n|")
        fantom_logger.debug("fantom answers")
        fantom_logger.debug(f"question type ----- {question['question type']}")
        fantom_logger.debug(f"data -------------- {data}")
        fantom_logger.debug(f"response index ---- {response_index}")
        fantom_logger.debug(f"response ---------- {data[response_index]}")
        return response_index

    def handle_json(self, data, my_answer):
        data = json.loads(data)
        response = self.answer(data, my_answer)
        # send back to server
        bytes_data = json.dumps(response).encode("utf-8")
        protocol.send_json(self.socket, bytes_data)

    def run(self):

        self.connect()

        my_answer = {"color": "", "position": 0, "power": False, "power_action": 0}
        while self.end is not True:
            received_message = protocol.receive_json(self.socket)
            if received_message:
                self.handle_json(received_message, my_answer)
            else:
                print("no message, finished learning")
                self.end = True


p = Player()

p.run()