"""This is a space for configuration required by the API module.

>>> Config

"""
import os
import platform
import warnings
from multiprocessing import current_process
from typing import Callable, List

import pvporcupine
from pydantic import BaseConfig, PositiveInt
from pyttsx3.voice import Voice

from jarvis_ui.executables.api_handler import make_request
from jarvis_ui.modules.exceptions import InvalidEnvVars
from jarvis_ui.modules.logger import logger
from jarvis_ui.modules.models import audio_driver, env, fileio, settings

add_ss_extn: Callable = lambda filepath: os.path.splitext(filepath)[0] + "_ss" + os.path.splitext(filepath)[1]


def swapper() -> None:
    """Swaps any request URL with the public URL if returned by Jarvis.

    Notes:
        Avoid making calls via load balancers or reverse proxy (if one is in place) such as CloudFront or Nginx.
    """
    if (public_url := make_request(path='offline-communicator',
                                   data={'command': 'ngrok public url'})) and public_url.get('detail'):
        if public_url['detail'][-1] != "/":
            public_url['detail'] += "/"
        if public_url['detail'] == env.request_url:
            return
        logger.info("Switching %s to %s", env.request_url, public_url['detail'])
        env.request_url = public_url['detail']


class Config(BaseConfig):
    """Gets keywords during start up. Runs custom validations on env-vars.

    >>> Config

    Raises:
        InvalidEnvVars:
        If the voice name is not present for the OperatingSystem.
    """

    if not env.recognizer_settings and not env.voice_phrase_limit:
        env.recognizer_settings = env.recognizer_settings_default  # Default override when phrase limit is not available

    if env.request_url[-1] != "/":
        env.request_url += "/"

    swapper()

    if isinstance(env.sensitivity, float) or isinstance(env.sensitivity, PositiveInt):
        env.sensitivity = [env.sensitivity] * len(env.wake_words)
    if keywords := make_request(path='keywords', method='GET'):
        logger.info("keywords have been loaded")

    if keywords:
        keywords = sum([v for _, v in keywords.items()], [])

    if env.speech_timeout and env.native_audio:
        warnings.warn(
            "Both `speech-synthesis` and `native-audio` cannot be enabled simultaneously.\n"
            "Speech synthesis uses third-party tts service where as `native_audio` preserves the audio from server.\n"
            "Disabling speech synthesis!!"
        )
        env.speech_timeout = 0

    if settings.operating_system != "Darwin" and not env.native_audio:
        env.speech_timeout = 10

    if env.speech_timeout and not env.native_audio:
        fileio.failed = add_ss_extn(fileio.failed)
        fileio.restart = add_ss_extn(fileio.restart)
        fileio.shutdown = add_ss_extn(fileio.shutdown)
        fileio.unprocessable = add_ss_extn(fileio.unprocessable)
        fileio.connection_restart = add_ss_extn(fileio.connection_restart)

    if settings.legacy:
        pvporcupine.KEYWORD_PATHS = {}
        pvporcupine.MODEL_PATH = os.path.join(os.path.dirname(pvporcupine.__file__),
                                              'lib/common/porcupine_params.pv')
        pvporcupine.LIBRARY_PATH = os.path.join(os.path.dirname(pvporcupine.__file__),
                                                f'lib/mac/{platform.machine()}/libpv_porcupine.dylib')
        keyword_files = os.listdir(os.path.join(os.path.dirname(pvporcupine.__file__), "resources/keyword_files/mac/"))
        for x in keyword_files:
            pvporcupine.KEYWORD_PATHS[x.split('_')[0]] = os.path.join(os.path.dirname(pvporcupine.__file__),
                                                                      f"resources/keyword_files/mac/{x}")

    for keyword in env.wake_words:
        if keyword == 'sphinx-build':
            break
        if not pvporcupine.KEYWORD_PATHS.get(keyword) or not os.path.isfile(pvporcupine.KEYWORD_PATHS[keyword]):
            raise ValueError(
                f"Detecting '{keyword}' is unsupported!\n"
                f"Available keywords are: {', '.join(list(pvporcupine.KEYWORD_PATHS.keys()))}"
            )

    if audio_driver:
        voices: List[Voice] = audio_driver.getProperty("voices")  # gets the list of voices available
        voice_names = [__voice.name for __voice in voices]
        if not env.voice_name:
            if settings.operating_system == "Darwin":
                env.voice_name = "Daniel"
            elif settings.operating_system == "Windows":
                env.voice_name = "David"
            elif settings.operating_system == "Linux":
                env.voice_name = "english-us"
        elif env.voice_name not in voice_names:
            raise InvalidEnvVars(
                f"{env.voice_name!r} is not available.\nAvailable voices are: {', '.join(voice_names)}"
            )
        for ind_d, voice in enumerate(voices):  # noqa
            if voice.name == env.voice_name:
                logger.debug(voice.__dict__)
                audio_driver.setProperty("voice", voices[ind_d].id)
                audio_driver.setProperty("rate", env.voice_rate)
                break
        else:
            logger.info("Using default voice model.")
    else:
        logger.warning("Failed to load the audio driver. Resolving to use SpeechSynthesis")


logger.info("Current Process: %s", current_process().name)
if current_process().name != "MainProcess" or settings.operating_system == "Linux":
    config = Config()  # Run validations only on SyncManager and child process
else:
    config = None
