#!/bin/bash
set -e                                   # stop at the first error
git add story.json
git commit -m "New story: $(date +%F)"
git push
sha=$(git rev-parse HEAD)                # the commit we just pushed
sleep 15                                 # give GitHub a moment to start the run
id=$(gh run list --workflow render.yml --commit "$sha" --json databaseId -q '.[0].databaseId')
gh run watch "$id" --exit-status         # wait until it finishes (or fails)
num=$(gh run view "$id" --json number -q .number)
gh release download "video-$num" -D "videos/$num" --clobber
echo "Done: videos/$num/video.mp4"
