import argparse
import socket
import struct
import sys
import time




from utils import PacketHeader, compute_checksum


def split_message(message, max_packet_size):
     # TODO: Divide the message into chunks according to max_packet_size
    chunks = [message[i:i + max_packet_size] for i in range(0, len(message), max_packet_size)]
    return chunks


def create_packet(seq_num, data, packet_type):
    # TODO: Create packet
    if isinstance(data, str):
        data = data.encode()  #Convert data into bytes
    pkt_header = PacketHeader(type=packet_type, seq_num=seq_num, length=len(data))
    pkt_header.checksum = compute_checksum(pkt_header / data)
    return pkt_header / data #This helps combine package header and data to create a complete package


   
def wait_for_ack(sock, timeout=0.5):
    #TODO: Wait for the ACK from the receiver. If time's out, return None
    try:
        sock.settimeout(timeout)
        data, _ = sock.recvfrom(1024) #data: be received from socket; _: IP and port of the receiver
        ack_seq_num = struct.unpack("!I", data[4:8])[0] #unpack data and use [0] to take ack_seq_num
        return ack_seq_num
    except socket.timeout:
        print("Timeout waiting for ACK.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def send_control_packet(s, seq_num, receiver_ip, receiver_port, packet_type, data, label, retry_count=0):
    """Send START/END control packet and wait for ACK (retry max 5 times if packet_type == 0)."""
    packet = create_packet(seq_num, data, packet_type=packet_type)
    s.sendto(bytes(packet), (receiver_ip, receiver_port))


    print(f"Sending {label} packet with seq = {seq_num}, waiting for ACK (max 500ms)...")
    ack = wait_for_ack(s, timeout=0.5)


    if ack is not None:
        print(f"ACK received for {label} packet: {ack}")
    else:
        print(f"No ACK for {label} packet. Retry count = {retry_count}")
        if packet_type == 1 and retry_count < 5:
            send_control_packet(s, seq_num, receiver_ip, receiver_port, packet_type, data, label, retry_count + 1)
        elif packet_type == 0 and retry_count < 5:
            send_control_packet(s, seq_num, receiver_ip, receiver_port, packet_type, data, label, retry_count + 1)
           


def sender(receiver_ip, receiver_port, window_size):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Gửi START packet
    send_control_packet(sock, 0, receiver_ip, receiver_port, packet_type=0, data="START", label="START")

    message = sys.stdin.read()
    chunks = split_message(message, max_packet_size=1472)

    # Khởi tạo trạng thái từng gói
    packet_states = {
        seq + 1: {
            "acked": False,
            "data": chunk
        }
        for seq, chunk in enumerate(chunks)
    }

   # total_packets = len(packet_states)
    base_seq = 1

    while not all(p["acked"] for p in packet_states.values()):
        # Gửi các gói trong cửa sổ nếu chưa
        for seq in range(base_seq, base_seq + window_size):
            if seq in packet_states:
                state = packet_states[seq]
                if not state["acked"]:  # Chỉ gửi nếu chưa nhận được ACK
                        pkt = create_packet(seq, state["data"], packet_type=2)
                        sock.sendto(bytes(pkt), (receiver_ip, receiver_port))
                        print(f"Sent packet seq={seq}")


        # Nhận ACKa
        timeout = 0.5
        start_time = time.time()
        while time.time() - start_time < timeout:
            ack = wait_for_ack(sock, timeout=0.05)  # Kiểm tra ACK mỗi 50ms
            if ack is not None:
                if ack in packet_states and not packet_states[ack]["acked"]:
                    packet_states[ack]["acked"] = True
                    print(f"ACK received: {ack}")
            else:
                break  # Nếu không còn ACK thì thoát khỏi vòng lặp nhận ACKs


        # Trượt cửa sổ nếu có thể
        while base_seq in packet_states and packet_states[base_seq]["acked"]:
            base_seq += 1
    # Gửi END packet
    send_control_packet(sock, base_seq, receiver_ip, receiver_port, packet_type=1, data="END", label="END")
    sock.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument( "receiver_ip", help="The IP address of the host that receiver is running on" )
    parser.add_argument("receiver_port", type=int, help="The port number on which receiver is listening")
    parser.add_argument(    "window_size", type=int, help="Maximum number of outstanding packets")
    args = parser.parse_args()


    sender(args.receiver_ip, args.receiver_port, args.window_size)


if __name__ == "__main__":
    main() 