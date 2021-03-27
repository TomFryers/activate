UIFILES := $(wildcard activate/resources/ui/*.ui)
PYFILES = $(patsubst activate/resources/ui/%.ui, activate/app/ui/%.py, $(UIFILES))

.PHONY: all build install clean ui

all: build

build: ui
	python3 setup.py sdist bdist_wheel

install:
	python3 -m pip install .

clean:
	python3 setup.py clean
	rm -r dist/ *.egg-info

ui: $(PYFILES)

activate/app/ui/%.py: activate/resources/ui/%.ui
	pyuic5 $< -o $@
