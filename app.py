from gpt_service import get_llm_response_stream
from langfuse.decorators import observe
from movie_functions import get_now_playing_movies, get_showtimes
from prompt import SYSTEM_PROMPT
from utils import parse_response, parse_now_playing_movies
from utils import logger

import chainlit as cl
import json

ERROR_MESSAGE = "I couldn't understand your request. Please try again."


def handle_external_function_call(function_name, args=None):
    if function_name == "get_now_playing_movies":
        movies = get_now_playing_movies()
        if "error" in movies:
            return {"error": "Failed to fetch now playing movies"}
        else:
            return {"content": parse_now_playing_movies(movies)}
    elif function_name == "get_showtimes":
        if args["title"] and args["zip_code"]:
            showtimes = get_showtimes(args["title"], args["zip_code"])
            if "error" in showtimes:
                return {"error": "Failed to fetch showtimes"}
            else:
                return {"content": showtimes}
    else:
        return {"error": "Function not found"}


@observe
@cl.on_chat_start
def on_chat_start():
    message_history = [{"role": "system", "content": SYSTEM_PROMPT}]
    cl.user_session.set("message_history", message_history)


@cl.on_message
@observe
async def on_message(message: cl.Message):
    logger.info(f"Received message: {message.content}")
    # Initialize the response
    response = cl.Message(content="")
    await response.send()

    # Get the message history
    message_history = cl.user_session.get("message_history", [])

    # Get the response from the LLM
    gpt_response = await get_llm_response_stream(
        {"role": "user", "content": message.content},
        message_history,
    )
    logger.info(f"Received response from LLM: {gpt_response}")
    parsed_response = parse_response(gpt_response)

    # Check if the response is a function call
    if "function_name" in parsed_response:
        # Log the function call
        logger.info(
            f"""Called function: {parsed_response['function_name']} with args: 
            {parsed_response.get('args', {})} because 
            {parsed_response['rationale']}"""
        )
        function_name = parsed_response["function_name"]
        args = parsed_response["args"] if "args" in parsed_response else None
        fn_response = handle_external_function_call(
            function_name=function_name, args=args
        )
        logger.info(f"Received response from function: {fn_response}")
        message_history.append(
            {"role": "system", "content": json.dumps(parsed_response)}
        )
        # Handle the response from the external function
        if "error" in fn_response:
            response.content = fn_response["error"]
        else:
            response.content = fn_response["content"]
    else:
        # Handle the response from the LLM
        if "error" in parsed_response:
            response.content = ERROR_MESSAGE
        else:
            response.content = parsed_response["content"]

    message_history.append({"role": "assistant", "content": response.content})
    # Add the entire conversation to the session context. This allows the model
    # to have message history available
    cl.user_session.set("message_history", message_history)
    # Send the response to the end-user
    await response.send()


if __name__ == "__main__":
    cl.main()
