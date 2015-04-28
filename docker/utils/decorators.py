from .. import errors


def check_resource(f):
    def wrapped(self, resource_id=None, *args, **kwargs):
        if resource_id is None:
            if kwargs.get('container'):
                resource_id = kwargs.pop('container')
            elif kwargs.get('image'):
                resource_id = kwargs.pop('image')
            else:
                raise errors.NullResource(
                    'image or container param is undefined'
                )
        return f(self, resource_id, *args, **kwargs)
    return wrapped
