# The Life of Jesus: an animated timeline

A narrated motion-graphics video, about 100 seconds, made only with open-source tools and rendered in the cloud on
GitHub's free runners.

| Part | Tool | License |
|---|---|---|
| Animation | [HyperFrames](https://github.com/heygen-com/hyperframes) (HTML + [GSAP](https://gsap.com)) | Apache 2.0 |
| Voice | [Kokoro](https://github.com/thewh1teagle/kokoro-onnx), voice `af_heart` | Apache 2.0 |
| Music | Generated with ffmpeg | n/a |
| Fonts | Cinzel, Cormorant Garamond | SIL OFL |
| Scripture | King James Version | public domain |

## Make the video

Push to `main` (or open **Actions → render → Run workflow**). When the run finishes, download `life-of-jesus` from
the run's **Artifacts**: it holds the MP4 and a few preview frames.

## Change it

Everything you see and hear comes from `script.json`: each scene has a year, a title, a KJV verse, a line icon
(`star house temple waves mountains fish sun gate cup cross sunrise cloud`) and the narration. Each scene lasts as
long as its narration, so timing never needs fixing by hand. The voice and its speed are at the top of `build.py`.

Check your edit before pushing (no voice or rendering needed):

```
python test_build.py
```
