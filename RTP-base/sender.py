from scapy.all import *
import struct
import zlib
import sys
import time
import socket
from utils import PacketHeader, compute_checksum  # Import từ utils.py

# Các hằng số cho các loại gói tin
START = 0
END = 1
DATA = 2
ACK = 3

# Hàm tạo gói tin với header sử dụng PacketHeader từ utils.py
def create_packet(seq_num, type, payload=b''):
    header = PacketHeader(type=type, seq_num=seq_num, length=len(payload), checksum=0)
    header.checksum = compute_checksum(header)
    return bytes(header) + payload

# Hàm gửi tin cậy
def reliable_send(sock, addr, file_data, window_size=4):
    chunk_size = 1472
    chunks = [file_data[i:i+chunk_size] for i in range(0, len(file_data), chunk_size)]
    total_packets = len(chunks)
    
    base = 0
    next_seq = 0
    acked = set()

    sock.settimeout(1.0)

    # Gửi gói tin START
    print("Đang gửi gói tin START...")
    start_packet = create_packet(0, START)
    sock.sendto(start_packet, addr)

    while True:
        try:
            data, _ = sock.recvfrom(2048)
            pkt_header = PacketHeader(data[:16])
            if pkt_header.type == ACK and pkt_header.seq_num == 1:
                print("Nhận ACK cho gói START.")
                break
        except socket.timeout:
            sock.sendto(start_packet, addr)

    print("Đang gửi các gói tin DATA...")
    while base < total_packets:
        while next_seq < base + window_size and next_seq < total_packets:
            packet = create_packet(next_seq + 1, DATA, chunks[next_seq])
            sock.sendto(packet, addr)
            print(f"Đã gửi gói tin DATA {next_seq + 1}")
            next_seq += 1

        try:
            data, _ = sock.recvfrom(2048)
            pkt_header = PacketHeader(data[:16])
            if pkt_header.type == ACK:
                if pkt_header.seq_num > base:
                    for i in range(base, pkt_header.seq_num):
                        acked.add(i)
                    base = pkt_header.seq_num
        except socket.timeout:
            print("Đã hết thời gian chờ, gửi lại các gói tin chưa được ACK.")
            for i in range(base, min(base + window_size, total_packets)):
                if i not in acked:
                    packet = create_packet(i + 1, DATA, chunks[i])
                    sock.sendto(packet, addr)
                    print(f"Đã gửi lại gói tin DATA {i + 1}")

    print("Đang gửi gói tin END...")
    end_packet = create_packet(total_packets + 1, END)
    sock.sendto(end_packet, addr)

    while True:
        try:
            data, _ = sock.recvfrom(2048)
            pkt_header = PacketHeader(data[:16])
            if pkt_header.type == ACK and pkt_header.seq_num == total_packets + 1:
                print("Nhận ACK cho gói END. Truyền tải hoàn tất.")
                break
        except socket.timeout:
            sock.sendto(end_packet, addr)

# Chương trình chính
if __name__ == "__main__":
    receiver_ip = "127.0.0.1"
    receiver_port = 12345
    window_size = 4

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver_addr = (receiver_ip, receiver_port)

    with open('test_scripts/test_message.txt', 'rb') as f:
        file_data = f.read()

    reliable_send(sock, receiver_addr, file_data, window_size)

    sock.close()
