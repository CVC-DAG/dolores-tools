#!/bin/bash

ROOT_PATH="$1/SET05-12/CVC.03"

mv "$ROOT_PATH"/CVC.S07.P04/MUSESCORE/XAC_ACAN_SMIAu63_099.010.mscz "$ROOT_PATH"/CVC.S07.P04/MUSESCORE/XAC_ACAN_SMIAu63_099.10.mscz

# Ensure everything went well
python3 ../validation_tools/validate.py "$ROOT_PATH"