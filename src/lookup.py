# Copyright (c) 2025 Mike Chambers
# https://github.com/mikechambers/echo
#
# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

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
from playsound import playsound
import traceback
import tempfile
from PIL import Image
from enum import Enum
import cv2
import pytesseract
import re

##todo
# dont convert to jpg if file is jpg


VERSION = "0.85.1"
API_KEY_ENV_NAME = "DESTINY_API_KEY"
OPENAI_API_KEY_ENV_NAME = "OPENAI_API_KEY"
LAUNCH_WAV = "launched.wav"

verbose = False
play_sound_on_launch = True

screenshot_dir = None
allowed_extensions = ["png", "jpg"]

optimize_screenshot = True
fallback = False
api_key = None


class Engine(Enum):
    OPENCV = 1
    OPENAI = 2

engine = Engine.OPENCV


class ImageAnalysis(BaseModel):
    id_str: str
    confidence: float

def main():
    event_handler = FileSystemEventHandler()
    event_handler.on_created = on_created
    observer = Observer()
    observer.schedule(event_handler, screenshot_dir, recursive=False)
    observer.start()

    print(f"Watching folder '{screenshot_dir}' for {allowed_extensions} ...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def encode_image(image_path:str):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def retrieve_member(bungie_id:BungieId) -> Member:
    destiny = Destiny(api_key, verbose)

    member = destiny.retrieve_member(bungie_id)

    return member


def play_sound(file_path: str):
    try:
        playsound(file_path)
    except Exception as e:
        print(f"Warning: Failed to play sound {file_path}. Error: {e}. Ignoring")

def launch_trials_report(member:Member):

    if play_sound_on_launch:
        play_sound(LAUNCH_WAV)

    url = f"https://destinytrialsreport.com/report/{member.platform_id}/{member.membership_id}"
    webbrowser.open(url)


def _parse_bungie_id(value: str) -> BungieId:
    bungie_id = BungieId.from_string(value)
    return bungie_id


def parse_bungie_id_from_screenshot(path:str, engine:Engine) -> str:
    if engine == Engine.OPENAI:
        return _open_ai_parse(path)
    elif engine == Engine.OPENCV:
        return _open_cv_parse(path)
    

def _open_cv_parse(path: str) -> str:
    """
    Loads an image at `path`, extracts text via OCR, and returns 
    the first Bungie ID of the form [A-Za-z0-9]+#[0-9]{4}.
    
    Returns:
        str: The first matching Bungie ID found, or an empty string if none.
    """
    # Load the image
    image = cv2.imread(path)
    if image is None:
        print(f"Error: Could not load image from path {path}")
        return ""

    # Convert the image to grayscale (often improves OCR accuracy)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Perform OCR using pytesseract
    text = pytesseract.image_to_string(gray)

    # Regex to find the first occurrence of a Bungie ID (e.g. "mesh#1234")
    pattern = r'[A-Za-z0-9]+#[0-9]{4}'
    match = re.search(pattern, text)
    
    if match:
        return match.group(0)
    else:
        return ""


def _open_ai_parse(path:str) -> str:

    base64_image = encode_image(path)

    client = OpenAI()

    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an assistant that analyzes screenshots from Destiny 2 that shows player information to identify the bungie id displayed in the form of NAME#CODE (for example FOO#1234)"
                    "You must always return JSON strictly matching this schema: "
                    "id_str: The bungie id string found in the screenshot."
                    "confidence: a floating-point score between 0 and 1."
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Find the bungie id in the for of NAME#CODE (i.e. FOO#1234) in this image."},
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
    structured_dict = parsed_result.model_dump()

    # Example: print out as a JSON-like string
    print("Structured response:")
    print(structured_dict)

    id_str = structured_dict["id_str"]

    return id_str


def convert_png_to_jpg(png_path: str) -> str:
    """
    Converts a PNG image to a JPG, saves it in a temporary directory, and returns the new file path.

    Args:
        png_path (str): The path to the original PNG file.

    Returns:
        str: The path to the converted JPG file.
    """
    # Ensure the file exists
    if not os.path.isfile(png_path):
        raise FileNotFoundError(f"File not found: {png_path}")

    # Open the PNG image
    with Image.open(png_path) as img:
        # Convert image to RGB (to remove transparency, if any)
        img = img.convert("RGB")

        # Create a temporary file for the JPG
        temp_dir = tempfile.gettempdir()  # Get system temp directory
        jpg_filename = os.path.splitext(os.path.basename(png_path))[0] + ".jpg"
        jpg_path = os.path.join(temp_dir, jpg_filename)

        # Save as JPG
        img.save(jpg_path, "JPEG", quality=75)

    return jpg_path  # Return the path to the new JPG


def parse_and_retrieve_member(path:str, engine:Engine) -> Member:
    try:
        id_str = parse_bungie_id_from_screenshot(path, engine)
    except Exception as e:
        print(f"Error extracting bungie id from screenshot")

        if verbose:
            traceback.print_exc()

        return

    if verbose:
        print(f"Found bungie id from screenshot : {id_str}")

    bungie_id = _parse_bungie_id(id_str)

    if not bungie_id.is_valid:
        print(f"Could not parse Bungie Id : {bungie_id}. Ignoring")
        return

    try:
        member = retrieve_member(bungie_id)
    except Exception as e:
        print("Error retrieving member from Destiny API")
        
        if verbose:
            traceback.print_exc()
        return
    
    if not member:
        print(f"Could not find member for {bungie_id} using {engine}. This is probably because the bungie id was read incorrectly from the screenshot.")
        return
    
    return member


def on_created(event):
    if not event.is_directory:
        # Check if file matches one of our allowed extensions
        lower_path = event.src_path.lower()
        if not any(lower_path.endswith(ext) for ext in allowed_extensions):
            return
        
        if verbose:
            print(f"New image detected: {event.src_path}")

        time.sleep(1.0)

        screenshot_path = event.src_path

        if optimize_screenshot:
            screenshot_path = convert_png_to_jpg(event.src_path)
            if verbose:
                print(f"Using jpg : {screenshot_path}")

        member = parse_and_retrieve_member(screenshot_path, engine)

        if not member and fallback:


            e = None
            if engine == Engine.OPENAI:
                e = Engine.OPENCV
            else:
                e = Engine.OPENAI

            if verbose:
                print(f"Primary engine ({engine}) failed. Falling back to secondary engine ({e}).")

            member = parse_and_retrieve_member(screenshot_path, e)

        if optimize_screenshot and os.path.exists(screenshot_path):
            os.remove(screenshot_path)
            if verbose:
                print(f"Temporary file deleted: {screenshot_path}")


        if not member:
            return


        launch_trials_report(member)
            
def _get_arg_from_env_or_error(env_var):
    if env_var in os.environ:
        return os.environ[env_var]
    else:
        print(f"Error: {env_var} is required to be set as an environment variable.", file=sys.stderr)
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

    parser.add_argument(
        "--screenshot-dir",
        type=str,
        required=True,
        help="Path to the directory where screenshots are stored"
    )

    parser.add_argument(
        "--fallback",
        action="store_true",
        help="Enable fallback mode (default: disabled)."
    )

    """"
    parser.add_argument(
        "--optimize-image",
        action="store_false",
        help="Disable image optimization (default: enabled)."
    )
    """

    valid_choices = [e.name for e in Engine]  # e.g. ["OPENCV", "OPENAI"]
    parser.add_argument(
        "--engine",
        type=str.upper,             # Convert user input to uppercase
        choices=valid_choices,      # Must match these after .upper()
        default=Engine.OPENCV.name, # Default is "OPENCV"
        help="Specify which engine to use (case-insensitive). Choices: OPENCV, OPENAI."
    )

    args = parser.parse_args()

    fallback = args.fallback
    engine = Engine[args.engine]

    #check destiny api key is set as an environment variable
    api_key = _get_arg_from_env_or_error(API_KEY_ENV_NAME)

    if engine == Engine.OPENAI or fallback:
        #check openai key is set as an environment variable
        _get_arg_from_env_or_error(OPENAI_API_KEY_ENV_NAME)

    screenshot_dir = args.screenshot_dir

    if not os.path.isdir(args.screenshot_dir):
        print(f"Error: {screenshot_dir} is not a valid directory.")
        sys.exit(1)

    verbose = args.verbose
    #optimize_screenshot = args.optimize_image
    #optimize_screenshot = engine == Engine.OPENAI
    optimize_screenshot = True

    

    try:
        main()
    except Exception as e:
        print(f"An error occurred. Aborting : {e}")
        traceback.print_exc()
        sys.exit(1)
