import os

from dotenv import load_dotenv
from uuid import uuid4

import streamlit as st

from workflow import create_config, initialize_graph

load_dotenv()

google_api_key = os.environ["GOOGLE_API_KEY"]

if "conversation_id" not in st.session_state:
    unique_id = str(uuid4())
    st.session_state.conversation_id = unique_id
    st.session_state.config = create_config(unique_id)

# Set the app title
st.title("Generate and interpret plots")

# Sidebar for API key input
with st.sidebar:
    if google_api_key is None:
        google_api_key = st.text_input("Enter your Google API Key", type="password")
        st.warning("Please enter your Google API key to use the agent.")

if st.button("Clear history"):
    st.session_state.messages = st.session_state.messages[:1]
    st.session_state.conversation_id = str(uuid4())


# Initialize resources only if API key is provided
if google_api_key:
    with st.spinner("Initializing agent..."):
        workflow = initialize_graph()
        st.success("Agent initialized successfully!", icon="🚀")

# Initialize message history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hello! I can generate and interpret plots from online shopping data!",
        }
    ]

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
prompt = st.chat_input("Your question...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)


# Generate answer if API key is provided
if google_api_key:
    if prompt:
        with st.spinner("Thinking..."):

            response = workflow.invoke(
                {"user_query": prompt, "unique_id": st.session_state.unique_id},
                st.session_state.config,
            )
        with st.chat_message("assistant"):
            st.image(
                response["plot_data"].plot_path,
                caption=response["plot_data"].plot_caption,
            )
            st.markdown(response["plot_summary"])
        st.session_state.messages.append(
            {"role": "assistant", "content": response["plot_summary"]}
        )
else:
    st.error("Please enter your Google API key in the sidebar to use the agent.")
