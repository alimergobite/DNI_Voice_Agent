import asyncio
import uuid
import azure.cognitiveservices.speech as speechsdk
from livekit.plugins import elevenlabs, sarvam
from livekit.agents import tts, DEFAULT_API_CONNECT_OPTIONS
from backend.config import settings

class AzureSpeechSDKTTS(tts.TTS):
    def __init__(self, speech_key: str, endpoint_url: str, voice: str = "en-IN-Diya:DragonHDLatestNeural"):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=16000,
            num_channels=1
        )
        self.speech_key = speech_key
        self.endpoint_url = endpoint_url
        self.voice = voice

    def synthesize(self, text: str, *, conn_options=None) -> "SynthesizeStream":
        return SynthesizeStream(tts=self, text=text, conn_options=conn_options)

class SynthesizeStream(tts.SynthesizeStream):
    def __init__(self, tts: AzureSpeechSDKTTS, text: str, conn_options=None):
        super().__init__(tts=tts, conn_options=conn_options or DEFAULT_API_CONNECT_OPTIONS)
        self._tts = tts
        self._text = text

    async def _run(self, output_emitter):
        speech_config = speechsdk.SpeechConfig(
            subscription=self._tts.speech_key,
            endpoint=self._tts.endpoint_url
        )
        speech_config.speech_synthesis_voice_name = self._tts.voice
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Raw16Khz16BitMonoPcm
        )
        
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
        
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, lambda: synthesizer.speak_text_async(self._text).get()
        )
        
        req_id = uuid.uuid4().hex
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted and result.audio_data:
            pcm_bytes = result.audio_data
            output_emitter.initialize(
                request_id=req_id,
                sample_rate=16000,
                num_channels=1,
                stream=True,
                mime_type="audio/pcm"
            )
            output_emitter.start_segment(segment_id=req_id)
            output_emitter.push(pcm_bytes)
            output_emitter.end_segment()
            output_emitter.end_input()

def get_tts_engine(provider: str = "azure"):
    """
    Returns the configured Text-to-Speech (TTS) engine.
    Defaults to Azure Speech SDK TTS with voice 'en-IN-Diya:DragonHDLatestNeural'.
    """
    if provider == "sarvam":
        return sarvam.TTS(
            api_key=settings.SARVAM_API_KEY,
            speaker="ritu"
        )
    elif provider == "elevenlabs":
        return elevenlabs.TTS(
            api_key=settings.ELEVENLABS_API_KEY, 
            model="eleven_flash_v2_5",
            voice_id=settings.ELEVENLABS_VOICE_ID,
            streaming_latency=2
        )
    else:
        # Default to Azure Speech SDK TTS (en-IN-Diya:DragonHDLatestNeural)
        return AzureSpeechSDKTTS(
            speech_key=settings.AZURE_SPEECH_KEY or settings.AZURE_OPENAI_API_KEY,
            endpoint_url=settings.AZURE_SPEECH_ENDPOINT,
            voice="en-IN-Diya:DragonHDLatestNeural"
        )
