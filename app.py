from gpt_service import get_llm_response_stream
from langfuse.decorators import observe
from movie_functions import get_now_playing_movies
from prompt import SYSTEM_PROMPT
from utils import parse_response, parse_now_playing_movies

import chainlit as cl
import json


@observe
@cl.on_chat_start
def on_chat_start():
    message_history = [{"role": "system", "content": SYSTEM_PROMPT}]
    cl.user_session.set("message_history", message_history)


@cl.on_message
@observe
async def on_message(message: cl.Message):
    response = cl.Message(content="")
    await response.send()
    message_history = cl.user_session.get("message_history", [])
    gpt_response = await get_llm_response_stream(
        {"role": "user", "content": message.content},
        message_history,
    )
    parsed_response = parse_response(gpt_response)

    if "function_name" in parsed_response:
        function_name = parsed_response["function_name"]
        rationale = parsed_response["rationale"]
        if function_name == "get_now_playing_movies":
            message_history.append(
                {"role": "system", "content": json.dumps(parsed_response)}
            )
            playing_movies = get_now_playing_movies()
            if "error" in playing_movies:
                response.content = (
                    "I couldn't understand your request. Please try again."
                )
            else:
                response.content = parse_now_playing_movies(playing_movies)
        else:
            print(f"Function {function_name} not found")
    else:
        if "error" in parsed_response:
            response.content = "I couldn't understand your request. Please try again."
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
