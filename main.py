from pprint import pprint
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
        final_output = output[-1]
        # final_output["plot_data"].plot_path
