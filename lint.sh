#!/bin/bash
isort -rc sv_mini_atlas
black sv_mini_atlas
flake8 sv_mini_atlas
