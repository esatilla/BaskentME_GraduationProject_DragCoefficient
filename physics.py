"""
physics.py - Fizik hesaplamaları modülü
Sürüklenme katsayısı, Reynolds sayısı, terminal hız hesaplamaları
"""
import numpy as np
from scipy.stats import linregress


def calculate_instantaneous_velocity(positions_px, times_s, px_per_mm):
    """
    Piksel pozisyonlarından anlık hızları hesaplar.
    
    positions_px: [(x, y), ...] piksel cinsinden pozisyonlar
    times_s: zaman damgaları (saniye)
    px_per_mm: piksel/mm kalibrasyon faktörü
    
    Returns: (times_mid, velocities_mm_s) - hız noktaları
    """
    if len(positions_px) < 2:
        return np.array([]), np.array([])
    
    y_mm = np.array([p[1] for p in positions_px]) / px_per_mm
    t = np.array(times_s)
    
    dy = np.diff(y_mm)
    dt = np.diff(t)
    
    # Sıfır bölmeyi engelle
    dt = np.where(dt < 1e-6, 1e-6, dt)
    velocities = np.abs(dy / dt)  # mm/s (mutlak değer - aşağı düşüş pozitif)
    times_mid = (t[:-1] + t[1:]) / 2
    
    return times_mid, velocities


def calculate_segment_velocities(positions, timestamps, px_per_mm, segment_mm=50.0):
    """
    Her segment_mm mesafede bir ortalama hız döndürür.
    Düşme yönü: Y ekseni artar (piksel koordinatları).

    Returns: list of dicts
        [{'seg_idx', 'dist_mm', 'v_mm_s', 't_start', 't_end', 'cum_dist_mm'}, ...]
    """
    if len(positions) < 2 or px_per_mm <= 0 or segment_mm <= 0:
        return []

    seg_px  = segment_mm * px_per_mm
    results = []
    y_start = positions[0][1]
    t_start = timestamps[0]
    cum_mm  = 0.0

    for i in range(1, len(positions)):
        dy = abs(positions[i][1] - y_start)
        if dy >= seg_px:
            dt = timestamps[i] - t_start
            if dt > 0:
                dist_mm  = dy / px_per_mm
                cum_mm  += dist_mm
                results.append({
                    'seg_idx':    len(results),
                    'dist_mm':    dist_mm,
                    'v_mm_s':     dist_mm / dt,
                    't_start':    t_start,
                    't_end':      timestamps[i],
                    'cum_dist_mm': cum_mm,
                })
            y_start = positions[i][1]
            t_start = timestamps[i]

    return results


def detect_terminal_velocity(times, velocities, stability_threshold=0.05, min_stable_points=15):
    """
    Hız-zaman grafiğinden terminal hızı tespit eder.
    Hız değişimi threshold'un altına düştüğünde terminal hıza ulaşıldığı kabul edilir.
    
    Returns: (v_terminal, terminal_start_idx) veya (None, None)
    """
    if len(velocities) < min_stable_points:
        return None, None
    
    # Kayan ortalama ile gürültüyü azalt
    window = max(5, len(velocities) // 8)
    if window > len(velocities) // 2:
        window = max(3, len(velocities) // 4)
    
    smoothed = np.convolve(velocities, np.ones(window) / window, mode='valid')
    
    if len(smoothed) < min_stable_points:
        return None, None
    
    # Terminal hız bölgesini tespit et: değişim oranı düşük olan bölge
    for i in range(len(smoothed) - min_stable_points):
        segment = smoothed[i:i + min_stable_points]
        mean_v = np.mean(segment)
        if mean_v < 1e-6:
            continue
        variation = np.std(segment) / mean_v
        if variation < stability_threshold:
            v_terminal = mean_v
            return v_terminal, i + window // 2
    
    # Stabil bölge bulunamadı — terminal hıza ulaşılmamış
    return None, None


def calculate_drag_coefficient(v_terminal_mm_s, diameter_mm, rho_particle, rho_fluid, mu_fluid):
    """
    Terminal hızdan sürüklenme katsayısını hesaplar.
    
    v_terminal_mm_s: terminal hız (mm/s)
    diameter_mm: parçacık çapı (mm)
    rho_particle: parçacık yoğunluğu (kg/m³)
    rho_fluid: akışkan yoğunluğu (kg/m³)
    mu_fluid: dinamik viskozite (Pa·s)
    
    Returns: dict {Cd, Re, v_stokes, Cd_stokes, Cd_empirical, error_stokes, error_empirical}
    """
    g = 9.81  # m/s²
    
    # Birim dönüşümleri
    v_t = v_terminal_mm_s / 1000.0   # m/s
    d = diameter_mm / 1000.0          # m
    r = d / 2.0
    
    if v_t <= 0 or d <= 0 or mu_fluid <= 0:
        return None
    
    # Reynolds sayısı
    Re = rho_fluid * v_t * d / mu_fluid
    
    # Kuvvet dengesi: C_d = (4/3) * (d/v²) * ((ρ_p - ρ_f)/ρ_f) * g
    delta_rho = rho_particle - rho_fluid
    if rho_fluid <= 0:
        return None
    
    C_d = (4.0 / 3.0) * (d / v_t**2) * (delta_rho / rho_fluid) * g
    
    # Stokes yasası terminal hızı: v_s = 2r²(ρ_p - ρ_f)g / (9μ)
    v_stokes = (2 * r**2 * delta_rho * g) / (9 * mu_fluid)  # m/s
    
    # Teorik C_d değerleri
    Cd_stokes = 24.0 / Re if Re > 0 else None
    Cd_empirical = _empirical_cd(Re)
    
    # Hatalar
    error_stokes = abs(C_d - Cd_stokes) / Cd_stokes * 100 if Cd_stokes else None
    error_empirical = abs(C_d - Cd_empirical) / Cd_empirical * 100 if Cd_empirical else None
    
    return {
        'Cd': C_d,
        'Re': Re,
        'v_terminal': v_t * 1000,  # mm/s olarak geri döndür
        'v_stokes': v_stokes * 1000,  # mm/s
        'Cd_stokes': Cd_stokes,
        'Cd_empirical': Cd_empirical,
        'error_stokes_pct': error_stokes,
        'error_empirical_pct': error_empirical,
        'regime': _flow_regime(Re),
    }


def apply_wall_correction(v_measured_mm_s, diameter_mm, cylinder_diameter_mm):
    """
    Duvar etkisi (wall effect) düzeltmesi uygular - Francis/Ladenburg metodu.
    Gerçek terminal hızı = ölçülen hız / düzeltme faktörü
    
    Returns: (v_corrected, correction_factor)
    """
    if cylinder_diameter_mm <= 0 or diameter_mm <= 0:
        return v_measured_mm_s, 1.0
    
    lambda_ = diameter_mm / cylinder_diameter_mm  # oranı
    
    if lambda_ >= 1.0:
        return v_measured_mm_s, 1.0
    
    # Ladenburg düzeltme faktörü (1 + 2.104λ + 2.089λ³ - ...)
    # Bu faktörle ölçülen hız düzeltilir: v_true = v_measured * k_inverse
    # Francis: k = 1 / (1 - 2.104λ + 2.089λ³)
    k = 1.0 / (1.0 - 2.104 * lambda_ + 2.089 * lambda_**3 - 0.948 * lambda_**5)
    v_corrected = v_measured_mm_s / k
    
    return v_corrected, k


def _empirical_cd(Re):
    """Schiller-Naumann ampirik sürüklenme katsayısı."""
    if Re <= 0:
        return None
    if Re < 1000:
        return (24.0 / Re) * (1 + 0.15 * Re**0.687)
    elif Re < 2e5:
        return 0.44
    else:
        return 0.2


def _flow_regime(Re):
    """Reynolds sayısına göre akış rejimi."""
    if Re < 0.5:
        return "Stokes (Sürüngen Akış)"
    elif Re < 2:
        return "Geçiş (Alt)"
    elif Re < 500:
        return "Ara Rejim"
    elif Re < 2e5:
        return "Newton Rejimi"
    else:
        return "Türbülanslı"


def pixel_to_mm_scale(reference_length_px, reference_length_mm):
    """Piksel/mm ölçek faktörünü hesaplar."""
    if reference_length_mm <= 0 or reference_length_px <= 0:
        return 1.0
    return reference_length_px / reference_length_mm
