call "scripts\activate"
@echo on
pyinstaller --noconfirm --log-level=WARN ^
    --onefile --nowindow ^
    --add-data="config.json;." ^
    --add-data="logging.json;." ^
    --icon=icon.ico ^
    bars_downloader.py
copy config.json "dist\config.json"
copy logging.json "dist\logging.json"
copy README.md "dist\README.md"

rem pip freeze > requirements.txt
rem pip wheel -w wheels/ -r requirements.txt --pre
