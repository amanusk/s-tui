import glob
import os

def get_cpu_freq():
    """
    Reads CPU frequencies from /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq.
    Uses glob to find all CPU cores and handles potential read errors gracefully.
    """
    freqs = []
    cpu_paths = glob.glob("/sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_cur_freq")
    
    # Sort paths to ensure consistent ordering if needed
    cpu_paths.sort(key=lambda x: int(x.split('cpu')[1].split('/')[0]))

    for path in cpu_paths:
        try:
            with open(path, 'r') as f:
                val = f.read().strip()
                if val:
                    freqs.append(int(val) / 1000.0)  # Convert kHz to MHz
                else:
                    freqs.append(0.0)
        except (IOError, ValueError, PermissionError):
            # Skip cores that fail to report frequency
            freqs.append(0.0)
            
    return freqs
