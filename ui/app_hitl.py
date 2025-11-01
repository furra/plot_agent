import logging
import json
import sys
from pathlib import Path
import os

from baml_py.errors import BamlClientError
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError
from langgraph.types import Command
from uuid import uuid4
import streamlit as st

load_dotenv()

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

google_api_key = os.environ.get("GOOGLE_API_KEY")

test_mode = os.environ.get("TEST_MODE")
if test_mode and test_mode.lower() == "true":
    st.write("Running on TEST mode!")

# Sidebar for API key input
with st.sidebar:
    if not google_api_key:
        st.sidebar.title("GOOGLE API KEY")
        google_api_key = st.text_input("Enter your Google API Key", type="password")
        os.environ["GOOGLE_API_KEY"] = google_api_key
        st.warning("Please enter your Google API key to use the agent.")

if not google_api_key:
    st.error("Please enter your Google API key in the sidebar to use the agent.")
    st.stop()
elif not st.session_state.get("valid_key"):
    # validate key first, just once
    try:
        test_llm = init_chat_model("gemini-2.5-flash", model_provider="google_genai")
        test_llm.invoke("Return the number `1`. No other output.")
    except ChatGoogleGenerativeAIError as e:
        logger.error(e, exc_info=True)
        if "400 API key not valid" in str(e):
            user_message = "API key not valid. Please pass a valid API key."
        else:
            user_message = "Something went wrong with the request."

        st.error(user_message)
        st.stop()

    st.session_state.valid_key = True

if (
    google_api_key
    and st.session_state.get("valid_key")
    and ("conversation_id" not in st.session_state or st.button("Clear history"))
):
    from src.workflow import create_config
    from src.workflow.hitl import initialize_graph

    unique_id = str(uuid4())
    st.session_state.conversation_id = unique_id
    st.session_state.config = create_config(unique_id)
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hello! I can generate and interpret plots from online shopping data!",
        }
    ]
    st.session_state.images = {}
    st.session_state.data_picked = False
    st.session_state.graph = None
    logger.info(f"Initializing state: {st.session_state}")

# Set the app title
st.title("Generate and interpret plots")

# Initialize resources only if API key is provided
if google_api_key and st.session_state.graph is None:
    with st.spinner("Initializing agent..."):
        st.session_state.graph = initialize_graph()
        st.success("Agent initialized successfully!", icon="🚀")


# Display chat history
if google_api_key:
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            if img := st.session_state.images.get(i):
                st.image(img["image"], caption=img["caption"])
            st.markdown(message["content"])

# Accept user input
prompt = st.chat_input("User input...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    if st.session_state.data_picked:
        st.session_state.params = Command(resume=prompt)
    else:
        st.session_state.params = {
            "user_query": prompt,
            "unique_id": st.session_state.conversation_id,
        }
    with st.chat_message("user"):
        st.markdown(prompt)


# Generate answer if API key is provided
if google_api_key and st.session_state.graph is not None:
    if prompt:
        with st.spinner("Thinking..."):
            try:
                response = st.session_state.graph.invoke(
                    st.session_state.params,
                    st.session_state.config,
                )
            except BamlClientError as e:
                logger.error(e, exc_info=True)
                try:
                    data = json.loads("{" + e.message.split("{", 1)[1])  # type: ignore
                    user_message = data["error"]["message"]
                except Exception as e:
                    user_message = "Something went wrong with the request."
                st.error(user_message)
                st.stop()
            except ChatGoogleGenerativeAIError as e:
                logger.error(e, exc_info=True)
                if "400 API key not valid" in str(e):
                    user_message = "API key not valid. Please pass a valid API key."
                else:
                    user_message = "Something went wrong with the request."
                st.error(user_message)
                st.stop()
            except Exception as e:
                logger.error(e, exc_info=True)
                user_message = "Something went wrong with the request."
                st.error(user_message)
                st.stop()

        if "__interrupt__" in response:
            interrupt_text = response["__interrupt__"][0].value.replace("\n", "  \n")
            state = st.session_state.graph.get_state(st.session_state.config)
            current_node = state.tasks[0].name

            if (
                current_node == "data_query"
                and response.get("plot_summary")
                and response.get("plot_data")
            ):
                with st.chat_message("assistant"):
                    st.image(
                        response["plot_data"].plot_path,
                        caption=response["plot_data"].plot_caption,
                    )
                    st.write(response["plot_summary"])
                    st.session_state.images[len(st.session_state.messages)] = {
                        "image": response["plot_data"].plot_path,
                        "caption": response["plot_data"].plot_caption,
                    }
                    st.session_state.messages.append(
                        {"role": "assistant", "content": response["plot_summary"]}
                    )
            with st.chat_message("assistant"):
                st.markdown(interrupt_text)
            st.session_state.messages.append(
                {"role": "assistant", "content": interrupt_text}
            )
            st.session_state.data_picked = True
        else:
            st.session_state.data_picked = False
            first_message = st.session_state.messages[0]
            with st.chat_message("assistant"):
                st.markdown(first_message["content"])
            st.session_state.messages.append(first_message)
