# NI-XNET CAN Telemetry Explorer

A desktop application for parsing, decoding, and visualizing CAN bus telemetry using IXXAT CSV logs and NI-XNET FIBEX XML databases.

# BEFORE READING: IN CASE YOU DON'T NEED TO KNOW HOW IT WORKS OR HOW TO DEBUG IT JUST USE THE ".\dist\IXXAT Plotter.exe" FILE



## Project Structure

* `main.py`: Main application entry point.
* `build_app.bat`: Build script for generating the standalone executable.
* `assets/`: Application UI assets (icon, logo).
* `src/`: Core source code containing the UI, log parser, and bit-unpacking engine.

## Environment Setup

Initialize and activate the virtual environment, then install the required dependencies:

Open in Terminal:
python -m venv venv
venv\Scripts\activate
pip install matplotlib pyinstaller

## Execution

With a venv activated run:

py .\main.py

### OR IF YOU WANT TO SEE DEBUG MSG

py .\main.py -d

## Build EXE

Run the  'build_exe.bat' script

