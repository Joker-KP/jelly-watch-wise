#!/bin/bash


docker build . --platform linux/amd64 -t macjoker/jelly-watch-wise:amd64 --push
docker build . --platform linux/arm64 -t macjoker/jelly-watch-wise:arm64 --push
docker buildx build --platform linux/amd64,linux/arm64 -t macjoker/jelly-watch-wise:multi --push .

