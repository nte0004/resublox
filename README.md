LibreOffice Required:
- MacOS: `brew install libreoffice`
- Linux: `apt install libreoffice`

*Windows not supported.*

mkdir models and use modelHelper.py to download a model
set the model in src/core.py

Kinda useful right now.

```
# make virtual environment first

pip install -r requirements.txt

python3 resublox.py -h

python3 resublox.py template.example.yaml "the content you want to optimize the resume for"
```
