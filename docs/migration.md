# Migration record

Date: November 9, 2026

Active project: `/Users/sasha/Documents/lumos`.

The specified old project `/Users/sasha/Documents/ChatGPT/Sub GHz Lamp on Home Assistant 2` was already absent at inspection. The two original Markdown files were recovered from the obvious sibling `/Users/sasha/Documents/ChatGPT/Sub GHz Lamp on Home Assistant`. No material was reconstructed. Following the user's reiterated cleanup instruction, the actual sibling project and its `.git` were removed after confirming that all non-Git files exactly matched the archived copies. Both old paths are now absent.

The removed Git repository had no commits or remotes. It contained one Codex checkpoint tree, an empty tree, and one blob that exactly matched the archived wiring notes. No unique file content was discarded.

The recovered files are preserved byte for byte in `docs/archive/`; those historical files intentionally retain old paths and status. The active wiring notes and plan were updated for Lumos and the supplied session context. All non-Git content found in the recovery source was preserved. Trash listing was denied by macOS; recovery succeeded from the sibling folder without requiring Trash access.

All twelve captures came from `/Users/sasha/Downloads/`. Their filenames and bytes were preserved, including duplicate recordings. Downloads originals remain untouched. SHA-256 values below were checked against the source files during copying and again after documentation updates; recovered Markdown files were also compared byte for byte immediately before removing the old project.

Lumos already contained its own `.git`, an unborn `main` branch (no local commits or refs), and `origin = https://github.com/sasha351/lumos.git`. Every regular file under that `.git` was snapshotted before the local migration and compared afterward, before staging or committing. The original Git configuration SHA-256 was `849a8f82a818ff329aad30ee16201827394cfb93ab7e943d1864299eed616430`. The local migration left Git metadata unchanged.

The user subsequently authorized a commit and push. A successful `git ls-remote --symref origin HEAD 'refs/heads/*'` returned no refs, establishing that the existing remote had no advertised HEAD or branches before publication. Publishing uses an ordinary commit and push to `main`, preserving the remote URL and setting upstream tracking. No force push, history replacement, or remote creation is authorized or needed.

## Preserved-file SHA-256 checksums

| Destination relative to Lumos | SHA-256 |
| --- | --- |
| `docs/archive/CC1101-ESP32-S3-wiring.md` | `86c232317c07c94f9a92bc3a778586116eec52d5103d19825256f2f182e995d8` |
| `docs/archive/2026-11-09-lamp-controller.md` | `e11a329d43d71ad821082a0f5bbd1de512e01a67a98dc454ee348dcf94925b52` |
| `captures/original/Read.sub` | `393301809c7313e65c245b5a3534572c887ad6d599d4e624b57f792d6fe16411` |
| `captures/original/Pwr.sub` | `9e599b5ed4c5d56e4d0abc4e4474c1fa7896150aaf518c63433f1b5385b9360a` |
| `captures/original/Nght.sub` | `ba50f9259311c15f5ab1ff72e6e56dceec92d55057741c898226ea25db3f0354` |
| `captures/original/Middl.sub` | `0b0f32b50b4e96dd39376a741b5c67361b8c908c29ab0030fb1a920bae84c28a` |
| `captures/original/Lei.sub` | `d620e1bb1bc2d02aeb7f89140ee367c90c768be93316ee08f8db2fa2cb634625` |
| `captures/original/Cool.sub` | `d95cf87d7e2d3f22bd582e840d919b43bbabbccce1fad5bbbfa02e66138801ff` |
| `captures/original/Bup.sub` | `6bc16b3cfaf067f7d3fafee1f289a125ac3e3cad2dc3b568ccec779a8af5e2ba` |
| `captures/original/Bdwn.sub` | `5d674537823a922d317b8538b763ace332fbcaa0f56096a7903969609f65d1fe` |
| `captures/original/SubGHz_2026-10-23_14,53,23.sub` | `7842b3058e0e5aa2df19c17ee291f0a51409d1aec199201f94aa826d0f1a56e1` |
| `captures/original/SubGHz_2026-10-23_14,53,06.sub` | `c06f4e1104f8e1820e09c1655d8147bbe82eb288ef62a969c0b6aff00bbc9521` |
| `captures/original/SubGHz_2026-10-23_14,52,52.sub` | `d620e1bb1bc2d02aeb7f89140ee367c90c768be93316ee08f8db2fa2cb634625` |
| `captures/original/SubGHz_2026-10-23_14,48,37.sub` | `9e599b5ed4c5d56e4d0abc4e4474c1fa7896150aaf518c63433f1b5385b9360a` |

## Scope of verification

Verified exact source/archive equality before cleanup, all twelve source/capture pairs, capture metadata and known duplicate pairs, Markdown links, ignore rules, unchanged Lumos Git metadata and remote, and absence of both old project directories. Pulse decoding, physical wiring, ESP identity, firmware, radio tests, and Home Assistant operation are outside this migration.
