# pp1 — all-in-one voice-assistant backend

Self-hosted **speech-to-text + text-to-speech + brain server** for the
[PP Friend](https://github.com/thautwarm/pp-friend) voice assistant, wired together
and started with a single compose file.

```
 phone / agent                         ┌──────────────────────────────┐
   │  MessagePack + Ogg Opus           │  brain  (pp-brain-server)    │
   └──────────────────────────────────▶│  :8787                       │
                                       │   ├─ STT ─▶ asr   :8082      │
                                       │   ├─ TTS ─▶ tts   :6677      │
                                       │   └─ revise ▶ chat :8088     │
                                       └──────────────────────────────┘
```

| Component | What it is | VRAM |
| --- | --- | --- |
| **asr** | [Qwen3-ASR-1.7B](https://huggingface.co/Qwen/Qwen3-ASR-1.7B), OpenAI-compatible `/v1/audio/transcriptions` | ~5 GB |
| **tts** | [moss-tts-windowed](https://github.com/thautwarm/moss-tts-windowed) — MOSS-TTS 8B, resident, streaming Ogg/Opus | ~6.8 GB per daemon |
| **brains** | [pp-brain-server](https://github.com/thautwarm/pp-brain-server) — the Brain API the app talks to | — |
| **chat** *(optional)* | llama.cpp + Qwen3-1.7B Q4, used only for the brain's background "was the transcription right?" pass | ~2 GB |

---

## Requirements

| | |
| --- | --- |
| GPU | NVIDIA, ≥ 16 GB for the full stack (STT + TTS + chat) |
| Disk | ~35 GB (weights ~14 GB, images ~20 GB) |
| Host | Linux (or WSL2). Docker + [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) |
| Build | `bash` is used for the TTS build (present on Linux/macOS/WSL) |

The TTS service keeps one model resident per daemon: one daemon is enough for
real-time speech (RTF ≈ 0.2); two or three let several conversations synthesize
in parallel. `onboard` picks a count from the VRAM it finds.

## Quick start

```bash
git clone https://github.com/thautwarm/pp1
cd pp1

# 1. check the machine, download weights, build images, write .env
./pp1-setup-linux-x64 all
#    (no prebuilt binary? use: deno run -A scripts/onboard.ts all)

# 2. start STT + TTS + brain (+ the optional chat model)
docker compose up -d

# 3. verify end to end
./pp1-setup-linux-x64 smoke
```

`all` is idempotent: downloads are checksum-verified and skipped when complete,
`.env` keeps edits you made, image builds are cached.

Then create a profile in the PP Friend app:

* **Brain URL** — `http://<host>:8787`
* **Brain ID** — `hw` (any name; the server creates it on first use)

Point an agent at the same brain ID and the loop is complete: speak → transcript →
agent text → speech.

## Ports

| Service | Host port | Endpoint |
| --- | --- | --- |
| brain | 8787 | `POST /human-to-brain`, `/brain-to-human`, `/agent-to-brain`, `/brain-to-agent` |
| TTS | 6677 | `GET /health`, `POST /v1/audio/speech/stream` |
| ASR | 8082 | `GET /health`, `POST /v1/audio/transcriptions` |
| chat | 8088 | OpenAI-compatible `/v1/chat/completions` (profile `local-chat`) |

Ports live in `.env` (`PP1_*_PORT`); the compose network addresses used by the
brain are `http://asr:8082/v1` and `http://tts:8080/v1`.

## Commands

```
pp1-setup <command>          # or: deno run -A scripts/onboard.ts <command>

  all        doctor + fetch + env + build (default)
  doctor     docker / GPU / compute cap / disk checks
  fetch      clone pinned components, download weights
  env        write/update .env
  build      build asr / tts / brain images
  up         docker compose up -d
  down       docker compose down
  status     container state + HTTP probes
  smoke      end-to-end: TTS, STT, brain, chat
```

Useful flags: `--hf-endpoint https://hf-mirror.com` (or set `HF_ENDPOINT`),
`--source modelscope` for the ASR weights, `--chat-base-url …` to use your own
chat model instead of the bundled one, `--daemons N` to change TTS parallelism.

Prebuilt `pp1-setup-{linux,darwin,windows}-{x64,arm64}` binaries are attached to
[releases](https://github.com/thautwarm/pp1/releases). They are self-contained —
run them in the repository root.

## Voices

`male-fun` is a synthetic voice (Qwen TTS voice design), included as a demo.
Add your own reference audio:

```bash
curl -X POST http://127.0.0.1:6677/api/v1/voices \
  -F voice=alice -F file=@alice.wav
```

The service stores `voices/alice.wav` plus a precomputed `.codes.bin`. Use it with
`{"voice": "alice"}` on the stream endpoint, or change the default in `.env`
(`TTS_VOICE`).

## Configuration

Everything is in `.env` (see [.env.example](.env.example)). The ones you are most
likely to touch:

| Key | Meaning |
| --- | --- |
| `MOSS_DAEMONS` | resident TTS workers; each ≈ 6.8 GB VRAM |
| `MOSS_LANGUAGE` | TTS language hint (`zh`, `en`, …) |
| `TTS_VOICE` | default voice for messages without `x-brain-voice` |
| `MIGHT_CHAT_API_BASE_URL` / `_KEY` / `_MODEL` | external OpenAI-compatible chat endpoint |
| `MIGHT_BRAINS_TOKEN` | bearer token for the brain API; empty = auth off |
| `MIGHT_LOG_LLM` | `1` = dump LLM requests/responses to `logs/brains/` (contains conversation text) |

To use an external chat model instead of the bundled one:

```bash
pp1-setup env --chat-base-url https://api.example.com/v1 \
              --chat-api-key sk-... --chat-model some-model
pp1-setup up
```

## Troubleshooting

**`CUDA error: no kernel image is available for execution on the device`** — the
daemon was compiled for another architecture. `onboard` reads
`nvidia-smi --query-gpu=compute_cap` and passes `CUDA_ARCH`; re-run
`pp1-setup build` if you changed GPUs.

**Downloads are slow** — use a HuggingFace mirror
(`--hf-endpoint https://hf-mirror.com`) or `--source modelscope` (fast in CN).
ASR weights are also on ModelScope under the same id.

**The first TTS request takes 2–3 s** — that is the CUDA graph build per daemon;
subsequent requests are first-byte ≈ 0.6 s.

**Ports are taken** — `--tts-port 16677` etc. (also updates `.env`).

**No NVIDIA GPU** — the stack targets CUDA. macOS builds of `pp1-setup` can fetch
and configure, but TTS/ASR need a Linux GPU host.

## Layout

```
docker-compose.yml        four services, one network
docker/asr/               Qwen3-ASR server (OpenAI-compatible)
scripts/onboard.ts        the setup tool (Deno, single file)
voices/                   demo voice + your references
models/                   downloaded weights (gitignored)
.components/              pinned checkouts of tts / brain (gitignored)
```

## Security

The brain is a personal/home service: state is in memory, there is no tenancy or
hardening. Run it on a trusted LAN or behind a VPN; keep the ports off the public
internet. `MIGHT_BRAINS_TOKEN` adds a bearer check to all four endpoints.

## Licenses

pp1 itself is MIT. The container images and weights carry their own licenses:
Qwen3-ASR and Qwen3-1.7B are Apache-2.0; MOSS-TTS weights and
moss-tts-windowed are covered by their upstream repositories — check them before
commercial use.
