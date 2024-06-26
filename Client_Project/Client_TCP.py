import socket
import sys

# Client configuration
HOST = '127.0.0.1'
PORT = 5678


def recv_message_and_parse(client_socket):
    try:
        full_msg = client_socket.recv(1024).decode()
        if not full_msg:
            return None, None
        parts = full_msg.split('|', 2)
        return parts[0], parts[2]
    except:
        return None, None


def build_and_send_message(client_socket, code, msg):
    full_msg = f"{code}|{len(msg):04d}|{msg}"
    client_socket.send(full_msg.encode())


def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))

    logged_in = False

    while True:
        if not logged_in:
            action = input("Choose action (login/register): ").strip().lower()
            if action == 'login':
                username = input("Enter username: ").strip()
                password = input("Enter password: ").strip()
                build_and_send_message(client_socket, "LOGIN", f"{username}# {password}")
                cmd, data = recv_message_and_parse(client_socket)
                if cmd == "LOGIN_OK":
                    print("Login successful")
                    logged_in = True
                elif cmd == "ERROR":
                    print(f"Error: {data}")
            elif action == 'register':
                username = input("Enter username: ").strip()
                password = input("Enter password: ").strip()
                build_and_send_message(client_socket, "REGISTER", f"{username}# {password}")
                cmd, data = recv_message_and_parse(client_socket)
                if cmd == "REGISTER_OK":
                    print("Registration successful, please login")
                elif cmd == "ERROR":
                    print(f"Error: {data}")
            else:
                print("Unknown command")
        else:
            action = input("Choose action (p - play, s - see my score, t - see top scores, q - quit): ").strip().lower()
            if action == 'p':
                build_and_send_message(client_socket, "PLAY", "")
                cmd, data = recv_message_and_parse(client_socket)
                if cmd == "QUESTION":
                    print(f"Question: {data}")
                    question, correct_answer, *options = data.split("#")
                    options.append(correct_answer)
                    options.sort()
                    print(f"Options: {', '.join(options)}")
                    answer = input("Your answer: ").strip()
                    build_and_send_message(client_socket, "ANSWER", f"{question}#{answer}")
                    cmd, data = recv_message_and_parse(client_socket)
                    if cmd == "ANSWER":
                        print(data)
                elif cmd == "ERROR":
                    print(f"Error: {data}")
            elif action == 's':
                build_and_send_message(client_socket, "SCORE", "")
                cmd, data = recv_message_and_parse(client_socket)
                if cmd == "SCORE":
                    print(f"Your score: {data}")
                elif cmd == "ERROR":
                    print(f"Error: {data}")
            elif action == 't':
                build_and_send_message(client_socket, "TOPSCORES", "")
                cmd, data = recv_message_and_parse(client_socket)
                if cmd == "TOPSCORES":
                    print("Top scores:")
                    print(data)
                elif cmd == "ERROR":
                    print(f"Error: {data}")
            elif action == 'q':
                build_and_send_message(client_socket, "LOGOUT", "")
                print("Goodbye!")
                main()
            else:
                print("Unknown command")

    client_socket.close()


if __name__ == "__main__":
    main()
