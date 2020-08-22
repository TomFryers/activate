UIFILES := $(wildcard resources/ui/*.ui)
PYFILES = $(patsubst resources/ui/%.ui, activate/app/ui/%.py, $(UIFILES))

.PHONY: ui
ui: $(PYFILES)

activate/app/ui/%.py: resources/ui/%.ui
	pyuic5 $< -o $@
