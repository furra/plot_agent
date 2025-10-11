from uuid import uuid4
from workflow import initialize_graph, stream


if __name__ == "__main__":
    graph = initialize_graph()

    while True:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit", "stop", "q"]:
            print("Goodbye!")
            break
        results = stream(graph, user_input, str(uuid4()))
        output = list(results)
        breakpoint()
        for message in output[-1]["messages"]:
            message.pretty_print()
