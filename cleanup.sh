#!/bin/bash
yapf --in-place beastacademy_get_report.py
radon cc beastacademy_get_report.py
prospector beastacademy_get_report.py
flake8
