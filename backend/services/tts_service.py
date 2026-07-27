import asyncio
import uuid
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
        req_id = uuid.uuid4().hex
        output_emitter.initialize(
            request_id=req_id,
            sample_rate=16000,
            num_channels=1,
            stream=False,
            mime_type="audio/pcm"
        )

        # ── Method 1: Pure HTTP REST API (Prevents C++ SPXERR_ABORT exit code -6 crashes) ──
        pcm_bytes = None
        rest_error = None
        
        try:
            import urllib.request, xml.sax.saxutils
            base_url = self._tts.endpoint_url.rstrip("/")
            if "cognitiveservices/v1" in base_url:
                rest_url = base_url
            else:
                rest_url = f"{base_url}/cognitiveservices/v1"

            escaped_text = xml.sax.saxutils.escape(self._text)
            voice_name = self._tts.voice
            
            ssml = (
                f"<speak version='1.0' xml:lang='en-IN'>"
                f"<voice xml:lang='en-IN' name='{voice_name}'>"
                f"{escaped_text}"
                f"</voice></speak>"
            )

            headers = {
                "Ocp-Apim-Subscription-Key": self._tts.speech_key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "raw-16khz-16bit-mono-pcm",
                "User-Agent": "DNIVoiceAgent"
            }

            def make_rest_call(url):
                req = urllib.request.Request(url, data=ssml.encode("utf-8"), headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return resp.read()

            loop = asyncio.get_running_loop()
            try:
                pcm_bytes = await loop.run_in_executor(None, lambda: make_rest_call(rest_url))
            except Exception as e1:
                # Try alternate REST URL path if endpoint includes region / tts prefix
                alt_url = f"{base_url}/tts/cognitiveservices/v1"
                try:
                    pcm_bytes = await loop.run_in_executor(None, lambda: make_rest_call(alt_url))
                except Exception as e2:
                    rest_error = f"REST e1: {e1}, REST e2: {e2}"

        except Exception as ex:
            rest_error = str(ex)

        # If REST API succeeded and returned audio
        if pcm_bytes and len(pcm_bytes) > 0:
            print(f"[Azure REST TTS] Synthesized {len(pcm_bytes)} bytes for: {self._text[:60]}...")
            output_emitter.push(pcm_bytes)
            output_emitter.flush()
            return

        print(f"[Azure REST TTS Warning] REST synthesis failed ({rest_error}), falling back to C++ Speech SDK...")

        # ── Method 2: C++ Speech SDK Fallback (with CRLF & safety flags) ──
        try:
            import azure.cognitiveservices.speech as speechsdk
        except ImportError:
            raise Exception(f"Azure REST failed ({rest_error}) and azure-cognitiveservices-speech is not installed.")

        speech_config = speechsdk.SpeechConfig(
            subscription=self._tts.speech_key,
            endpoint=self._tts.endpoint_url
        )
        speech_config.speech_synthesis_voice_name = self._tts.voice
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Raw16Khz16BitMonoPcm
        )
        speech_config.set_property_by_name("OPENSSL_DISABLE_CRL_CHECK", "true")
        
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
        
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, lambda: synthesizer.speak_text_async(self._text).get()
        )
        
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted and result.audio_data:
            pcm_bytes = result.audio_data
            print(f"[Azure SDK TTS] Synthesized {len(pcm_bytes)} bytes for: {self._text[:60]}...")
            output_emitter.push(pcm_bytes)
            output_emitter.flush()
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation = result.cancellation_details
            print(f"[Azure SDK TTS ERROR] CANCELED: Reason={cancellation.reason}, Details: {cancellation.error_details}")
            raise Exception(f"Azure TTS canceled: {cancellation.error_details}")
        else:
            print(f"[Azure SDK TTS ERROR] Unexpected reason: {result.reason}")
            raise Exception(f"Azure TTS failed with reason: {result.reason}")

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
