import requests

from flask import redirect, render_template, session
from functools import wraps
import random
from string import ascii_uppercase

def login_required(f):
    #https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

#def create_game(room):
#    board = room['board']
#    current_player = 'X' if room['turn'] == 1 else 'O'
#    last_move = room['last_move']
#    if room["won"] == 1:
#        winner = 'X WON!'
#    elif room["won"] == 2:
#        winner = 'O WON!'
#    elif room["won"] == 3:
#        winner = 'Tie'
#    else:
#        winner = None
#    winning_combination = [room['winning_combination']//100, room['winning_combination']%100//10, room['winning_combination']%10]
#    game = TicTacToe(list(board), current_player, last_move, winner=winner, winning_combination=winning_combination)
#    return game

def generate_room_code(rooms):
    while True:
        code = ''.join(random.choice(ascii_uppercase) for _ in range(4))
        for room in rooms:
            if room['code'] == code:
                break
        else:
            break
    return ''.join(random.choice(ascii_uppercase) for _ in range(4))

class TicTacToe:
    def __init__(self, board=[' '] * 81, current_player='X', last_move=10, winner=None, winning_combination=[1, 0, 0]):
        self.board = board
        self.board_alt = []
        for item in self.board:
            self.board_alt.append(item)
        self.current_player = current_player
        self.last_move = last_move
        self.winner = winner
        self.winning_combination = winning_combination
        self.winning_combinations = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],
            [0, 3, 6], [1, 4, 7], [2, 5, 8],
            [0, 4, 8], [2, 4, 6]
        ]

        self.check_winner()
        self.check_winner_sub()

    def check_winner_sub(self):
        self.board_alt = []
        for item in self.board:
            self.board_alt.append(item)
        for i in range(0, 81, 9):
            chunk = self.board_alt[i:i + 9]
            winner = None  
            for combo in self.winning_combinations:
                if chunk[combo[0]] == chunk[combo[1]] == chunk[combo[2]] and chunk[combo[0]] != ' ':
                    winner = chunk[combo[0]]
                    break
            if winner:
                for j in range(9):
                    self.board_alt[i + j] = winner
    
    def make_move(self, position):
        if position == None or self.winner:
            return False
        if position == -1:
            other_player = 'X' if self.current_player == 'O' else 'O'
            #self.board_alt = [other_player] * 81
            self.current_player = 'O' if self.current_player == 'X' else 'X'
            self.check_winner(surrender=True, other_player=other_player)
            self.winning_combination = [9, 0, 0]
            return True
        if self.board_alt[position] == ' ':
            if (position < (self.last_move + 1) * 9 and position >= self.last_move * 9) or self.last_move == 10:
                self.board[position] = self.current_player
                self.current_player = 'O' if self.current_player == 'X' else 'X'
                self.check_winner_sub()

                if ' ' not in self.board_alt[position % 9 * 9: position % 9 * 9 + 9]:
                    self.last_move = 10
                else:
                    self.last_move = position % 9
                self.check_winner()
                return True
            return False
    
    def check_winner(self, surrender=False, other_player=None):
        for combination in self.winning_combinations:
            if (surrender or self.board_alt[combination[0]*9:combination[0]*9+9] == self.board_alt[combination[1]*9:combination[1]*9+9] 
                == self.board_alt[combination[2]*9:combination[2]*9+9] == [self.board_alt[combination[0]*9] for _ in range(9)] != [' ']*9):
                self.winning_combination = combination
                if surrender:
                    self.winner = other_player + ' WON!'
                else: 
                    self.winner = self.board_alt[combination[0]*9] + ' WON!'
                return 
        if ' ' not in self.board_alt:
            self.winner = 'Tie'
            return 
    
