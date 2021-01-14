# UnpackDarkSoulsExtended

Unpacks **Dark Souls: Prepare To Die Edition** archive files for modding. Works with Steam and GFWL versions. The code is mainly based on a heavily modified and refactored version of [UnpackDarkSoulsForModding](https://github.com/HotPocketRemix/UnpackDarkSoulsForModding).

## Requirements
* Python 3.8+

## Building
git clone https://github.com/michi-no-robotto/UnpackDarkSoulsExtended.git
cd UnpackDarkSoulsExtended
pip install -r requirements.txt
pyinstaller main.py --name UnpackDarkSoulsExtended --icon favicon.ico --onefile

## Credits
* Based on: [UnpackDarkSoulsForModding](https://github.com/HotPocketRemix/UnpackDarkSoulsForModding) by [HotPocketRemix](https://github.com/HotPocketRemix)
* Some ideas borrowed from: [SoulsFormats](https://github.com/Meowmaritus/SoulsFormats) by [Meowmaritus](https://github.com/Meowmaritus)