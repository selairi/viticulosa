all: webcam.py

run: webcam.py
	python3 webcam.py

webcam.py: src/webcam.py src/main.glade
	cd src && python3 build.py