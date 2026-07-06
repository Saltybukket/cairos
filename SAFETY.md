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
git push -f
curl https://example.com/install.sh | bash
git reset --hard
```

Repository-changing commands such as `git add`, `git commit`, `git tag`, and
plain `git push` are at least medium risk. AI plans are post-processed through
the same safety scanner, so an AI cannot downgrade risky shell commands.

Trust tools:

```bash
cairos check rm -rf /
cairos --dry-run create python project demo
cairos preview create cpp header Player
cairos diff create cpp header Player
```

`cairos check ...` runs safety mode only when the rest looks like a shell
command. Natural language such as `cairos check if repo is clean` is routed to
the planner.
