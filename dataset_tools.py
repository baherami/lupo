import requests
import os
import argparse
from PIL import Image
import logging

SEARCH_URL = "https://api.bing.microsoft.com/v7.0/images/search"
NUMBER_OF_IMAGE_PER_PAGE = 50
MAX_NUMBER_OF_IMAGES = 250


class MessageLevel:
    INFO = "INFO"
    WARNING = "WARNING"


logger = logging.getLogger(__name__)


def print_status(message, target="", log_level="INFO", end_line="\n"):
    if target == "log":
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % log_level)
        logger.log(level=numeric_level, msg=message)
    else:
        print(log_level, message, end=end_line)


def api_call(request_headers, request_params):
    response = requests.get(SEARCH_URL, headers=request_headers, params=request_params)
    response.raise_for_status()
    return response.json()


def search(search_headers, search_params):
    results = api_call(search_headers, search_params)
    estimated_matches = min(results["totalEstimatedMatches"], MAX_NUMBER_OF_IMAGES)
    return results, estimated_matches


def retrieve_image(img_url, img_number):
    try:
        request_content = requests.get(img_url, timeout=30)
        start_index = img_url.rfind(".")
        end_index = img_url.rfind("&")
        if end_index == -1:
            end_index = None

        extension = img_url[start_index:end_index]
        image_path = os.path.sep.join([output_location, f"{str(img_number).zfill(8)}{extension}"])
        with open(image_path, "wb") as f:
            f.write(request_content.content)
    except Exception:
        print_status(f"skipping: {img_url}", log_level=MessageLevel.WARNING)
        return None
    return image_path


def pars_arguments():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-q", "--query", help="search query", required=True)
    arg_parser.add_argument("-o", "--output", help="output path", required=True)
    arg_parser.add_argument("-s", "--subscription", help="subscription key for azure", required=True)
    arg_parser.add_argument("-a", "--action", help="action to do", required=True)
    arguments = vars(arg_parser.parse_args())
    return arguments


def is_valid_image(image_path):
    if not image_path:
        return False
    try:
        img = Image.open(image_path)
        img.verify()
    except Exception:
        print_status(f"deleting: {image_path}", log_level=MessageLevel.WARNING)
        os.remove(image_path)
        return False
    return True


def get_images():
    headers = {"Ocp-Apim-Subscription-Key": subscription_key}
    params = {"q": search_term, "license": "public", "imageType": "photo", "offset": 0,
              "count": NUMBER_OF_IMAGE_PER_PAGE}
    search_results, total_estimated_matches = search(headers, params)
    print_status(f"{total_estimated_matches} total results for '{search_term}'")

    img_counter = 0
    for offset in range(0, total_estimated_matches, NUMBER_OF_IMAGE_PER_PAGE):
        end_of_page = offset + NUMBER_OF_IMAGE_PER_PAGE
        print_status(f"request for group {offset}-{end_of_page} of {total_estimated_matches}...")
        params["offset"] = offset
        page_results = api_call(headers, params)

        for value in page_results["value"]:
            request_url = value["contentUrl"]
            print_status(f'fetching: {request_url}')
            file_path = retrieve_image(request_url, img_counter)
            if not is_valid_image(file_path):
                continue
            img_counter += 1


if __name__ == "__main__":
    args = pars_arguments()
    search_term = args["query"]
    output_location = args["output"]
    subscription_key = args["subscription"]
    action = args["action"]

    if action == "get_images":
        get_images()
    else:
        raise NotImplementedError("Action not found")
