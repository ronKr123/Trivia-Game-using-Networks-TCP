import socket
import select
import requests
import html

# Server configuration
HOST = '127.0.0.1'
PORT = 5678

# Global variables
users = {
    "user1": {"password": "pass1", "score": 0, "questions_asked": []},
    "user2": {"password": "pass2", "score": 0, "questions_asked": []}
}

logged_users = {}
messages_to_send = []


def fetch_questions():
    url = 'https://opentdb.com/api.php?amount=50&difficulty=easy&type=multiple'
    response = requests.get(url)
    data = response.json()
    questions = []
    for item in data['results']:
        question = html.unescape(item['question'])
        correct_answer = html.unescape(item['correct_answer'])
        incorrect_answers = [html.unescape(ans) for ans in item['incorrect_answers']]
        questions.append({
            'question': question,
            'correct_answer': correct_answer,
            'incorrect_answers': incorrect_answers
        })
    return questions


questions = fetch_questions()


def setup_socket():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"Server started, listening on IP address {HOST}:{PORT}")
    return server_socket


def send_error(client_socket, error_msg):
    build_and_send_message(client_socket, "ERROR", error_msg)


def build_and_send_message(client_socket, code, msg):
    global messages_to_send
    full_msg = f"{code}|{len(msg):04d}|{msg}"
    messages_to_send.append((client_socket, full_msg))


def recv_message_and_parse(client_socket):
    try:
        full_msg = client_socket.recv(1024).decode()
        if not full_msg:
            return None, None
        parts = full_msg.split('|', 2)
        return parts[0], parts[2]
    except:
        return None, None


def handle_login_message(client_socket, data):
    try:
        username, password = data.split('#')
        if username in users and users[username]['password'] == password:
            logged_users[client_socket.getpeername()] = username
            build_and_send_message(client_socket, "LOGIN_OK", "")
        else:
            send_error(client_socket, "Username or password is incorrect")
    except:
        send_error(client_socket, "Invalid login data")


def handle_register_message(client_socket, data):
    try:
        username, password = data.split('#')
        if username in users:
            send_error(client_socket, "Username already exists")
        else:
            users[username] = {"password": password, "score": 0, "questions_asked": []}
            build_and_send_message(client_socket, "REGISTER_OK", "")
    except:
        send_error(client_socket, "Invalid registration data")


def handle_play_message(client_socket):
    username = logged_users.get(client_socket.getpeername())
    if not username:
        send_error(client_socket, "Not logged in")
        return

    user = users[username]
    available_questions = [q for q in questions if q['question'] not in user['questions_asked']]

    if not available_questions:
        build_and_send_message(client_socket, "PLAY", "No more questions available")
        return

    question = available_questions[0]
    user['questions_asked'].append(question['question'])
    build_and_send_message(client_socket, "QUESTION",
                           f"{question['question']}#{question['correct_answer']}#{'|'.join(question['incorrect_answers'])}")


def handle_answer_message(client_socket, data):
    username = logged_users.get(client_socket.getpeername())
    if not username:
        send_error(client_socket, "Not logged in")
        return

    user = users[username]
    question, answer = data.split('#')

    for q in questions:
        if q['question'] == question:
            if q['correct_answer'] == answer:
                user['score'] += 1
                build_and_send_message(client_socket, "ANSWER", "Correct")
            else:
                build_and_send_message(client_socket, "ANSWER", "Incorrect")
            return

    send_error(client_socket, "Question not found")


def handle_score_message(client_socket):
    username = logged_users.get(client_socket.getpeername())
    if not username:
        send_error(client_socket, "Not logged in")
        return

    score = users[username]['score']
    build_and_send_message(client_socket, "SCORE", str(score))


def handle_top_scores_message(client_socket):
    top_scores = sorted(users.items(), key=lambda x: x[1]['score'], reverse=True)[:3]
    top_scores_msg = "\n".join([f"{user[0]}: {user[1]['score']}" for user in top_scores])
    build_and_send_message(client_socket, "TOPSCORES", top_scores_msg)


def handle_logout_message(client_socket):
    if client_socket.getpeername() in logged_users:
        del logged_users[client_socket.getpeername()]
    client_socket.close()


def handle_client_message(client_socket, cmd, data):
    if cmd == "LOGIN":
        handle_login_message(client_socket, data)
    elif cmd == "REGISTER":
        handle_register_message(client_socket, data)
    elif cmd == "PLAY":
        handle_play_message(client_socket)
    elif cmd == "ANSWER":
        handle_answer_message(client_socket, data)
    elif cmd == "SCORE":
        handle_score_message(client_socket)
    elif cmd == "TOPSCORES":
        handle_top_scores_message(client_socket)
    elif cmd == "LOGOUT":
        handle_logout_message(client_socket)
    else:
        send_error(client_socket, "Unknown command")


def main():
    server_socket = setup_socket()
    client_sockets = []
    global messages_to_send

    while True:
        read_list, write_list, error_list = select.select([server_socket] + client_sockets, client_sockets, [])
        for notified_socket in read_list:
            if notified_socket == server_socket:
                client_socket, client_address = server_socket.accept()
                print(f"New connection from {client_address}")
                client_sockets.append(client_socket)
            else:
                cmd, data = recv_message_and_parse(notified_socket)
                if cmd is None:
                    handle_logout_message(notified_socket)
                    client_sockets.remove(notified_socket)
                else:
                    handle_client_message(notified_socket, cmd, data)

        for message in messages_to_send:
            client_socket, msg = message
            if client_socket in write_list:
                client_socket.send(msg.encode())
                messages_to_send.remove(message)


if __name__ == "__main__":
    main()
