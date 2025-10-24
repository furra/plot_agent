import os

from dotenv import load_dotenv
from langgraph.types import Command
from uuid import uuid4

import streamlit as st

from workflow import create_config
from workflow_hitl import initialize_graph

load_dotenv()

google_api_key = os.environ["GOOGLE_API_KEY"]

if "conversation_id" not in st.session_state or st.button("Clear history"):
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
    st.session_state.data_locked = False
    st.session_state.graph = None

# Set the app title
st.title("Generate and interpret plots")

# Sidebar for API key input
with st.sidebar:
    if google_api_key is None:
        google_api_key = st.text_input("Enter your Google API Key", type="password")
        st.warning("Please enter your Google API key to use the agent.")

# Initialize resources only if API key is provided
# st.write(st.session_state)
if google_api_key and st.session_state.graph is None:
    with st.spinner("Initializing agent..."):
        st.session_state.graph = initialize_graph()
        st.success("Agent initialized successfully!", icon="🚀")


# Display chat history
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        if img := st.session_state.images.get(i):
            st.image(img["image"], caption=img["caption"])
        st.markdown(message["content"])

# Accept user input
prompt = st.chat_input("User input...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    if st.session_state.data_locked:
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
            response = st.session_state.graph.invoke(
                st.session_state.params,
                st.session_state.config,
            )

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
                    st.markdown(response["plot_summary"])
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
            st.session_state.data_locked = True
        else:
            st.session_state.data_locked = False
            first_message = st.session_state.messages[0]
            with st.chat_message("assistant"):
                st.markdown(first_message["content"])
            st.session_state.messages.append(first_message)

else:
    st.error("Please enter your Google API key in the sidebar to use the agent.")
