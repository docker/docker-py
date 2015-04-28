import docker.errors


def check_resource(f):
    def wrapped(resource_id=None, *args, **kwargs):
        if resource_id is None and (
            kwargs.get('container') is None and kwargs.get('image') is None
        ):
            raise docker.errors.NullResource(
                'image or container param is None'
            )
        return f(resource_id, *args, **kwargs)
    return wrapped
