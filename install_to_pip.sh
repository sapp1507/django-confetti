python -m pip install build twine
python -m build
twine check dist/*

twine upload -r testpypi dist/*
# затем в чистой venv проверить установку:
python -m venv .venv && . .venv/bin/activate
pip install -i https://test.pypi.org/simple/ django-confetti==0.3.1
python -c "import confetti; print(confetti.__version__)"

twine upload dist/*
