# pp1 voices

Voice cloning references for the TTS service. Layout (same as
[moss-tts-windowed](https://github.com/thautwarm/moss-tts-windowed)):

```
<id>.wav                        # 24 kHz / mono / 16-bit PCM
<id>.<sha256(wav)[:8]>.codes.bin  # precomputed reference codes
```

`male-fun` is a **synthetic** voice produced with Qwen TTS voice design — it is not a
recording of a real person and is redistributed here as a ready-to-use demo voice.

Add your own voice (any format, converted to 24 kHz mono by the TTS image):

```bash
curl -X POST http://127.0.0.1:6677/api/v1/voices \
  -F voice=alice -F file=@ref/alice.wav
```

or drop `<id>.wav` into this directory and call the synthesis endpoint — the service
computes the missing `.codes.bin` on first use (a few seconds, CPU).
