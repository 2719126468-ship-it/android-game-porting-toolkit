.PHONY: test compile help

test:
	python -m unittest discover -s tests -v

compile:
	python -m compileall -q src tests

help:
	python -m agpt --help
