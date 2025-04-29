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

# Hàm trợ giúp để tính toán checksum CRC
def calculate_checksum(data):
    return zlib.crc32(data) & 0xffffffff

# Hàm để tạo header gói tin với checksum
def create_header(seq_num, type, data_len):
    header = struct.pack('!IIII', type, seq_num, data_len, 0)
    checksum = calculate_checksum(header)
    return header[:12] + struct.pack('!I', checksum)

# Hàm để tạo một gói tin đầy đủ (header + dữ liệu)
def create_packet(seq_num, type, payload=b''):
    header = create_header(seq_num, type, len(payload))
    return header + payload

# Hàm nhận dữ liệu chính
def reliable_receive(sock, window_size=4):
    expected_seq = 1
    received_data = b''

    # Không cần set timeout ở đây vì bên nhận chỉ cần chờ nhận gói tin
    while True:
        try:
            # Nhận dữ liệu từ socket
            data, addr = sock.recvfrom(2048)
            pkt_type, seq_num, data_len, checksum = struct.unpack('!IIII', data[:16])
            packet_data = data[16:]

            # Kiểm tra checksum
            if checksum != calculate_checksum(data[:12] + struct.pack('!I', 0)):
                print(f"Lỗi checksum cho gói tin {seq_num}, bỏ qua.")
                continue

            # Xử lý các loại gói tin khác nhau
            if pkt_type == START:
                print("Nhận được gói tin START.")
                # Gửi ACK cho gói START
                ack_packet = create_packet(1, ACK, b'')
                sock.sendto(ack_packet, addr)
                print("Gửi ACK cho gói tin START.")

            elif pkt_type == DATA:
                if seq_num == expected_seq:
                    print(f"Nhận được gói tin DATA {seq_num}")
                    received_data += packet_data
                    expected_seq += 1

                    # Gửi ACK cho gói tin đã nhận
                    ack_packet = create_packet(seq_num, ACK, b'')
                    sock.sendto(ack_packet, addr)
                    print(f"Gửi ACK cho gói tin DATA {seq_num}")

                else:
                    print(f"Gói tin ngoài thứ tự {seq_num}, mong đợi {expected_seq}. Gửi lại ACK {expected_seq}.")
                    # Gửi lại ACK cho gói tin mong đợi
                    ack_packet = create_packet(expected_seq, ACK, b'')
                    sock.sendto(ack_packet, addr)

            elif pkt_type == END:
                print("Nhận được gói tin END.")
                # Gửi ACK cho gói END
                ack_packet = create_packet(seq_num, ACK, b'')
                sock.sendto(ack_packet, addr)
                print(f"Gửi ACK cho gói tin END {seq_num}.")
                break

        except Exception as e:
            print(f"Xảy ra lỗi: {e}")
            continue

    return received_data

# Chương trình chính
if __name__ == "__main__":
    # Sử dụng các giá trị cố định
    receiver_ip = "127.0.0.1"  # Địa chỉ IP của máy nhận
    receiver_port = 12345      # Cổng nhận
    window_size = 4            # Kích thước cửa sổ

    # Tạo socket UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((receiver_ip, receiver_port))

    print("Máy nhận đã sẵn sàng nhận dữ liệu...")
    
    # Nhận dữ liệu
    file_data = reliable_receive(sock, window_size)

    # Ghi dữ liệu nhận được vào tệp (hoặc in ra, tùy thuộc vào yêu cầu)
    print("Dữ liệu nhận được:", file_data.decode())

    # Đóng kết nối
    sock.close()
