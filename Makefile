UIFILES := $(wildcard activate/resources/ui/*.ui)
PYFILES = $(patsubst activate/resources/ui/%.ui, activate/app/ui/%.py, $(UIFILES))

.PHONY: ui
ui: $(PYFILES)

activate/app/ui/%.py: activate/resources/ui/%.ui
	pyuic5 $< -o $@
