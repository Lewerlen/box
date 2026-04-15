#!/bin/bash
set -e

pip install -r requirements.txt -q

cd frontend && npm install --legacy-peer-deps && cd ..
