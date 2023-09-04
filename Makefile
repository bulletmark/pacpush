NAME = $(shell basename $(CURDIR))
PYNAME = $(subst -,_,$(NAME))

check:
	ruff .
	flake8 .
	vermin -vv --exclude importlib.resources.files --no-tips -i */*.py

doc:
	update-readme-usage -a

clean:
	@rm -vrf *.egg-info .venv/ build/ dist/ __pycache__/
