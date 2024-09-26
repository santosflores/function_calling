from gpt_service import get_llm_response_stream
from langfuse.decorators import observe
from movie_functions import get_now_playing_movies, get_showtimes, pick_random_movie
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
    elif function_name == "pick_random_movie":
        if args["movies"]:
            random_movie = pick_random_movie(args["movies"])
            if "error" in random_movie:
                return {"error": "Failed to pick a random movie"}
            else:
                return {"content": random_movie}
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
        logger.info("Parsed response is a function call")
        task_queue = parsed_response.get("task_queue", [])
        task_queue.insert(
            0,
            {
                "function_name": parsed_response.get("function_name", "N/A"),
                "rationale": parsed_response.get("rationale", "N/A"),
                "args": parsed_response.get("args", {}),
            },
        )
        print(f"Task queue: {task_queue}")
        for task in task_queue:
            # Generate the request for the task
            content = f"""Make a call to function {task.get("function_name", "N/A")} 
            because {task.get("rationale", "N/A")}"""
            task_request = await get_llm_response_stream(
                {"role": "system", "content": content},
                message_history,
            )
            logger.info(f"Created task request: {task_request}")
            # Format the suggested task by the LLM into a JSON object
            parsed_task_response = parse_response(task_request)
            logger.info(f"Parsed task response: {parsed_task_response}")
            # Extract the function name, rationale, and args from the parsed task response
            function_name = parsed_task_response.get("function_name", "N/A")
            rationale = parsed_task_response.get("rationale", "N/A")
            args = parsed_task_response.get("args", {})
            # Call the external function with the parsed arguments
            function_response = handle_external_function_call(
                function_name=function_name,
                args=args,
            )
            # Log the function call and its response
            logger.info(
                f"""Called function: {function_name} with args: {args} because 
                {rationale} with response: {function_response}"""
            )
            # Update the system with the function request and response to the message history
            system_message = {
                "debug_info":{
                    "function_request": parsed_task_response,
                    "function_response": function_response,
                }
            }
            message_history.append(
                {"role": "system", "content": json.dumps(system_message)}
            )
        # Handle the response from the external function
        if "error" in function_response:
            response.content = function_response["error"]
        else:
            response.content = function_response["content"]
    else:
        # Handle the response from the LLM
        if "error" in parsed_response:
            logger.info(f"Error in parsed response: {parsed_response['error']}")
            response.content = ERROR_MESSAGE
        else:
            logger.info(f"Parsed response is content type: {parsed_response}")
            response.content = parsed_response["content"]

    message_history.append({"role": "assistant", "content": response.content})
    # Add the entire conversation to the session context. This allows the model
    # to have message history available
    cl.user_session.set("message_history", message_history)
    # Send the response to the end-user
    await response.send()


if __name__ == "__main__":
    cl.main()
