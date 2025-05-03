import argparse
import socket
import sys
from utils import PacketHeader, compute_checksum

def parse_packet(packet_bytes):
    # Tách gói tin thành phần tiêu đề và thông điệp
    pkt_header = PacketHeader(packet_bytes[:16])
    msg = packet_bytes[16:16 + pkt_header.length]

    return pkt_header, msg

def is_valid_checksum(pkt_header, msg):
    # Kiểm tra tính hợp lệ của checksum
    received_checksum = pkt_header.checksum
    pkt_header.checksum = 0
    return received_checksum == compute_checksum(pkt_header / msg)

def send_ack(s, seq_num, address):
    # Gửi gói tin xác nhận với số thứ tự cụ thể đến địa chỉ thích hợp
    ack_header = PacketHeader(type=3, seq_num=seq_num, length=0, checksum=0)
    ack_header.checksum = compute_checksum(ack_header / b"")
    s.sendto(bytes(ack_header / b""), address)
    #print(f"==================================== Đã gửi ACK với seq = {seq_num}")

def receiver(receiver_ip, receiver_port, window_size):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((receiver_ip, receiver_port))

    expected_seq = 0
    buffer = {}  # Bộ đệm cho các gói tin nhận sai thứ tự
    received_data = []  # Danh sách lưu trữ dữ liệu nhận đúng thứ tự

    while True:
        packet, address = s.recvfrom(2048)
        pkt_header, msg = parse_packet(packet)

        if not is_valid_checksum(pkt_header, msg):
            #===========print("Checksum không khớp. Bỏ qua gói tin.")
            continue

        if pkt_header.type == 0:  # GÓI TIN BẮT ĐẦU
            #===========print("\nĐã nhận gói START.")
            expected_seq = 1
            send_ack(s, expected_seq, address)
            continue

        if pkt_header.type == 2:  # GÓI TIN DỮ LIỆU
            seq = pkt_header.seq_num

            # Bỏ qua các gói ngoài cửa sổ nhận
            if seq >= expected_seq + window_size:
                #===========print(f"Gói có seq = {seq} nằm ngoài cửa sổ. Bỏ qua.")
                continue

            # Đệm các gói nhận sai thứ tự
            if seq >= expected_seq:
                if seq not in buffer:
                    buffer[seq] = msg
                    #===========print(f"Đã đệm gói tin có seq = {seq}")

            # Nếu gói đúng thứ tự đã đến
            while expected_seq in buffer:
                received_data.append(buffer.pop(expected_seq))
                expected_seq += 1

            # Gửi ACK tích lũy (gói tin tiếp theo mong đợi)
            send_ack(s, expected_seq, address)

        elif pkt_header.type == 1:  # GÓI TIN KẾT THÚC
            #===========print("Đã nhận gói END.")
            expected_seq += 1
            send_ack(s, expected_seq, address)
            break

    # Xuất toàn bộ dữ liệu đã thu thập được
    sys.stdout.buffer.write(b"".join(received_data))
    sys.stdout.flush()  

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("receiver_ip", help="Địa chỉ IP của máy chạy chương trình nhận")
    parser.add_argument("receiver_port", type=int, help="Cổng mà trình nhận đang lắng nghe")
    parser.add_argument("window_size", type=int, help="Số gói tin có thể nhận chưa xác nhận tối đa")
    args = parser.parse_args()

    receiver(args.receiver_ip, args.receiver_port, args.window_size)

if __name__ == "__main__":
    main()
