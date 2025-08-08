import os

from cs50 import SQL
from flask import Flask, redirect, render_template, request, session, jsonify
from flask_socketio import SocketIO, join_room, leave_room, send
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import login_required, TicTacToe, generate_room_code

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["jsonify"] = jsonify

# Configure session
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["SECRET_KEY"] = "super secret key"
app.config["DEBUG"] = True
app.config['TEMPLATES_AUTO_RELOAD'] = True
Session(app)

socketio = SocketIO(app)

# SQLite database
db = SQL("sqlite:///project.db")

def rooom():
    """Load all rooms from the database and create TicTacToe instances"""
    global rooms, game

    rooms = db.execute("SELECT code, player_one_id, player_two_id, board, turn, last_move, won, winning_combination FROM rooms")
    for room in rooms:
        board = room['board']
        current_player = 'X' if room['turn'] == 1 else 'O'
        last_move = room['last_move']
        if room["won"] == 1:
            winner = 'X WON!'
        elif room["won"] == 2:
            winner = 'O WON!'
        elif room["won"] == 3:
            winner = 'Tie'
        else:
            winner = None
        winning_combination = [room['winning_combination']//100, room['winning_combination']%100//10, room['winning_combination']%10]
        game = TicTacToe(list(board), current_player, last_move, winner=winner, winning_combination=winning_combination)
        room["game"] = game

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/login")

@app.after_request
def after_request(response):
    # Load from the server, istead of a cached copy.    
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    
    return None
    #return render_template("index.html", board=game.board)


@app.route("/rules", methods=["GET", "POST"])
@login_required
def rules():
    

    return render_template("rules.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        if not request.form.get("username"):
            return redirect("/login")
            #return render_template("error.html", message="Please enter a username", code=400)
        if not request.form.get("password"):
            return redirect("/login")
            #return render_template("error.html", message="Please enter a password", code=400)

        # Query database for username
        rows = db.execute("SELECT id, hash FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return redirect("/login")
            #return render_template("error.html", message="Invalid username and/or password", code=400)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return rules()

    # User reached route via GET (as by clicking a link or via redirect)
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":
        return render_template("register.html")
    
    if not request.form.get("username"):
        return redirect("/register")
        return render_template("error.html", message="Please enter a username", code=400)
    
    if db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username")):
        return redirect("/register")
        return render_template("error.html", message="Username already taken", code=400)

    if not request.form.get("password") or not request.form.get("password_2"):
        return redirect("/register")
        return render_template("error.html", message="Please enter a password", code=400)
    
    if request.form.get("password") != request.form.get("password_2"):
        return redirect("/register")
        return render_template("error.html", message="Passwords don't match", code=400)
    
    username = request.form.get("username")
    password = request.form.get("password")
    hash = generate_password_hash(password)

    try:
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, hash)
    except:
        return redirect("/register")
        return render_template("error.html", message="Username already taken", code=400)

    session["user_id"] = db.execute("SELECT id FROM users WHERE username=?", username)[0]["id"]
    return rules()

    return render_template("register.html")

@app.route("/make_move", methods=["POST"])
def make_move():
    if not session.get("code"): 
        return redirect("/play")
    for room in rooms:
        if room['code'] == session["code"]:
            game: TicTacToe = room["game"]
            user_player = 'X' if session["user_id"] == room['player_one_id'] else 'O'
            break

        
    data = request.get_json()
    position = data["position"]
    winning_combination = game.winning_combination
    if game.current_player == user_player or position == -1:
        if (room["player_two_id"] and game.make_move(position)):
            turn = 1 if game.current_player == 'X' else 2
            winner = 1 if game.winner == 'X WON!' else 2 if game.winner == 'O WON!' else 3 if game.winner == 'Tie' else 0
            if game.winning_combination:
                winning_combination = int(''.join(map(str, game.winning_combination)))
            else:
                winning_combination = 100
            db.execute("UPDATE rooms SET board=?, turn=?, last_move=?, won=?, winning_combination=? WHERE code=?", ''.join(game.board), turn, game.last_move, winner, winning_combination, session["code"])
            return jsonify({'status': 'success', 'winner': game.winner, 'winning_combination': game.winning_combination, 'board': game.board_alt, 'last_move': game.last_move, 'current_player': game.current_player})
    
    if not session.get("code"):
        return redirect("/play")
    return jsonify({'status': 'error', 'message': 'Invalid move', 'winner': game.winner, 'winning_combination': game.winning_combination, 'board': game.board_alt, 'last_move': game.last_move, 'current_player': game.current_player})

@login_required
@app.route("/play", methods=["GET", "POST"])
def play(status=""):
    rooom()
    if request.method == "GET":
        return render_template("play.html", message=status)
    if request.form.get("code"): # Enter a room
        code = request.form.get("code")
        
        for room in rooms:
            if room['code'] == code:
                break # now room is the room with the code
        else:
            return render_template("play.html", message="Room does not exist") # room does not exist

        if session["user_id"] == room['player_one_id']: # user is in the room
            session["code"] = code
            
            return redirect("/room") # redirect to room

        if room['player_two_id']: 
            if session["user_id"] == room['player_two_id']: # room is full but user is in it already
                session["code"] = code
                return redirect("/room") # redirect to room

        if not room['player_two_id']: # room has a free spot
            session["code"] = code
            room['player_two_id'] = session["user_id"]
            db.execute("UPDATE rooms SET player_two_id=? WHERE code=?", session["user_id"], code)
            return redirect("/room")
        return render_template("play.html", status="Room is full")
    else:
        code = generate_room_code(rooms)
        session["code"] = code
        db.execute("INSERT INTO rooms (code, player_one_id) VALUES (?, ?)", code, session["user_id"])
        rooms.append({"code": code, "player_one_id": session["user_id"], "player_two_id": None,
                      "board": ''.join(' ' for _ in range(81)), "turn": 1, "last_move": 10, "won": 0, "winning_combination": 100, game: TicTacToe(), "won": 0})
        
        connect(None)
        return redirect("/room")

@app.route("/room", methods=["GET", "POST"])
def room():
    rooom()
    if request.method == "GET":
        for room in rooms:
            if room['code'] == session["code"]:
                break
        else:
            return redirect("/play")
        board = room['board']
        current_player = 'X' if room['turn'] == 1 else 'O'
        last_move = room['last_move']
        winner = "X WON!" if room['won'] == 1 else "O WON!" if room['won'] == 2 else "Tie" if room['won'] == 3 else None
        winning_combination = [room['winning_combination']//100, room['winning_combination']%100//10, room['winning_combination']%10]
        game = TicTacToe(list(board), current_player, last_move, winner=winner, winning_combination=winning_combination)
        room["game"] = game
        user_player = 'X' if session["user_id"] == room['player_one_id'] else 'O'
        return render_template("room.html", board=list(room['game'].board_alt), code=session["code"], user_player=user_player)
    return redirect("/play")

@app.route("/exit_game", methods=["GET", "POST"])
def exit_game():
    return redirect("/play")

@socketio.on("connect")
def connect(auth):
    if not session.get("code") or not session.get("user_id"):
        return
    for room in rooms:
        if room['code'] == session["code"]:
            user_player = 'X' if session["user_id"] == room['player_one_id'] else 'O'
            break
    try:
        join_room(session["code"] + user_player)
    except:
        pass
    #send({"board": board, "last_move": room['last_move'], "current_player": room['turn']}, to=session["code"])
    
    
@socketio.on("disconnect")
def disconnect():
    if not session.get("code") or not session.get("user_id"):
        return
    for room in rooms:
        if room['code'] == session["code"]:
            if not room.get("game"):
                return
            break
    else:
        return
    if session["user_id"] == room['player_one_id']:
        room['player_one_id'] = None
    else:
        room['player_two_id'] = None
    leave_room(session["code"])
    
@socketio.on("message")
def message(data):
    if not session.get("code") or not session.get("user_id"):
        return
    for room in rooms:
        if room['code'] == session["code"]:
            if not room.get("game"):
                return
            break
    else:
        return redirect("/play")
    game: TicTacToe = room["game"]
    other_player = 'O' if session["user_id"] == room['player_one_id'] else 'X'
    winning_combination = game.winning_combination
    send({"board": game.board_alt, "last_move": game.last_move, "current_player": game.current_player, "winner": game.winner, "winning_combination": winning_combination}, to=session["code"]+other_player)

@socketio.on("delete_room")
def delete_room(data):
    if not session.get("code") or not session.get("user_id"):
        return
    for room in rooms:
        if room['code'] == session["code"]:
            if not room.get("game"):
                return
            break
    else:
        return
    game: TicTacToe = room["game"]
    if game.winning_combination:
        winning_combination = int(''.join(map(str, game.winning_combination)))
    else:
        winning_combination = 100
    winner = 1 if game.winner == 'X WON!' else 2 if game.winner == 'O WON!' else 3 if game.winner == 'Tie' else 0

    if room["player_two_id"]:
        time_created_list = db.execute("SELECT time_created FROM rooms WHERE code=?", session["code"])
        if time_created_list:
            time_created = time_created_list[0]["time_created"]
            db.execute("INSERT INTO games (player_one_id, player_two_id, board, time_created, won, winning_combination) VALUES (?, ?, ?, ?, ?, ?)",
                room['player_one_id'], room['player_two_id'], ''.join(game.board), time_created, winner, winning_combination)
        db.execute("DELETE FROM rooms WHERE code=?", session["code"])

    del session["code"]
    del room

@app.route("/about")
def about():
    return render_template("about.html")

@login_required
@app.route("/games")
def games():
    return render_template("games.html")

if __name__ == "__main__":
    socketio.run(app, debug=True)