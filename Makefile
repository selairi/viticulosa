all: viticulosa.py

run: webcam.py
	python3 viticulosa.py

viticulosa.py: src/webcam.py src/main.glade
	cd src && python3 build.py
	chmod +x viticulosa.py