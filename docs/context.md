# BuildContext object
An immutable representation (named tuple) of a Docker build context. This object
has the following fields:
* path (str): the absolute filesystem path to the build context
* format: a string tag for the context type; one of 'tarball', 'dockerfile',
'remote', 'directory'.
* dockerfile: the name of the Dockerfile for this context.
* job_params: a helper dictionary holding the parameters for a `Client.build`
invocation. The `create_context_from_path` function populates this dictionary
with the specific combination of values that is valid for the kind of build
context represented by the tuple. For example, if the `BuildContext` represents
a tarball context, its `job_params` field will contain a dict with the mappings:
```python
job_params = {
  'encoding': 'gzip'
  'custom_context': True
  'fileobj': open(path)
}
```
When the `BuildContext` represents a single Dockerfile context, `job_params`
will contain:
```python
job_params = {
  'fileobj': open(path)
}
```
## create_context_from_path

This is an intermediary call that you can use to create a `BuildContext`. Using
the returned object you can perform custom validation and filtering steps before
invoking `Client.build`. In a call to `create_context_from_path`, the parameter
`path` can point to any kind of resource supported by the docker daemon, namely:
* A local path to a directory containing a Dockerfile.
* An URL pointing to a git repository or a remote Dockerfile.
* A local path to a tarball containing a pre-packaged build context.

The returned `BuildContext` object can be used in an invocation of
`Client.build` as such:
```python
from docker import Client
from docker.utils.context import (
  create_context_from_path,
  ContextError
)
cli = Client(base_url='tcp://127.0.0.1:2375')
try:
  ctxpath = '/context/path'  # or '/context/Dockerfile',
                             # or '/context/ctx.tar'
                             # or 'https://github.com/user/repo.git'
  ctx = create_context_from_path(ctxpath)
except ContextError as e
  print(e.message)

# here you can perform custom validation, filtering, inserting, etc. on 'ctx'

cli.build(ctx.path, **ctx.job_params)
```

**Params**:

* path (str): Path to the build context.
* dockerfile (str): path within the build context to the Dockerfile

**Returns** (namedtuple): A `BuildContext` object.

**Raises** ContextError: when the contents at `path` are either inaccessible or
inconsistent with the parameters (e.g. a custom 'Dockerfile' name was specified
but the file does not exist at `path`.
