import os
from uuid import uuid4
from dotenv import load_dotenv
from langgraph.types import Command
import fire

load_dotenv()


class AIAgent:
    """AI agent class that calls the simple graph or the human in the loop graph"""

    def base(self):
        from src.workflow import initialize_graph, create_config

        graph = initialize_graph()
        unique_id = str(uuid4())
        config = create_config(unique_id)

        while True:
            user_input = input("User: ")
            if user_input.lower() in ["quit", "exit", "stop", "q"]:
                print("Goodbye!")
                break
            if not user_input:
                continue

            output = graph.invoke(
                {
                    "user_query": user_input,
                    "unique_id": unique_id,
                },
                config,
            )
            print(f"Plot explanation:\n{output["plot_summary"]}")
            print(f"Plot location: {output["plot_data"].plot_path}\n")

    def hitl(self):
        from src.workflow import create_config
        from src.workflow.hitl import initialize_graph

        graph = initialize_graph()
        unique_id = str(uuid4())
        config = create_config(unique_id)

        while True:
            user_input = input("User: ")
            if user_input.lower() in ["quit", "exit", "stop", "q"]:
                print("Goodbye!")
                break
            if not user_input:
                continue

            params = {
                "user_query": user_input,
                "unique_id": unique_id,
            }
            while True:
                response = graph.invoke(params, config)

                if "__interrupt__" in response:
                    interrupt_text = response["__interrupt__"][0].value
                    state = graph.get_state(config)
                    current_node = state.tasks[0].name

                    if current_node == "data_query":
                        if response.get("plot_summary") and response.get("plot_data"):
                            print(f"Plot explanation:\n{response.get("plot_summary")}")
                            print(
                                f"Plot location:\n{response["plot_data"].plot_path}\n"
                            )
                    print(interrupt_text)
                    params = Command(resume=input())
                else:
                    print("Ending...")
                    break


if __name__ == "__main__":
    if os.getenv("TEST_MODE", "False").lower() == "true":
        print("Test mode enabled!")
    fire.Fire(AIAgent)
