from scapy.all import *
import struct
import zlib
import sys
import time
import socket

# Các hằng số cho các loại gói tin
START = 0
END = 1
DATA = 2
ACK = 3

# Hàm trợ giúp tính toán checksum CRC
def calculate_checksum(data):
    return zlib.crc32(data) & 0xffffffff

# Hàm tạo header cho gói tin với checksum
def create_header(seq_num, type, data_len):
    header = struct.pack('!IIII', type, seq_num, data_len, 0)
    checksum = calculate_checksum(header)
    return header[:12] + struct.pack('!I', checksum)

# Hàm tạo gói tin hoàn chỉnh (bao gồm header và dữ liệu)
def create_packet(seq_num, type, payload=b''):
    header = create_header(seq_num, type, len(payload))
    return header + payload

# Hàm gửi tin cậy
def reliable_send(sock, addr, file_data, window_size=4):
    # Chia file_data thành các khối có kích thước 1472 byte
    chunk_size = 1472
    chunks = [file_data[i:i+chunk_size] for i in range(0, len(file_data), chunk_size)]
    total_packets = len(chunks)
    
    base = 0
    next_seq = 0
    acked = set()

    sock.settimeout(1.0)  # Tăng thời gian chờ để xử lý các mạng chậm hơn

    # Gửi gói tin START
    print("Đang gửi gói tin START...")
    start_packet = create_packet(0, START)
    sock.sendto(start_packet, addr)

    # Chờ nhận ACK cho gói START
    while True:
        try:
            data, _ = sock.recvfrom(2048)
            type, ack_seq_num, _, checksum = struct.unpack('!IIII', data[:16])
            if type == ACK and ack_seq_num == 1:
                print("Nhận ACK cho gói START.")
                break
        except socket.timeout:
            sock.sendto(start_packet, addr)

    # Gửi các gói tin DATA với cửa sổ trượt
    print("Đang gửi các gói tin DATA...")
    while base < total_packets:
        # Gửi các gói tin trong cửa sổ
        while next_seq < base + window_size and next_seq < total_packets:
            packet = create_packet(next_seq + 1, DATA, chunks[next_seq])
            sock.sendto(packet, addr)
            print(f"Đã gửi gói tin DATA {next_seq + 1}")
            next_seq += 1

        try:
            data, _ = sock.recvfrom(2048)
            pkt_type, ack_seq_num, _, checksum = struct.unpack('!IIII', data[:16])
            if pkt_type == ACK:
                # ack_seq_num là số gói đã nhận được thành công
                print(f"Nhận ACK cho gói tin {ack_seq_num}")
                if ack_seq_num > base:
                    for i in range(base, ack_seq_num):
                        acked.add(i)
                    base = ack_seq_num
        except socket.timeout:
            # Gửi lại tất cả các gói tin chưa được ACK trong cửa sổ
            print("Đã hết thời gian chờ, gửi lại các gói tin chưa được ACK.")
            for i in range(base, min(base + window_size, total_packets)):
                if i not in acked:
                    packet = create_packet(i + 1, DATA, chunks[i])
                    sock.sendto(packet, addr)
                    print(f"Đã gửi lại gói tin DATA {i + 1}")

    # Gửi gói tin END
    print("Đang gửi gói tin END...")
    end_packet = create_packet(total_packets + 1, END)
    sock.sendto(end_packet, addr)

    # Chờ nhận ACK cho gói END
    while True:
        try:
            data, _ = sock.recvfrom(2048)
            type, ack_seq_num, _, checksum = struct.unpack('!IIII', data[:16])
            if type == ACK and ack_seq_num == total_packets + 1:
                print("Nhận ACK cho gói END. Truyền tải hoàn tất.")
                break
        except socket.timeout:
            sock.sendto(end_packet, addr)

# Chương trình chính
if __name__ == "__main__":
    # Sử dụng các giá trị cố định
    receiver_ip = "127.0.0.1"  # Địa chỉ IP của máy nhận
    receiver_port = 12345      # Cổng nhận
    window_size = 4            # Kích thước cửa sổ

    # Tạo socket UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver_addr = (receiver_ip, receiver_port)

    # Nhập nội dung cần truyền từ terminal
    file_data = input("Nhập nội dung cần truyền: ").encode()

    # Gửi nội dung
    reliable_send(sock, receiver_addr, file_data, window_size)

    # Đóng kết nối
    sock.close()
