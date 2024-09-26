import json
import re
import logging

# Configure the logger
logger = logging.getLogger(__name__)

def has_function_call(response: str) -> bool:
    pattern = r'"function_name"\s*:'
    return bool(re.search(pattern, response))


def parse_response(response):
    if has_function_call(response):
        try:
            response_json = json.loads(response)
            return response_json
        except json.JSONDecodeError:
            return {"error": "Invalid JSON response"}
    return {"content": response}


def parse_now_playing_movies(movies):
    if movies["status_code"] == 404:
        return "No movies are currently playing."
    else:
        response = ""
        for movie in movies["items"]:
            title = movie.get("title", "N/A")
            movie_id = movie.get("id", "N/A")
            release_date = movie.get("release_date", "N/A")
            overview = movie.get("overview", "N/A")
            response += (
                f"**Title:** {title}\n"
                f"**Movie ID:** {movie_id}\n"
                f"**Release Date:** {release_date}\n"
                f"**Overview:** {overview}\n\n"
            )
        return response

