#!/bin/bash
IRONPYTHON_DOWNLOAD_URL="https://github.com/IronLanguages/main/releases/download/ipy-2.7.4/IronPython-2.7.4.zip"
IRONPYTHON_DIR="IronPython-2.7.4"

if [[ ! $(which mono) ]]; then
  echo "Mono seems not installed.  You can download it from the Mono website:"
  echo http://www.mono-project.com/
  exit 1
fi
if [[ ! $(which curl) ]]; then
  echo "cURL seems not installed.  You can download it from the cURL website:"
  echo http://curl.haxx.se/
  exit 1
fi
if [[ ! $(which hg) ]]; then
  echo "Mercurial seems not installed.  You can download it from the website:"
  echo http://mercurial.selenic.com/
  exit 1
fi

if [[ ! -d .ipy-env ]]; then
  mkdir .ipy-env/
fi
pushd .ipy-env/
if [[ ! -f "$IRONPYTHON_DIR".zip ]]; then
  curl -L -O $IRONPYTHON_DOWNLOAD_URL
fi
if [[ ! -d $IRONPYTHON_DIR ]]; then
  unzip "$IRONPYTHON_DIR".zip
fi
if [[ -d py ]]; then
  pushd py/
  hg pull -u
  popd
else
  hg clone https://bitbucket.org/dahlia/py-ironpython py
fi
if [[ -d pytest ]]; then
  pushd pytest/
  hg pull -u
  popd
else
  hg clone https://bitbucket.org/dahlia/pytest-ironpython pytest
fi
popd

IRONPYTHONPATH=.ipy-env/py/:.ipy-env/pytest/ \
mono .ipy-env/$IRONPYTHON_DIR/ipy.exe \
     -X:ExceptionDetail \
     -X:ShowClrExceptions \
     -X:Frames \
     .ipy-env/pytest/pytest.py -v \
                               -s \
                               --assert=plain \
                               $@ \
                               tests
exit $?
