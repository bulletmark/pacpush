NAME = $(shell basename $(CURDIR))
PYNAME = $(subst -,_,$(NAME))

all:
	@echo "Type sudo make install|uninstall"
	@echo "or make check|clean"

install:
	pip3 install -U --root-user-action=ignore .

uninstall:
	pip3 uninstall --root-user-action=ignore $(NAME)

check:
	flake8 $(PYNAME).py setup.py
	vermin --no-tips -i $(PYNAME).py setup.py
	python3 setup.py check

clean:
	@rm -vrf *.egg-info build/ dist/ __pycache__/
