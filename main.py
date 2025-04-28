def ma_hoa_caesar(text, shift=3):
    ket_qua = ""
    for char in text:
        if char.isalpha():
            offset = 65 if char.isupper() else 97
            ket_qua += chr((ord(char) - offset + shift) % 26 + offset)
 