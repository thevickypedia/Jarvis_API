import asyncio
import logging

import speech_recognition
import yaml

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

RECOGNIZER = speech_recognition.Recognizer()
ERROR_TUPLE = (
    speech_recognition.UnknownValueError,
    speech_recognition.RequestError,
    speech_recognition.WaitTimeoutError,
    TimeoutError,
    ConnectionError,
)

defaults = dict(
    energy_threshold=RECOGNIZER.energy_threshold,
    dynamic_energy_threshold=RECOGNIZER.dynamic_energy_threshold,
    pause_threshold=RECOGNIZER.pause_threshold,
    phrase_threshold=RECOGNIZER.phrase_threshold,
)

RECOGNIZER.energy_threshold = 1100
RECOGNIZER.pause_threshold = 1
RECOGNIZER.phrase_threshold = 0.1
RECOGNIZER.dynamic_energy_threshold = False
RECOGNIZER.non_speaking_duration = 1

changed = dict(
    energy_threshold=RECOGNIZER.energy_threshold,
    dynamic_energy_threshold=RECOGNIZER.dynamic_energy_threshold,
    pause_threshold=RECOGNIZER.pause_threshold,
    phrase_threshold=RECOGNIZER.phrase_threshold,
)


async def save_for_reference():
    """Saves the original config and new config in a yaml file."""
    with open("speech_recognition_values.yaml", "w") as file:
        yaml.dump(data={"defaults": defaults, "modified": changed}, stream=file)


async def main():
    """Initiates yaml dump in an asynchronous call and initiates listener in a never ending loop."""
    asyncio.create_task(save_for_reference())
    with speech_recognition.Microphone() as source:
        while True:
            try:
                logger.info("Listening..")
                audio = RECOGNIZER.listen(source)
                logger.info("Recognizing..")
                recognized = RECOGNIZER.recognize_google(
                    audio_data=audio
                )  # Requires stable internet connection
                # recognized = RECOGNIZER.recognize_sphinx(audio_data=audio)  # Requires pocketsphinx module
                if "stop" in recognized.lower().split():
                    break
            except ERROR_TUPLE:
                continue


if __name__ == "__main__":
    asyncio.run(main())
