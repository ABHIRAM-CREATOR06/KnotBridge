# KnotBridge MVP architecture

```text
CLI / PowerShell wrapper
          |
          v
     Git process adapter
          |
   +------+------+
   |             |
 github       tangled
 remote       remote
```

KnotBridge deliberately uses ordinary Git remotes instead of provider-specific APIs for the MVP. Authentication remains with Git/SSH and the operating system. The tool runs pushes sequentially so it can report partial success and support targeted retries.

## Safety boundaries

- No shell command concatenation in the Python CLI.
- No private-key or token storage.
- No force pushes.
- No automatic branch deletion.
- No rollback claim across independent remotes.
- Ambiguous network results require status verification.
