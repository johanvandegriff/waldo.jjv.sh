#!/bin/bash
source `dirname $0`/.venv/bin/activate
printer=`ls /dev/usb/lp*`
sudo chmod 777 "$printer"
export BROTHER_QL_MODEL=QL-800
export BROTHER_QL_PRINTER=file://"$printer"
brother_ql print -l 62 --red $@
