import base64
import audioop
import json
import wave

# Generate a 1-second 8kHz sine wave in mu-law
import math
pcm_data = bytearray()
for i in range(8000):
    val = int(32767.0 * math.sin(2 * math.pi * 440.0 * i / 8000.0))
    pcm_data.extend(val.to_bytes(2, 'little', signed=True))

mulaw_data = audioop.lin2ulaw(pcm_data, 2)

tw_ratecv_state = None
tw_audio_buffer = bytearray()
output_pcm_16k = bytearray()

# Simulate Twilio sending 20ms chunks (160 bytes of mu-law)
for i in range(0, len(mulaw_data), 160):
    chunk_mulaw = mulaw_data[i:i+160]
    
    # 1. Decode mulaw
    pcm_8k = audioop.ulaw2lin(chunk_mulaw, 2)
    
    # 2. Upsample 8kHz -> 16kHz
    pcm_16k, tw_ratecv_state = audioop.ratecv(pcm_8k, 2, 1, 8000, 16000, tw_ratecv_state)
    
    # 3. Buffer and chunk 10ms (320 bytes)
    tw_audio_buffer.extend(pcm_16k)
    while len(tw_audio_buffer) >= 320:
        chunk = bytes(tw_audio_buffer[:320])
        tw_audio_buffer = tw_audio_buffer[320:]
        
        output_pcm_16k.extend(chunk)

with wave.open("test_out.wav", "wb") as f:
    f.setnchannels(1)
    f.setsampwidth(2)
    f.setframerate(16000)
    f.writeframes(output_pcm_16k)

print(f"Generated {len(output_pcm_16k)} bytes of 16kHz PCM")
