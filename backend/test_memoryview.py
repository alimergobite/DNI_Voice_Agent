import ctypes

# Simulate frame.data which is a 160-element array of 16-bit integers
class AudioFrameData(ctypes.Structure):
    _fields_ = [("data", ctypes.c_int16 * 160)]
    
    def __init__(self):
        super().__init__()
        # initialize to zero
        for i in range(160):
            self.data[i] = 0
            
    def get_memoryview(self):
        return memoryview(self.data)

frame_data = AudioFrameData()
mv = frame_data.get_memoryview()

print("Original format:", mv.format)
print("Original itemsize:", mv.itemsize)
print("Original length:", len(mv))

mv_bytes = mv.cast('B')
print("Casted format:", mv_bytes.format)
print("Casted itemsize:", mv_bytes.itemsize)
print("Casted length:", len(mv_bytes))

chunk = b'\x01' * 320
try:
    mv_bytes[:] = chunk
    print("Assignment WORKED!")
    
    # check if the first element is correctly populated
    print("First element after assignment (16-bit):", mv[0])
except Exception as e:
    print(f"Assignment FAILED: {e}")
