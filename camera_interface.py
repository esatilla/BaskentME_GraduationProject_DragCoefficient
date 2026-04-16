"""
camera_interface.py - Basler acA 1440-220uc
CreateTl("BaslerUsb") kullanır — GigE Connection Guard bypass.
"""
import os, sys, pathlib

# Sistem Pylon SDK kuruluysa GENICAM_GENTL64_PATH değişkeni sistem DLL'lerine
# işaret eder — bu pypylon'un paketlediği DLL'lerle çakışıp segfault verir.
# Çözüm: GENTL path'i pypylon paket dizinine yönlendir.
def _fix_pypylon_dll_path():
    try:
        import pypylon
        pkg_dir = str(pathlib.Path(pypylon.__file__).parent)
        os.environ['GENICAM_GENTL64_PATH'] = pkg_dir + os.sep
        os.environ['GENICAM_GENTL32_PATH'] = pkg_dir + os.sep
        if hasattr(os, 'add_dll_directory'):
            os.add_dll_directory(pkg_dir)
    except ImportError:
        pass
_fix_pypylon_dll_path()

import cv2, numpy as np, time, threading, queue


class BaslerCamera:

    def __init__(self):
        self.camera      = None
        self.is_open     = False
        self._running    = False
        self._thread     = None
        self._queue      = queue.Queue(maxsize=4)   # sadece ekran için (latest)
        self._converter  = None
        self._pylon      = None
        self._usb_tl     = None     # USB transport layer
        self._has_fps    = False
        self.fps         = 100.0
        self.exposure_us = 1000
        self._frame_cb   = None     # callback(frame, timestamp) — grab thread'inde çağrılır
        self.grab_fps    = 0.0      # gerçek yakalama hızı
        self._recorder   = None     # cv2.VideoWriter — ham kayıt
        self._rec_count  = 0        # kaydedilen frame sayısı
        self._rec_rotate = -1       # kayıt döndürme kodu (-1=yok, 0/1/2=cv2 kodu)

    def open(self, device_index=0):
        # 1. pypylon import
        try:
            from pypylon import pylon
            self._pylon = pylon
        except ImportError:
            return False, "pypylon bulunamadı. 'pip install pypylon' çalıştırın."

        # 2. SADECE USB transport layer — GigE Connection Guard'ı atlar
        try:
            factory      = pylon.TlFactory.GetInstance()
            self._usb_tl = factory.CreateTl("BaslerUsb")
            devices      = self._usb_tl.EnumerateDevices()
        except Exception as e:
            return False, f"USB transport layer başlatılamadı: {e}"

        if not devices:
            return False, ("USB Basler kamera bulunamadı.\n"
                           "• USB kablosunu söküp takın\n"
                           "• Pylon Viewer açıksa kapatın\n"
                           "• Farklı USB portunu deneyin")

        if device_index >= len(devices):
            device_index = 0

        # 3. Kamerayı USB transport layer üzerinden aç
        try:
            self.camera = pylon.InstantCamera(
                self._usb_tl.CreateDevice(devices[device_index]))
            self.camera.Open()
        except Exception as e:
            return False, f"Kamera açılamadı: {e}"

        model = devices[device_index].GetModelName()

        # 4. Ayarlar
        self._setup_pixel_format()
        self._setup_fps()
        self._setup_exposure()
        self._setup_gain()
        self._setup_trigger()
        self._setup_converter()

        self.is_open = True
        return True, f"✓ Kamera açıldı: {model}"

    def _setup_pixel_format(self):
        try:
            available = list(self.camera.PixelFormat.Symbolics)
        except Exception:
            return
        for fmt in ["Mono8","BGR8","RGB8","BayerRG8","BayerGB8","BayerBG8"]:
            if fmt in available:
                try:
                    self.camera.PixelFormat.SetValue(fmt)
                    return
                except Exception:
                    continue

    def _setup_fps(self):
        try:
            self.camera.AcquisitionFrameRateEnable.SetValue(True)
            max_fps = self.camera.AcquisitionFrameRate.GetMax()
            self.camera.AcquisitionFrameRate.SetValue(min(self.fps, max_fps))
            self._has_fps = True
        except Exception:
            pass

    def _setup_exposure(self):
        try: self.camera.ExposureAuto.SetValue("Off")
        except Exception: pass
        for attr in ["ExposureTime", "ExposureTimeAbs"]:
            try:
                getattr(self.camera, attr).SetValue(float(self.exposure_us))
                return
            except Exception:
                continue

    def _setup_gain(self):
        try: self.camera.GainAuto.SetValue("Off")
        except Exception: pass
        for attr, val in [("Gain", 0.0), ("GainRaw", 0)]:
            try:
                getattr(self.camera, attr).SetValue(val)
                return
            except Exception:
                continue

    def _setup_trigger(self):
        try: self.camera.TriggerMode.SetValue("Off")
        except Exception: pass

    def _setup_converter(self):
        try:
            pylon = self._pylon
            self._converter = pylon.ImageFormatConverter()
            self._converter.OutputPixelFormat  = pylon.PixelType_BGR8packed
            self._converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
        except Exception:
            self._converter = None

    def start_capture(self):
        if not self.is_open:
            return False
        pylon = self._pylon
        for strategy in [pylon.GrabStrategy_LatestImageOnly,
                         pylon.GrabStrategy_OneByOne]:
            try:
                self.camera.StartGrabbing(strategy)
                break
            except Exception:
                continue
        self._running = True
        self._thread  = threading.Thread(target=self._grab_loop, daemon=True)
        self._thread.start()
        return True

    def set_frame_callback(self, cb):
        """Her yakalanan frame için çağrılacak callback: cb(frame, timestamp).
        Grab thread'inde çalışır — hafif işlem yapılmalıdır."""
        self._frame_cb = cb

    def _grab_loop(self):
        pylon = self._pylon
        fps_count = 0
        fps_timer = time.time()
        has_cb = self._frame_cb is not None
        display_interval = 1.0 / 30.0   # ekrana ~30 FPS yeter
        last_display = 0.0
        while self._running:
            if not self.camera.IsGrabbing():
                break
            try:
                gr = self.camera.RetrieveResult(
                    2000, pylon.TimeoutHandling_ThrowException)
                if not gr.GrabSucceeded():
                    gr.Release(); continue
            except Exception:
                time.sleep(0.01)
                continue

            ts = time.time()
            fps_count += 1

            # Raw array — tespit callback + ham kayıt için
            try:
                raw = gr.GetArray()
            except Exception:
                gr.Release(); continue

            # Callback: HER frame için (tespit)
            if has_cb:
                try:
                    self._frame_cb(raw, ts)
                except Exception:
                    pass

            # Ham video kayıt — belleğe frame biriktir (döndürülmüş)
            if self._recorder is not None:
                try:
                    f = cv2.cvtColor(raw, cv2.COLOR_GRAY2BGR) if raw.ndim == 2 else raw.copy()
                    rc = self._rec_rotate
                    if rc >= 0:
                        f = cv2.rotate(f, rc)
                    self._rec_frames.append(f)
                    self._rec_count += 1
                except Exception:
                    pass

            # Ekran kuyruğu: BGR dönüşümü sadece ~30 FPS
            if ts - last_display >= display_interval:
                last_display = ts
                try:
                    frame = self._to_bgr(gr)
                except Exception:
                    gr.Release(); continue
                if frame is not None:
                    while not self._queue.empty():
                        try: self._queue.get_nowait()
                        except queue.Empty: break
                    try: self._queue.put_nowait((frame, ts))
                    except queue.Full: pass

            gr.Release()

            # Grab FPS
            el = time.time() - fps_timer
            if el >= 1.0:
                self.grab_fps = fps_count / el
                fps_count = 0
                fps_timer = time.time()

    def _to_bgr(self, gr):
        if self._converter is not None:
            try:
                img = self._converter.Convert(gr)
                arr = img.GetArray()
                if arr.ndim == 2:
                    arr = cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
                return arr
            except Exception:
                pass
        arr = gr.GetArray()
        if arr.ndim == 2:
            arr = cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
        return arr

    def read(self):
        try:
            frame, ts = self._queue.get(timeout=0.15)
            return True, frame, ts
        except queue.Empty:
            return False, None, None

    def set_exposure(self, us):
        self.exposure_us = us
        if not self.is_open: return
        for attr in ["ExposureTime", "ExposureTimeAbs"]:
            try: getattr(self.camera, attr).SetValue(float(us)); return
            except Exception: continue

    def set_fps(self, fps):
        self.fps = float(fps)
        if not self.is_open or not self._has_fps: return
        try:
            self.camera.AcquisitionFrameRate.SetValue(
                min(fps, self.camera.AcquisitionFrameRate.GetMax()))
        except Exception: pass

    # ── ROI ──────────────────────���───────────────────────────────────────────

    def set_roi(self, offset_x, offset_y, width, height, pixel_format=None):
        """ROI ayarla. Grab döngüsünü geçici olarak durdurur.
        pixel_format: isteğe bağlı piksel formatı değişikliği (örn. 'BayerRG8').
        """
        if not self.is_open:
            return False, "Kamera açık değil"
        was_running = self._running
        # Grab döngüsünü durdur
        self._running = False
        try:
            if self.camera.IsGrabbing():
                self.camera.StopGrabbing()
        except Exception:
            pass
        time.sleep(0.15)   # Döngünün çıkması için bekle
        # Kuyruğu temizle
        while not self._queue.empty():
            try: self._queue.get_nowait()
            except Exception: break
        try:
            # Piksel formatı değişikliği (isteğe bağlı — daha yüksek FPS için)
            if pixel_format:
                try:
                    available = list(self.camera.PixelFormat.Symbolics)
                    if pixel_format in available:
                        self.camera.PixelFormat.SetValue(pixel_format)
                except Exception:
                    pass
            # Sıralama önemli: önce offset sıfırla, sonra boyut, sonra offset
            self.camera.OffsetX.SetValue(0)
            self.camera.OffsetY.SetValue(0)
            self.camera.Width.SetValue(int(width))
            self.camera.Height.SetValue(int(height))
            self.camera.OffsetX.SetValue(int(offset_x))
            self.camera.OffsetY.SetValue(int(offset_y))
            result = True, f"ROI: {width}×{height} @ ({offset_x},{offset_y})"
        except Exception as e:
            result = False, f"ROI hatası: {e}"
        # Grab döngüsünü yeniden başlat
        if was_running:
            pylon = self._pylon
            for strategy in [pylon.GrabStrategy_LatestImageOnly,
                              pylon.GrabStrategy_OneByOne]:
                try:
                    self.camera.StartGrabbing(strategy)
                    break
                except Exception:
                    continue
            self._running = True
            self._thread = threading.Thread(target=self._grab_loop, daemon=True)
            self._thread.start()
        return result

    def reset_roi(self):
        """Tam sensör alanına döndür."""
        if not self.is_open:
            return
        try:
            w_max = self.camera.Width.GetMax()
            h_max = self.camera.Height.GetMax()
            self.set_roi(0, 0, w_max, h_max)
        except Exception:
            pass

    def get_roi(self):
        """Mevcut ROI değerlerini döndür: (offset_x, offset_y, width, height)."""
        if not self.is_open:
            return 0, 0, 1440, 1080
        try:
            return (self.camera.OffsetX.GetValue(),
                    self.camera.OffsetY.GetValue(),
                    self.camera.Width.GetValue(),
                    self.camera.Height.GetValue())
        except Exception:
            return 0, 0, 1440, 1080

    # ── Gain ────────────────────────────────────────────────────────────���────

    def set_gain(self, db):
        """Gain ayarla (0.0 – 36.0 dB)."""
        if not self.is_open:
            return
        try:
            self.camera.GainAuto.SetValue("Off")
            g_min = self.camera.Gain.GetMin()
            g_max = self.camera.Gain.GetMax()
            self.camera.Gain.SetValue(float(max(g_min, min(db, g_max))))
        except Exception:
            pass

    def set_gain_auto(self, mode="Off"):
        """Gain modunu ayarla: 'Off' | 'Once' | 'Continuous'."""
        if not self.is_open:
            return
        try:
            self.camera.GainAuto.SetValue(mode)
        except Exception:
            pass

    # ── White Balance ──────────────────────────────────────��──────────────────

    def set_white_balance(self, red, green, blue):
        """Manuel beyaz dengesi oranlarını ayarla (0.0 – 15.9998)."""
        if not self.is_open:
            return
        try:
            self.camera.BalanceWhiteAuto.SetValue("Off")
            for ch, val in [("Red", red), ("Green", green), ("Blue", blue)]:
                self.camera.BalanceRatioSelector.SetValue(ch)
                self.camera.BalanceRatio.SetValue(float(val))
        except Exception:
            pass

    def set_wb_auto(self, mode="Off"):
        """Beyaz dengesi modunu ayarla: 'Off' | 'Once' | 'Continuous'."""
        if not self.is_open:
            return
        try:
            self.camera.BalanceWhiteAuto.SetValue(mode)
        except Exception:
            pass

    def get_settings(self):
        """Kameranın mevcut ayarlarını sözlük olarak döndür."""
        if not self.is_open:
            return {}
        s = {}
        try: s['roi'] = self.get_roi()
        except Exception: pass
        try: s['pixel_format'] = self.camera.PixelFormat.GetValue()
        except Exception: pass
        try: s['fps_enable'] = self.camera.AcquisitionFrameRateEnable.GetValue()
        except Exception: pass
        try: s['fps'] = self.camera.AcquisitionFrameRate.GetValue()
        except Exception: pass
        try: s['resulting_fps'] = self.camera.ResultingFrameRate.GetValue()
        except Exception: pass
        try: s['exposure'] = self.camera.ExposureTime.GetValue()
        except Exception: pass
        try: s['gain_auto'] = self.camera.GainAuto.GetValue()
        except Exception: pass
        try: s['gain'] = self.camera.Gain.GetValue()
        except Exception: pass
        if s.get('pixel_format') != 'Mono8':
            try:
                s['wb_auto'] = self.camera.BalanceWhiteAuto.GetValue()
                wb = {}
                for ch in ["Red", "Green", "Blue"]:
                    self.camera.BalanceRatioSelector.SetValue(ch)
                    wb[ch.lower()] = self.camera.BalanceRatio.GetValue()
                s['wb'] = wb
            except Exception: pass
        try: s['temperature'] = self.camera.DeviceTemperature.GetValue()
        except Exception: pass
        return s

    def configure_experiment_mode(self, roi_height=270):
        """Kamera durdurulmadan (henüz grab başlamadan) deney modunu ayarla.
        Sıra: BayerRG8 formatı → 1440×roi_height HW ROI → maks FPS.
        roi_height: ROI yüksekliği (piksel, çifte yuvarlanır).
        """
        if not self.is_open:
            return []
        msgs = []
        # Piksel formatı: 1 byte/piksel
        try:
            available = list(self.camera.PixelFormat.Symbolics)
            for fmt in ["Mono8", "BayerRG8", "BayerGB8", "BayerBG8"]:
                if fmt in available:
                    self.camera.PixelFormat.SetValue(fmt)
                    msgs.append(f"Format: {fmt}")
                    break
        except Exception as e:
            msgs.append(f"Format hatasi: {e}")
        # Hardware ROI: 1440×roi_height, dikey merkez
        try:
            self.camera.OffsetX.SetValue(0)
            self.camera.OffsetY.SetValue(0)
            w = 1440
            h = (int(roi_height) // 2) * 2   # inc=2'ye yuvarla
            h = max(2, min(h, self.camera.Height.GetMax()))
            self.camera.Width.SetValue(w)
            self.camera.Height.SetValue(h)
            sensor_h = self.camera.SensorHeight.GetValue()
            oy = ((sensor_h - h) // 2 // 2) * 2
            self.camera.OffsetY.SetValue(oy)
            msgs.append(f"HW ROI: {w}x{h} @(0,{oy})")
        except Exception as e:
            msgs.append(f"ROI hatasi: {e}")
        # FPS: mümkün olan en yüksek
        try:
            self.camera.AcquisitionFrameRateEnable.SetValue(True)
            fps_max = self.camera.AcquisitionFrameRate.GetMax()
            target  = min(800.0, fps_max)
            self.camera.AcquisitionFrameRate.SetValue(target)
            msgs.append(f"FPS: {target:.0f} (maks={fps_max:.1f})")
        except Exception as e:
            msgs.append(f"FPS hatasi: {e}")
        return msgs

    # ── Ham video kayıt (belleğe) ───────────────────────────────────────────

    def start_recording(self, rotation_code=0):
        """Bellekte frame biriktirmeye başla.
        rotation_code: 0=yok, 1=90°CW, 2=180°, 3=90°CCW
        """
        self._rec_frames = []
        self._recorder = True
        self._rec_count = 0
        _cv2_rot = {1: cv2.ROTATE_90_CLOCKWISE,
                    2: cv2.ROTATE_180,
                    3: cv2.ROTATE_90_COUNTERCLOCKWISE}
        self._rec_rotate = _cv2_rot.get(rotation_code, -1)

    def stop_recording(self):
        """Biriktirmeyi durdur. (frame listesi _rec_frames'te kalır.)"""
        self._recorder = None
        count = self._rec_count
        self._rec_count = 0
        return count

    def get_recorded_frames(self):
        """Kaydedilen frame listesini döndür ve temizle."""
        frames = getattr(self, '_rec_frames', [])
        self._rec_frames = []
        return frames

    def save_recording(self, filepath, fps=None):
        """Bellekteki frameleri dosyaya yaz."""
        frames = getattr(self, '_rec_frames', [])
        if not frames:
            return 0
        if fps is None:
            fps = self.grab_fps if self.grab_fps > 0 else 800.0
        h, w = frames[0].shape[:2]
        fourcc = (cv2.VideoWriter_fourcc(*'XVID') if filepath.endswith('.avi')
                  else cv2.VideoWriter_fourcc(*'mp4v'))
        writer = cv2.VideoWriter(filepath, fourcc, fps, (w, h))
        for f in frames:
            writer.write(f)
        writer.release()
        return len(frames)

    def stop(self):
        self._running = False
        self.stop_recording()
        try:
            if self.camera and self.camera.IsGrabbing():
                self.camera.StopGrabbing()
        except Exception: pass

    def close(self):
        self.stop()
        try:
            if self.camera and self.is_open:
                self.camera.Close()
        except Exception: pass
        self.is_open = False


class VideoFileSource:
    def __init__(self):
        self.cap=None; self.is_open=False; self.paused=False
        self.fps=30.0; self.total_frames=0; self.current_frame_idx=0

    def open(self, filepath):
        self.cap = cv2.VideoCapture(filepath)
        if not self.cap.isOpened():
            return False, f"Video açılamadı: {filepath}"
        self.is_open=True
        self.fps=self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.total_frames=int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        w=int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h=int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        import os
        return True,(f"✓ Video: {os.path.basename(filepath)} {w}x{h} "
                     f"{self.fps:.1f}fps {self.total_frames}kare")

    def read(self):
        if not self.is_open: return False,None,None
        ret,frame=self.cap.read()
        if not ret: return False,None,None
        self.current_frame_idx=int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        return True,frame,self.cap.get(cv2.CAP_PROP_POS_MSEC)/1000.0

    def seek(self,idx):
        if self.cap: self.cap.set(cv2.CAP_PROP_POS_FRAMES,idx)
    def pause(self):  self.paused=True
    def resume(self): self.paused=False
    def close(self):
        if self.cap: self.cap.release()
        self.is_open=False

    @property
    def progress(self):
        return self.current_frame_idx/self.total_frames if self.total_frames else 0
    @property
    def current_time_s(self):
        return self.cap.get(cv2.CAP_PROP_POS_MSEC)/1000.0 if self.cap else 0


class MockCamera:
    def __init__(self,width=1440,height=1080,fps=30):
        self.width=width; self.height=height; self.fps=fps
        self.is_open=False; self._py=80.0; self._v=0.0

    def open(self,device_index=0):
        self.is_open=True
        return True,"TEST MODU – Simüle kamera aktif"

    def start_capture(self): return True

    def read(self):
        if not self.is_open: return False,None,None
        dt=1.0/max(self.fps,1)
        self._v=min(self._v+60*dt,200); self._py+=self._v*dt
        if self._py>self.height-60: self._py=80.0; self._v=0.0
        f=np.zeros((self.height,self.width,3),np.uint8)
        cx=self.width//2
        cv2.rectangle(f,(cx-160,0),(cx+160,self.height),(35,40,55),-1)
        cv2.circle(f,(cx,int(self._py)),22,(190,190,190),-1)
        cv2.putText(f,f"SIM v={self._v:.0f}px/s",(10,self.height-15),
                    cv2.FONT_HERSHEY_SIMPLEX,0.5,(80,80,80),1)
        time.sleep(dt)
        return True,f,time.time()

    def set_exposure(self,us): pass
    def set_fps(self,fps): self.fps=max(fps,1)
    def stop(self): pass
    def close(self): self.is_open=False
