# Local assets

- `models/pose_landmarker_lite.task`: installed by `scripts/download_model.py` from the official versioned Google MediaPipe model URL. See the script for its checksum and the upstream model documentation linked in the root README. Model binaries are excluded from Git; run setup once before going offline.
- `pumpkins/` and `bats/`: extension points for optional assets.
- `overlays/heads.png`, `visitors.png`, `details.png`, and `visitors-blink.png`: bundled 1536×1024 transparent sprite packs generated with the built-in image generation tool on 2026-09-17. The exact prompts are in `overlays/generation-prompts.txt`. `app/renderer/sprites.py` loads the appropriate regions once; generated source files are preserved. Friendly character faces, skull, bat, ghost, flying witch, spider, zombie hand, black cat, gravestone, dirt and moon share one visual style. Original code-drawn factories remain available as missing-asset fallbacks.
- `backgrounds/haunted-house-standby.png`: festive waiting-screen artwork with the title “The Dance Floor Awaits”, created with the built-in image generation tool on 2026-09-17. The exact prompt is saved beside it in `haunted-house-standby-prompt.txt`. Bundled locally for offline runtime.
- `sounds/`: add locally licensed `scream.wav`, `lightning.wav`, `ghost.wav`, or `.ogg` equivalents. Missing files are intentionally silent.

No third-party artwork or cue recordings are bundled. No webcam images are recorded.
