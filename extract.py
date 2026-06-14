from PyInstaller.archive.readers import CArchiveReader

archive = CArchiveReader(r"E:\workspace\GameLauncher_v2\GameLauncher.exe")
try:
    data = archive.extract('main')
    with open(r'E:\workspace\GameLauncher_v2\extracted_main.pyc', 'wb') as f:
        f.write(data)
    print('Extracted successfully! Size:', len(data))
except Exception as e:
    print('Error:', e)
