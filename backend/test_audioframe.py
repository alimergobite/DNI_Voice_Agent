from livekit import rtc
try:
    options = rtc.TrackPublishOptions()
    options.source = rtc.TrackSource.SOURCE_MICROPHONE
    print("TrackPublishOptions.source assignment WORKED!")
except Exception as e:
    print(f"Error: {e}")
