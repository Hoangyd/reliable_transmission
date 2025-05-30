import argparse
import socket
import sys
from utils import PacketHeader, compute_checksum

def parse_packet(packet_bytes):
    # TODO: tách gói tin thành phần tiêu đề và thông điệp
    pkt_header = PacketHeader(packet_bytes[:16])
    msg = packet_bytes[16:16 + pkt_header.length]

    return pkt_header, msg

def is_valid_checksum(pkt_header, msg):
    # TODO: kiểm tra checksum có hợp lệ không
    received_checksum = pkt_header.checksum
    pkt_header.checksum = 0
    return received_checksum == compute_checksum(pkt_header / msg)

def send_ack(s, seq_num, address):
    # TODO: gửi gói tin ACK với số thứ tự chỉ định đến địa chỉ phù hợp
    ack_header = PacketHeader(type=3, seq_num=seq_num, length=0, checksum=0)
    ack_header.checksum = compute_checksum(ack_header / b"")
    s.sendto(bytes(ack_header / b""), address)
    #print(f"==================================== Sending ACK with seq = {seq_num}")

def receiver(receiver_ip, receiver_port, window_size):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((receiver_ip, receiver_port))

    expected_seq = 0
    buffer = {}  # Bộ đệm cho các gói nhận sai thứ tự
    received_data = []  # Danh sách lưu dữ liệu nhận đúng thứ tự

    while True:
        packet, address = s.recvfrom(2048)
        pkt_header, msg = parse_packet(packet)

        if not is_valid_checksum(pkt_header, msg):
            continue

        if pkt_header.type == 0:  # Gói START
            expected_seq = 1
            send_ack(s, expected_seq, address)
            continue

        if pkt_header.type == 2:  # Gói DATA
            seq = pkt_header.seq_num

            # Bỏ qua các gói nằm ngoài cửa sổ nhận
            if seq >= expected_seq + window_size:
                continue

            # Lưu các gói nhận sai thứ tự vào bộ đệm và chờ xử lý
            if seq >= expected_seq:
                if seq not in buffer:
                    buffer[seq] = msg

            # Nếu gói mong đợi có trong bộ đệm
            while expected_seq in buffer:
                received_data.append(buffer.pop(expected_seq))
                expected_seq += 1

            # Gửi ACK tích lũy (ACK cho gói có số thứ tự mong đợi tiếp theo)
            send_ack(s, expected_seq, address)

        elif pkt_header.type == 1:  # Gói END
            expected_seq += 1
            send_ack(s, expected_seq, address)
            break

    # In ra toàn bộ dữ liệu đã nhận
    sys.stdout.buffer.write(b"".join(received_data))
    sys.stdout.flush()  


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("receiver_ip", help="The IP address of the host that receiver is running on")
    parser.add_argument("receiver_port", type=int, help="The port number on which receiver is listening")
    parser.add_argument("window_size", type=int, help="Maximum number of outstanding packets")
    args = parser.parse_args()

    receiver(args.receiver_ip, args.receiver_port, args.window_size)

if __name__ == "__main__":
    main()
