UIFILES := $(wildcard activate/resources/ui/*.ui)
PYFILES = $(patsubst activate/resources/ui/%.ui, activate/app/ui/%.py, $(UIFILES))

.PHONY: all build install ui

all: build

build: ui
	python3 setup.py build

install:
	pip install .

ui: $(PYFILES)

activate/app/ui/%.py: activate/resources/ui/%.ui
	pyuic5 $< -o $@
