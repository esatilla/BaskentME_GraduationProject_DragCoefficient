from pypylon import pylon

print("pypylon OK")
factory = pylon.TlFactory.GetInstance()

print("USB transport layer direkt aciliyor (GigE atlanıyor)...")
usb_tl  = factory.CreateTl("BaslerUsb")          # sadece USB — GigE yok
devices = usb_tl.EnumerateDevices()
print(f"Bulunan: {len(devices)} kamera")

if not devices:
    print("USB kamera bulunamadi."); exit()

for i,d in enumerate(devices):
    print(f"  [{i}] {d.GetModelName()} S/N:{d.GetSerialNumber()}")

print("Aciliyor...")
cam = pylon.InstantCamera(usb_tl.CreateDevice(devices[0]))
cam.Open()
print("Acildi!")

try: print("Pixel formatları:", list(cam.PixelFormat.Symbolics))
except: pass

print("Grab testi...")
converter = pylon.ImageFormatConverter()
converter.OutputPixelFormat  = pylon.PixelType_BGR8packed
converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
for i in range(3):
    gr = cam.RetrieveResult(3000, pylon.TimeoutHandling_ThrowException)
    if gr.GrabSucceeded():
        img = converter.Convert(gr)
        arr = img.GetArray()
        print(f"  Kare {i+1}: {arr.shape} dtype={arr.dtype}")
    gr.Release()
cam.StopGrabbing()
cam.Close()
print("BASARILI!")
