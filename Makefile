NAME = $(shell basename $(CURDIR))
PYNAME = $(subst -,_,$(NAME))

check:
	ruff check .
	vermin -vv --exclude importlib.metadata \
	       	--no-tips -i *.py

build:
	rm -rf dist
	python3 -m build

upload: build
	twine3 upload dist/*

doc:
	update-readme-usage

clean:
	@rm -vrf *.egg-info .venv/ build/ dist/ __pycache__/
