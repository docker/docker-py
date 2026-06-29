# Benchmarks

Small, self-contained scripts that demonstrate the behaviour of changes in
this repository. They do not require a running Docker daemon.

## `stream_leak.py`

Reproduces the streaming socket/file-descriptor leak from
[#2766](https://github.com/docker/docker-py/issues/2766) and shows that the
`try/finally` cleanup added to the streaming generators fixes it.

It starts a local HTTP server that streams a chunked response indefinitely
(mimicking `container.logs(stream=True, follow=True)`), then repeatedly opens a
stream, reads a single chunk, and abandons the iterator — exactly the pattern
that leaked before this change. After each batch it counts the process's open
TCP connections.

```console
$ python benchmarks/stream_leak.py --iterations 200
opening 200 streams, reading one chunk, then stopping each early

impl       streams  sockets leaked   ESTABLISHED conns
------------------------------------------------------
old            200             200                 200
fixed          200               0                   0

PASS: old leaks all 200 sockets on early stop; fixed closes every one.
```

Requires `psutil` (already a transitive test dependency). The `old` row uses a
generator with no cleanup (the pre-fix behaviour); the `fixed` row uses the same
generator wrapped in `try/finally: response.close()`, mirroring
`APIClient._stream_raw_result`. `sockets leaked` is counted client-side
(`http.client` responses still open); `ESTABLISHED conns` is the corroborating
count from `psutil`.
