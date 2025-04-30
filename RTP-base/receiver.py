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

# Hàm để tạo gói tin với header sử dụng PacketHeader từ utils.py
def create_packet(seq_num, type, payload=b''):
    # Tạo header gói tin sử dụng PacketHeader
    header = PacketHeader(type=type, seq_num=seq_num, length=len(payload), checksum=0)
    
    # Tính toán checksum cho header và gói tin
    header.checksum = compute_checksum(header)
    
    # Trả về gói tin (header + payload)
    return bytes(header) + payload

# Hàm nhận dữ liệu chính
def reliable_receive(sock, window_size=4):
    expected_seq = 1
    received_data = b''

    while True:
        try:
            # Nhận dữ liệu từ socket
            data, addr = sock.recvfrom(2048)
            pkt_header = PacketHeader(data[:16])

            # Kiểm tra checksum
            if pkt_header.checksum != compute_checksum(pkt_header):
                print(f"Lỗi checksum cho gói tin {pkt_header.seq_num}, bỏ qua.")
                continue

            # Xử lý các loại gói tin khác nhau
            if pkt_header.type == START:
                print("Nhận được gói tin START.")
                ack_packet = create_packet(1, ACK, b'')
                sock.sendto(ack_packet, addr)
                print("Gửi ACK cho gói tin START.")

            elif pkt_header.type == DATA:
                if pkt_header.seq_num == expected_seq:
                    print(f"Nhận được gói tin DATA {pkt_header.seq_num}")
                    received_data += data[16:]
                    expected_seq += 1

                    # Gửi ACK cho gói tin đã nhận
                    ack_packet = create_packet(pkt_header.seq_num, ACK, b'')
                    sock.sendto(ack_packet, addr)
                    print(f"Gửi ACK cho gói tin DATA {pkt_header.seq_num}")

                else:
                    print(f"Gói tin ngoài thứ tự {pkt_header.seq_num}, mong đợi {expected_seq}. Gửi lại ACK {expected_seq}.")
                    ack_packet = create_packet(expected_seq, ACK, b'')
                    sock.sendto(ack_packet, addr)

            elif pkt_header.type == END:
                print("Nhận được gói tin END.")
                ack_packet = create_packet(pkt_header.seq_num, ACK, b'')
                sock.sendto(ack_packet, addr)
                print(f"Gửi ACK cho gói tin END {pkt_header.seq_num}.")
                break

        except Exception as e:
            print(f"Xảy ra lỗi: {e}")
            continue

    with open('RTP-base/output.txt', 'wb') as f:
        f.write(received_data)

    return received_data

# Chương trình chính
if __name__ == "__main__":
    receiver_ip = "127.0.0.1"
    receiver_port = 12345
    window_size = 4

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((receiver_ip, receiver_port))

    print("Máy nhận đã sẵn sàng nhận dữ liệu...")

    file_data = reliable_receive(sock, window_size)
    print("Dữ liệu nhận được:", file_data.decode())

    sock.close()
