# Third-party sources

`src/movie_agent/prompts.py` adapts the story expansion, scene segmentation,
filmable-action and character-motivation methods from
[ViMax agents/screenwriter.py](https://github.com/HKUDS/ViMax/blob/05a48943878312d88fe5a016c12a9654940ecc43/agents/screenwriter.py).
Version: `05a48943878312d88fe5a016c12a9654940ecc43`. License: [MIT](./ViMax-LICENSE.txt).
The prompts were shortened, translated and changed to support user review,
open narrative structures, immutable film versions and AgentScope tools.
The original LangChain calls, global pipeline and Web runtime are not included.

Reference selection and camera/scene continuity organization follow the same
version's [storyboard artist](https://github.com/HKUDS/ViMax/blob/05a48943878312d88fe5a016c12a9654940ecc43/agents/storyboard_artist.py),
[reference selector](https://github.com/HKUDS/ViMax/blob/05a48943878312d88fe5a016c12a9654940ecc43/agents/reference_image_selector.py),
[character extractor](https://github.com/HKUDS/ViMax/blob/05a48943878312d88fe5a016c12a9654940ecc43/agents/character_extractor.py)
and [scene extractor](https://github.com/HKUDS/ViMax/blob/05a48943878312d88fe5a016c12a9654940ecc43/agents/scene_extractor.py).
The adapted prompts separate static identity from changing state, first/last-frame
composition from motion, and select nonredundant references by view, scene and story state.
Their fixed scene/reference counts and LangChain runtime are omitted; actual provider
parameters are validated separately. This does not claim its entire production pipeline was reused.

AgentScope is a pinned dependency in `uv.lock`; its own package license remains
with that distribution. FFmpeg is downloaded as a local tool during setup from
Gyan's published Windows build, checksum verified, with the archive's license
and build configuration retained. These third-party notices do not select a
license for the movie-agent project itself.
