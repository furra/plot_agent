from uuid import uuid4
from langgraph.types import Command
import fire


class AIAgent:
    """AI agent class that calls the simple graph or the human in the loop graph"""

    def agent(self):
        from workflow import initialize_graph, stream

        graph = initialize_graph()

        while True:
            user_input = input("User: ")
            if user_input.lower() in ["quit", "exit", "stop", "q"]:
                print("Goodbye!")
                break
            if not user_input:
                continue
            # use invoke instead
            results = stream(graph, user_input, str(uuid4()))
            output = list(results)
            output = output[-1]
            print(f"Plot explanation:\n{output["plot_summary"]}")
            print(f"Plot location: {output["plot_data"].plot_path}")

    def hitl(self):
        from workflow import create_config
        from workflow_hitl import initialize_graph

        graph = initialize_graph()
        thread_id = str(uuid4())
        config = create_config(thread_id)

        while True:
            user_input = input("User: ")
            if user_input.lower() in ["quit", "exit", "stop", "q"]:
                print("Goodbye!")
                break
            if not user_input:
                continue

            params = {
                "user_query": user_input,
                "unique_id": thread_id,
            }
            while True:
                response = graph.invoke(params, config)

                if "__interrupt__" in response:
                    interrupt_text = response["__interrupt__"][0].value
                    state = graph.get_state(config)
                    current_node = state.tasks[0].name

                    if (
                        "confirm" in current_node
                    ):  # "user_confirm_sql", "user_confirm_data"
                        print(interrupt_text)
                        should_continue = input().lower().startswith("y")
                        params = Command(resume=should_continue)
                        if not should_continue:
                            graph.invoke(params, config=config)
                            break
                    elif current_node == "data_query":
                        if response.get("plot_summary") and response.get("plot_data"):
                            print(f"Plot explanation:\n{response.get("plot_summary")}")
                            print(
                                f"Plot location:\n{response["plot_data"].plot_path}\n"
                            )

                        print(interrupt_text)
                        data_query = input()
                        params = Command(resume=data_query)
                    else:
                        print(f"Unknown node: {current_node}")
                        break
                else:
                    print("Ending...")
                    break


if __name__ == "__main__":
    fire.Fire(AIAgent)
