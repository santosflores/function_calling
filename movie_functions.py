import os
import requests
from serpapi import GoogleSearch
import os


def get_now_playing_movies():
    url = "https://api.themoviedb.org/3/movie/now_playing?language=en-US&page=1"
    headers = {"Authorization": f"Bearer {os.getenv('TMDB_API_ACCESS_TOKEN')}"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return {
            "error": True,
            "status_code": response.status_code,
            "message": response.reason,
        }

    data = response.json()
    movies = data.get("results", [])
    if not movies:
        return {
            "status_code": 40,
            "items": [],
            "number_of_items": 0,
        }

    return {
        "status_code": response.status_code,
        "items": movies,
        "number_of_items": len(movies),
    }


def get_showtimes(title, location):
    params = {
        "api_key": os.getenv("SERP_API_KEY"),
        "engine": "google",
        "q": f"showtimes for {title}",
        "location": location,
        "google_domain": "google.com",
        "gl": "us",
        "hl": "en",
    }

    search = GoogleSearch(params)
    results = search.get_dict()

    if "showtimes" not in results:
        return f"No showtimes found for {title} in {location}."

    showtimes = results["showtimes"][0]
    formatted_showtimes = f"Showtimes for {title} in {location}:\n\n"

    if showtimes["theaters"]:
        theater = showtimes["theaters"][0]
        theater_name = theater.get("name", "Unknown Theater")
        formatted_showtimes += f"**{theater_name}**\n"

        date = showtimes.get("day", "Unknown Date")
        formatted_showtimes += f"  {date}:\n"

        for showing in theater.get("showing", []):
            for time in showing.get("time", []):
                formatted_showtimes += f"    - {time}\n"

    formatted_showtimes += "\n"

    return formatted_showtimes


def buy_ticket(theater, movie, showtime):
    return f"Ticket purchased for {movie} at {theater} for {showtime}."


def get_reviews(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/reviews?language=en-US&page=1"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {os.getenv('TMDB_API_ACCESS_TOKEN')}",
    }
    response = requests.get(url, headers=headers)
    reviews_data = response.json()

    if "results" not in reviews_data or not reviews_data["results"]:
        return "No reviews found."

    formatted_reviews = ""
    for review in reviews_data["results"]:
        author = review.get("author", "N/A")
        rating = review.get("author_details", {}).get("rating", "N/A")
        content = review.get("content", "N/A")
        created_at = review.get("created_at", "N/A")
        url = review.get("url", "N/A")

        formatted_reviews += (
            f"**Author:** {author}\n"
            f"**Rating:** {rating}\n"
            f"**Content:** {content}\n"
            f"**Created At:** {created_at}\n"
            f"**URL:** {url}\n"
            "----------------------------------------\n"
        )

    return formatted_reviews
