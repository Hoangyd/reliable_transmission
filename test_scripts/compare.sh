#!/bin/bash

# Kiểm tra xem 2 file có giống nhau không
if cmp -s "$1" "$2"
then
    # Nếu giống nhau thì in thông báo thành công
    echo "SUCCESS: Message received matches message sent!"
else
    # Nếu khác nhau, in thông báo lỗi và hiển thị sự khác biệt
    echo "ERROR: Message received does NOT match message sent!"
    diff "$1" "$2"  # So sánh chi tiết sự khác biệt
fi