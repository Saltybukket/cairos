# CAIROS Safety Model

CAIROS plans first and executes only through `cairos run ...`.

Risk levels:

- `low`: read-only commands or narrow structured writes.
- `medium`: broad writes, cleanup, git index changes, package generation.
- `high`: force pushes, downloaded scripts piped to shells, recursive ownership changes.
- `critical`: destructive disk or root operations. These are blocked.

Examples blocked as critical:

```bash
rm -rf /
sudo rm -rf /tmp/example
mkfs.ext4 /dev/sda
dd if=image.iso of=/dev/sda
```

High-risk examples require the explicit high-risk phrase:

```bash
git push --force
curl https://example.com/install.sh | bash
git reset --hard
```

Trust tools:

```bash
cairos check rm -rf /
cairos --dry-run create python project demo
cairos preview create cpp header Player
cairos diff create cpp header Player
```
