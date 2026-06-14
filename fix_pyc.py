import os

# Read the extracted data (missing header)
with open('extracted_main.pyc', 'rb') as f:
    body = f.read()

# Create a valid Python 3.11 pyc header
# magic: a7 0d 0d 0a
# null: 00 00 00 00
# timestamp: we can use zeros
# size: we can use zeros
header = bytes([
    0xa7, 0x0d, 0x0d, 0x0a,  # magic
    0x00, 0x00, 0x00, 0x00,  # bit field / null
    0x00, 0x00, 0x00, 0x00,  # timestamp (or hash) - can be zeros
    0x00, 0x00, 0x00, 0x00   # source size - can be zeros
])

with open('main_fixed.pyc', 'wb') as f:
    f.write(header + body)

print('Created main_fixed.pyc, size:', len(header + body))
