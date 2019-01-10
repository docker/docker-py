Handling multiplexed streams
============================

.. note::
      The following instruction assume you're interested in getting output from
      an ``exec`` command. These instruction are similarly applicable to the
      output of ``attach``.

First create a container that runs in the background:

>>> client = docker.from_env()
>>> container = client.containers.run(
...     'bfirsh/reticulate-splines', detach=True)

Prepare the command we are going to use. It prints "hello stdout"
in `stdout`, followed by "hello stderr" in `stderr`:

>>> cmd = '/bin/sh -c "echo hello stdout ; echo hello stderr >&2"'
We'll run this command with all four the combinations of ``stream``
and ``demux``.
With ``stream=False`` and ``demux=False``, the output is a string
that contains both the `stdout` and the `stderr` output:
>>> res = container.exec_run(cmd, stream=False, demux=False)
>>> res.output
b'hello stderr\nhello stdout\n'

With ``stream=True``, and ``demux=False``, the output is a
generator that yields strings containing the output of both
`stdout` and `stderr`:

>>> res = container.exec_run(cmd, stream=True, demux=False)
>>> next(res.output)
b'hello stdout\n'
>>> next(res.output)
b'hello stderr\n'
>>> next(res.output)
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
StopIteration

With ``stream=True`` and ``demux=True``, the generator now
separates the streams, and yield tuples
``(stdout, stderr)``:

>>> res = container.exec_run(cmd, stream=True, demux=True)
>>> next(res.output)
(b'hello stdout\n', None)
>>> next(res.output)
(None, b'hello stderr\n')
>>> next(res.output)
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
StopIteration

Finally, with ``stream=False`` and ``demux=True``, the whole output
is returned, but the streams are still separated:

>>> res = container.exec_run(cmd, stream=True, demux=True)
>>> next(res.output)
(b'hello stdout\n', None)
>>> next(res.output)
(None, b'hello stderr\n')
>>> next(res.output)
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
StopIteration
