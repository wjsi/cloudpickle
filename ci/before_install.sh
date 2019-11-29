#!/bin/bash

# if python version is not PyPY, then install miniconda
if [[ $TRAVIS_PYTHON_VERSION != 'pypy'* && $TRAVIS_PYTHON_VERSION != "3.7" ]]
then

    # Escape standard Travis virtualenv
    deactivate
    # See: http://conda.pydata.org/docs/travis.html
    wget http://repo.continuum.io/miniconda/Miniconda3-3.6.0-Linux-x86_64.sh -O miniconda.sh
    bash miniconda.sh -b -p $HOME/miniconda
    export PATH="$HOME/miniconda/bin:$PATH"
    hash -r
    conda config --set always_yes yes --set changeps1 no
    conda update -q conda
    conda info -a
    conda create -q -n testenv python=$TRAVIS_PYTHON_VERSION numpy scipy pip
    if [[ $TRAVIS_PYTHON_VERSION == *'2.7'* ]]
    then
        conda create -q -n py26 python=2.6 numpy scipy pip pytest six
        export PY26_EXECUTABLE="$HOME/miniconda/envs/py26/bin/python"
        conda create -q -n py37 python=3.7 numpy scipy pip pytest six
        export PY37_EXECUTABLE="$HOME/miniconda/envs/py37/bin/python"
    fi
fi
