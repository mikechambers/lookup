import argparse
import sys
import time
import os
import base64
from pydantic import BaseModel
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from openai import OpenAI
from modules.destiny import Destiny
from modules.member import BungieId, Member
import webbrowser

VERSION = "0.85.1"
API_KEY_ENV_NAME = "DESTINY_API_KEY"
OPENAI_API_KEY_ENV_NAME = "OPENAI_API_KEY"

verbose = False

folder_to_watch = "/Users/mesh/tmp/lookup"
allowed_extensions = ["png", "jpg"]

client = OpenAI()

# 1) Define a Pydantic model describing the JSON structure you need from the model.
class ImageAnalysis(BaseModel):
    description: str
    confidence: float

def main():
    event_handler = FileSystemEventHandler()
    event_handler.on_created = on_created
    observer = Observer()
    observer.schedule(event_handler, folder_to_watch, recursive=False)
    observer.start()

    print(f"Watching folder '{folder_to_watch}' for {allowed_extensions} ...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def encode_image(image_path:str):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def retrieve_member(bungie_id:BungieId):
    global verbose, api_key
    destiny = Destiny(api_key, verbose)

    #bungie_id = _parse_bungie_id(bungie_id)
    member = destiny.retrieve_member(bungie_id)

    return member

def launch_trials_report(member:Member):
    url = f"https://destinytrialsreport.com/report/{member.platform_id}/{member.membership_id}"
    webbrowser.open(url)


def _parse_bungie_id(value: str) -> BungieId:
    """Parses and validates the Bungie ID, returning a BungieId object"""
    bungie_id = BungieId.from_string(value)
    if not bungie_id.is_valid:
        raise argparse.ArgumentTypeError(
            "Invalid Bungie ID format. Expected format: NAME#1234 (e.g., Guardian#1234)"
        )
    return bungie_id

def parse_bungie_id_from_screenshot(path:str):
    global verbose

    base64_image = encode_image(path)

    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an assistant that analyzes screenshots from Destiny 2 that shows player information to identify the bungie id displayed in the form of NAME#CODE (for example mesh#3230)"
                    "You must always return JSON strictly matching this schema: "
                    "id_str: The bungie id string found in the screenshot."
                    "confidence: a floating-point score between 0 and 1."
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Find the bungie id in the for of NAME#CODE (i.e. mesh#3230) in this image."},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ],
            },
        ],
        # Tell the model what valid output format you need
        response_format=ImageAnalysis,
    )

    # 3) Retrieve the structured object from the model
    parsed_result = response.choices[0].message.parsed
    structured_dict = parsed_result.dict()

    # Example: print out as a JSON-like string
    print("Structured response:")
    print(structured_dict)

    id_str = structured_dict.description

    return id_str


def on_created(event):
    global verbose
    if not event.is_directory:
        # Check if file matches one of our allowed extensions
        lower_path = event.src_path.lower()
        if any(lower_path.endswith(ext) for ext in allowed_extensions):
            
            if verbose:
                print(f"New image detected: {event.src_path}")

            try:
                id_str = parse_bungie_id_from_screenshot(event.src_path)
            except Exception as e:
                print(f"Error calling open ai AIP")
                return

            if verbose:
                print(f"Found bungie id from screenshot : {id_str}")

            try:
                bungie_id = _parse_bungie_id(id_str)
            except Exception as e:
                print(f"Error parsing bungie_id : {id_str}")
                return

            if not bungie_id.is_valid:
                print(f"Could not parse Bungie Id : {bungie_id}. Ignoring")
                return

            try:
                member = retrieve_member(bungie_id)
            except Exception as e:
                print("Error retrieving member from Destiny API")
                import traceback
                traceback.print_exc()
                return

            launch_trials_report(member)
            
def _get_arg_from_env_or_error(env_var, arg_value, arg_name):
    """Return argument value, fallback to environment variable, else throw an error."""
    if arg_value is not None:
        return arg_value
    elif env_var in os.environ:
        return os.environ[env_var]
    else:
        print(f"Error: {arg_name} is required to be set as an environment variable {env_var}.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse bungie ids from screenshots and lookup on destinytrialsreport.com"
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {VERSION}',
        help="Display the version")

    parser.add_argument(
        '--verbose',
        dest='verbose', 
        action='store_true', 
        help='display additional information as script runs'
    )

    args = parser.parse_args()

    #check destiny api key is set as an environment variable
    api_key = _get_arg_from_env_or_error(API_KEY_ENV_NAME)

    #check openai key is set as an environment variable
    _get_arg_from_env_or_error(OPENAI_API_KEY_ENV_NAME)

    verbose = args.verbose

    try:
        main()
    except Exception as e:
        print(f"An error occurred. Aborting : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
