import os
import time
import psutil
import signal
import matplotlib.pyplot as plt
from datetime import datetime
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import matplotlib.dates as mdates
import matplotlib.ticker as ticker

timestamps = []
enc_speeds = []
dec_speeds = []
in_traffic = []
out_traffic = []
disk_io = []
disk_enc_speeds = []
time_intervals = []

key = os.urandom(32)
iv = os.urandom(16)
backend = default_backend()
sample_data = os.urandom(10 * 1024 * 1024)

prev_net = psutil.net_io_counters()
prev_disk = psutil.disk_io_counters()
prev_time = time.time()

DISK_PATH = 'C:\\Users\\emo'

print("Available Disk Partitions:")
for disk in psutil.disk_partitions():
    print(f"Disk: {disk.device} | Mount point: {disk.mountpoint}")

def signal_handler(sig, frame):
    print("\nMonitoring interrupted.")
    save_choice = input("Save data as (1) PNG Graph or (2) Log File? Enter 1 or 2: ")
    if save_choice == '1':
        save_as_png()
    elif save_choice == '2':
        save_as_log()
    else:
        print("Invalid choice.")
    exit(0)

signal.signal(signal.SIGINT, signal_handler)

def bytes_to_human(n, pos=None):
    units = ['Bytes', 'KB', 'MB', 'GB', 'TB']
    size = n
    for unit in units:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"

def format_size_dynamic(size_bytes):
    return bytes_to_human(size_bytes)

def measure_encryption_speed():
    start_time = time.time()
    total_bytes = 0
    while time.time() - start_time < 1:
        encryptor = Cipher(algorithms.AES(key), modes.CFB(iv), backend=backend).encryptor()
        _ = encryptor.update(sample_data) + encryptor.finalize()
        total_bytes += len(sample_data)
    duration = time.time() - start_time
    return (total_bytes * 8) / duration / 8

def measure_decryption_speed():
    start_time = time.time()
    total_bytes = 0
    while time.time() - start_time < 1:
        decryptor = Cipher(algorithms.AES(key), modes.CFB(iv), backend=backend).decryptor()
        _ = decryptor.update(sample_data) + decryptor.finalize()
        total_bytes += len(sample_data)
    duration = time.time() - start_time
    return (total_bytes * 8) / duration / 8

def measure_disk_encryption_speed(disk_path):
    try:
        test_file_path = os.path.join(disk_path, 'test_file.dat')
        if not os.path.exists(test_file_path):
            with open(test_file_path, 'wb') as f:
                f.write(sample_data)
        with open(test_file_path, 'rb') as f:
            data = f.read()
        start_time = time.time()
        encryptor = Cipher(algorithms.AES(key), modes.CFB(iv), backend=backend).encryptor()
        _ = encryptor.update(data) + encryptor.finalize()
        duration = time.time() - start_time
        return (len(data) * 8) / duration / 8
    except Exception as e:
        print(f"Error measuring disk speed: {e}")
        return 0

def get_speeds():
    global prev_net, prev_disk, prev_time
    curr_net = psutil.net_io_counters()
    curr_disk = psutil.disk_io_counters()
    curr_time = time.time()

    duration = curr_time - prev_time
    if duration == 0:
        duration = 1e-6

    in_bytes = curr_net.bytes_recv - prev_net.bytes_recv
    out_bytes = curr_net.bytes_sent - prev_net.bytes_sent
    disk_bytes = (curr_disk.read_bytes - prev_disk.read_bytes) + (curr_disk.write_bytes - prev_disk.write_bytes)

    prev_net = curr_net
    prev_disk = curr_disk
    prev_time = curr_time

    return in_bytes / duration, out_bytes / duration, disk_bytes / duration

def save_as_png():
    plt.figure(figsize=(12, 8))
    def plot_data(data, label):
        plt.plot(timestamps, [format_size_dynamic(v) for v in data], label=label)

    plot_data(enc_speeds, 'Encryption Speed')
    plot_data(dec_speeds, 'Decryption Speed')
    plot_data(in_traffic, 'Incoming Traffic')
    plot_data(out_traffic, 'Outgoing Traffic')
    plot_data(disk_io, 'Disk I/O')
    plot_data(disk_enc_speeds, 'Disk Enc Speed')

    plt.xlabel('Time')
    plt.ylabel('Data')
    plt.title('Real-Time System Monitoring')
    plt.legend()
    plt.grid(True)

    ax = plt.gca()
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))
    plt.xticks(rotation=45, ha='right')

    ax.yaxis.set_major_formatter(ticker.FuncFormatter(bytes_to_human))
    ax.yaxis.set_major_locator(ticker.MaxNLocator(6))

    plt.tight_layout()
    filename = f"monitoring_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(filename)
    print(f"Graph saved as {filename}")

def save_as_log():
    filename = f"monitoring_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    with open(filename, 'w') as f:
        f.write("Timestamp,Enc Speed,Dec Speed,In,Out,Disk I/O,Disk Enc Speed,Interval (s)\n")
        for i in range(len(timestamps)):
            interval = time_intervals[i] if i < len(time_intervals) else ''
            f.write(f"{timestamps[i]},"
                    f"{format_size_dynamic(enc_speeds[i])},"
                    f"{format_size_dynamic(dec_speeds[i])},"
                    f"{format_size_dynamic(in_traffic[i])},"
                    f"{format_size_dynamic(out_traffic[i])},"
                    f"{format_size_dynamic(disk_io[i])},"
                    f"{format_size_dynamic(disk_enc_speeds[i])},"
                    f"{interval:.3f}\n")
    print(f"Log saved as {filename}")

prev_timestamp = time.time()

print("Starting real-time system monitoring. Press Ctrl+C to stop and save.")
try:
    while True:
        timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        current_time = time.time()

        interval = current_time - prev_timestamp
        prev_timestamp = current_time

        enc_speed_bps = measure_encryption_speed()
        dec_speed_bps = measure_decryption_speed()

        in_bps, out_bps, disk_bps = get_speeds()

        disk_enc_speed_bps = measure_disk_encryption_speed(DISK_PATH)

        timestamps.append(timestamp_str)
        time_intervals.append(interval)
        enc_speeds.append(enc_speed_bps)
        dec_speeds.append(dec_speed_bps)
        in_traffic.append(in_bps)
        out_traffic.append(out_bps)
        disk_io.append(disk_bps)
        disk_enc_speeds.append(disk_enc_speed_bps)

        print(f"{timestamp_str} | Enc: {format_size_dynamic(enc_speed_bps)} | "
              f"Dec: {format_size_dynamic(dec_speed_bps)} | "
              f"In: {format_size_dynamic(in_bps)} | "
              f"Out: {format_size_dynamic(out_bps)} | "
              f"Disk I/O: {format_size_dynamic(disk_bps)} | "
              f"Disk Enc Speed: {format_size_dynamic(disk_enc_speed_bps)} | "
              f"Interval: {interval:.3f} s", end='\r')

        time.sleep(1)

except KeyboardInterrupt:
    print("\nMonitoring stopped.")
    save_as_png()
    save_as_log()
