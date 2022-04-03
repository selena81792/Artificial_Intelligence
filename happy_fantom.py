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

def character_alone(game_state, color):
    character = find_character(game_state, color)
    nb = len(find_character_pos(game_state, character["position"]))
    return True if nb == 1 else False

def character_shadow(game_state, color):
    character = find_character(game_state, color)
    return character["position"] == game_state["shadow"]

def get_score(game_state):
    score = game_state["position_carlotta"]
    fantom = find_character(game_state, game_state["fantom"])
    suspects = []
    for character in game_state["characters"]:
        if character["suspect"]:
            suspects.append(character)
    if character_alone(game_state, game_state["fantom"]) or character_shadow(game_state, game_state["fantom"]):
        score += 1
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

def remove_character(game_state, color):
    for character in game_state["active character_cards"]:
        if character["color"] == color:
            game_state["active character_cards"].remove(character)
            break
    return game_state

def possible_positions(new_pos, passages, initial_pos, current_pos, distance, blocked):
    for pos in passages[current_pos]:
        if (blocked[0] == current_pos and blocked[1] == pos) \
                or (blocked[0] == pos and blocked[1] == current_pos):
            continue
        if pos in new_pos or pos == initial_pos:
            continue
        new_pos.append(pos)
        if distance > 1:
            possible_positions(new_pos, passages, initial_pos, pos, distance - 1, blocked)

def new_positions(game_state, color, initial_pos, distance):
    new_pos = []
    blocked = game_state["blocked"]

    if color == "pink":
        possible_positions(new_pos, pink_passages, initial_pos, initial_pos, distance, blocked)
    else:
        possible_positions(new_pos, passages, initial_pos, initial_pos, distance, blocked)

    return new_pos

def blocked_positions(game_state, blue_pos):
    blocked = game_state["blocked"]
    new_blocked = []
    for i in range(len(passages)):
        if i == blue_pos:
            continue
        for dest in passages[i]:
            if (dest == blue_pos) \
                    or (blocked[0] == i and blocked[1] == dest) \
                    or (blocked[0] == dest and blocked[1] == i):
                continue
            if [i, dest] in new_blocked or [dest, i] in new_blocked:
                continue
            new_blocked.append([i, dest])
    return new_blocked

def save_solution(game_state, predictions, solutions, color, power_action):
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
        predict_turn(game_state, predictions, solution)
    else:
        predictions.append(solution)


def basic_turn(game_state, character, predictions, solutions, power):
    color = character["color"]
    initial_pos = character["position"]
    distance = len(find_character_pos(game_state, initial_pos))

    for pos in new_positions(game_state, color, initial_pos, distance):
        new_gs = copy.deepcopy(game_state)
        new_gs = update_character(new_gs, color, pos, power)
        new_gs = remove_character(new_gs, color)
        save_solution(new_gs, predictions, solutions, color, 0)


def pink_turn(game_state, character, predictions, solutions):
    basic_turn(game_state, character, predictions, solutions, False)


def blue_turn(game_state, character, predictions, solutions):
    color = character["color"]
    initial_pos = character["position"]
    distance = len(find_character_pos(game_state, initial_pos))

    for pos in new_positions(game_state, color, initial_pos, distance):
        tmp_gs = copy.deepcopy(game_state)
        tmp_gs = update_character(tmp_gs, color, pos, True)
        tmp_gs = remove_character(tmp_gs, color)
        for passage in blocked_positions(tmp_gs, pos):
            new_gs = copy.deepcopy(tmp_gs)
            new_gs["blocked"] = passage
            save_solution(new_gs, predictions, solutions, color, passage)


def purple_turn(game_state, character, predictions, solutions):
    color = character["color"]

    basic_turn(game_state, character, predictions, solutions, False)

    for target in game_state["characters"]:
        tmp_pos = target["position"]
        if target["color"] == color or tmp_pos == character["position"]:
            continue
        new_gs = copy.deepcopy(game_state)
        new_gs = update_character(new_gs, target["color"], character["position"], target["power"])
        new_gs = update_character(new_gs, color, tmp_pos, True)
        new_gs = remove_character(new_gs, color)
        save_solution(new_gs, predictions, solutions, color, target["color"])


def grey_turn(game_state, character, predictions, solutions):
    color = character["color"]
    initial_pos = character["position"]
    distance = len(find_character_pos(game_state, initial_pos))

    for pos in new_positions(game_state, color, initial_pos, distance):
        tmp_gs = copy.deepcopy(game_state)
        tmp_gs = update_character(tmp_gs, color, pos, True)
        tmp_gs = remove_character(tmp_gs, color)
        for shadow_pos in range(10):
            if shadow_pos == tmp_gs["shadow"]:
                continue
            new_gs = copy.deepcopy(tmp_gs)
            new_gs["shadow"] = shadow_pos
            save_solution(new_gs, predictions, solutions, color, new_gs["shadow"])


def white_power(game_state, predictions, solutions, color, pos):
    valid_passages = []
    blocked = game_state["blocked"]

    for passage in passages[pos]:
        if (passage == blocked[0] and blocked[1] == pos) or (passage == blocked[1] and blocked[0] == pos):
            continue
        valid_passages.append(passage)

    for passage in valid_passages:
        power_action = []
        new_gs = copy.deepcopy(game_state)
        for character in find_character_pos(game_state, pos):
            if character["color"] == color:
                continue
            new_gs = update_character(new_gs, character["color"], passage, character["power"])
            power_action.append([character["color"], passage])
        save_solution(new_gs, predictions, solutions, color, power_action)


def white_turn(game_state, character, predictions, solutions):
    color = character["color"]
    initial_pos = character["position"]
    distance = len(find_character_pos(game_state, initial_pos))

    for pos in new_positions(game_state, color, initial_pos, distance):
        new_gs = copy.deepcopy(game_state)
        new_gs = remove_character(new_gs, color)
        new_gs = update_character(new_gs, color, pos, False)

        if character_alone(new_gs, color):
            save_solution(new_gs, predictions, solutions, color, 0)
            continue

        new_gs = update_character(new_gs, color, pos, True)
        white_power(new_gs, predictions, solutions, color, pos)


def black_power_attracting_neighbours(game_state, pos):
    blocked = game_state["blocked"]

    for neighbour in passages[pos]:
        if (neighbour == blocked[0] and pos == blocked[1]) or (neighbour == blocked[1] and pos == blocked[0]):
            continue
        for character in find_character_pos(game_state, neighbour):
            game_state = update_character(game_state, character["color"], pos, character["power"])

    return game_state


def black_turn(game_state, character, predictions, solutions):
    color = character["color"]
    initial_pos = character["position"]
    distance = len(find_character_pos(game_state, initial_pos))

    for pos in new_positions(game_state, color, initial_pos, distance):
        for power in range(2):
            new_gs = copy.deepcopy(game_state)
            if power == 0:
                new_gs = update_character(new_gs, color, pos, False)
            else:
                new_gs = update_character(new_gs, color, pos, True)
                new_gs = black_power_attracting_neighbours(new_gs, pos)
            new_gs = remove_character(new_gs, color)

            save_solution(new_gs, predictions, solutions, color, 0)


def red_turn(game_state, character, predictions, solutions):
    basic_turn(game_state, character, predictions, solutions, True)


def brown_turn(game_state, character, predictions, solutions):
    color = character["color"]
    initial_pos = character["position"]
    distance = len(find_character_pos(game_state, initial_pos))

    for pos in new_positions(game_state, color, initial_pos, distance):
        new_gs = copy.deepcopy(game_state)
        new_gs = update_character(new_gs, color, pos, False)
        new_gs = remove_character(new_gs, color)
        save_solution(new_gs, predictions, solutions, color, 0)

    if not character_alone(game_state, color):
        for target in find_character_pos(game_state, initial_pos):
            if target["color"] == color:
                continue
            for pos in new_positions(game_state, color, initial_pos, distance):
                new_gs = copy.deepcopy(game_state)
                new_gs = update_character(new_gs, color, pos, True)
                new_gs = update_character(new_gs, target["color"], pos, target["power"])
                new_gs = remove_character(new_gs, color)
                save_solution(new_gs, predictions, solutions, color, target["color"])


def predict_turn(game_state, predictions, solutions):

    character_turn = {
        "pink": pink_turn,
        "blue": blue_turn,
        "purple": purple_turn,
        "grey": grey_turn,
        "white": white_turn,
        "black": black_turn,
        "red": red_turn,
        "brown": brown_turn,
    }

    for character in game_state["active character_cards"]:
        character_turn[character["color"]](game_state, character, predictions, solutions)


def find_max_and_reduce_predictions(predictions, depth):
    new_pred = []
    max_score = 0

    for pred in predictions:
        if pred[depth]["score"] > max_score:
            max_score = pred[depth]["score"]

    for pred in predictions:
        if pred[depth]["score"] == max_score:
            new_pred.append(pred)

    return new_pred


def play_turn(game_state, my_answer):
    predictions = []
    predict_turn(game_state, predictions, [])
    depth = len(predictions[0])

    while depth > 0:
        depth -= 1
        predictions = find_max_and_reduce_predictions(predictions, depth)

    index = random.randint(0, len(predictions) - 1)

    my_answer["color"] = predictions[index][0]["data"]["color"]
    my_answer["position"] = predictions[index][0]["data"]["position"]
    my_answer["power"] = predictions[index][0]["data"]["power"]
    my_answer["power_action"] = predictions[index][0]["data"]["power_action"]

    return my_answer


def get_answer(question, data, game_state, my_answer):
    response_index = 0

    if question["question type"] == "select character":
        my_answer = play_turn(game_state, my_answer)
        for character in data:
            if character["color"] == my_answer["color"]:
                response_index = data.index(character)
                break
    elif question["question type"] == "select position":
        response_index = data.index(my_answer["position"])
    elif question["question type"] == "activate " + my_answer["color"] + " power":
        response_index = 1 if my_answer["power"] else 0
    elif question["question type"] == "blue character power room":
        response_index = data.index(my_answer["power_action"][0])
    elif question["question type"] == "blue character power exit":
        response_index = data.index(my_answer["power_action"][1])
    elif question["question type"].startswith("white character power move "):
        color = question["question type"].replace("white character power move ", "")
        for power_action in my_answer["power_action"]:
            if power_action[0] == color:
                response_index = data.index(power_action[1])
                break
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
        response_index = get_answer(question, data, game_state, my_answer)
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