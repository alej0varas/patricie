# Upgrade all packages. After running this script edit
# requirements.txt and remove all lines from the second time arcade
# appears until the end of the file.
pip list --outdated | cut -d' ' -f 1 | tail --lines=+3 | xargs -n1 pip install --upgrade
pip freeze -r requirements.txt >> requirements.txt
