from livekit.api import VideoGrants
grants = VideoGrants(room_join=True, room="test")
print(f"can_publish: {grants.can_publish}")
