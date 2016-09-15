
def add_port_mapping(port_bindings, internal_port, external):
    if internal_port in port_bindings:
        port_bindings[internal_port].append(external)
    else:
        port_bindings[internal_port] = [external]


def add_port(port_bindings, internal_port_range, external_range):
    if external_range is None:
        for internal_port in internal_port_range:
            add_port_mapping(port_bindings, internal_port, None)
    else:
        ports = zip(internal_port_range, external_range)
        for internal_port, external_port in ports:
            add_port_mapping(port_bindings, internal_port, external_port)


def build_port_bindings(ports):
    port_bindings = {}
    for port in ports:
        internal_port_range, external_range = split_port(port)
        add_port(port_bindings, internal_port_range, external_range)
    return port_bindings


def to_port_range(port):
    if not port:
        return None

    protocol = ""
    if "/" in port:
        parts = port.split("/")
        if len(parts) != 2:
            _raise_invalid_port(port)

        port, protocol = parts
        protocol = "/" + protocol

    parts = str(port).split('-')

    if len(parts) == 1:
        return ["%s%s" % (port, protocol)]

    if len(parts) == 2:
        full_port_range = range(int(parts[0]), int(parts[1]) + 1)
        return ["%s%s" % (p, protocol) for p in full_port_range]

    raise ValueError('Invalid port range "%s", should be '
                     'port or startport-endport' % port)


def _raise_invalid_port(port):
    raise ValueError('Invalid port "%s", should be '
                     '[[remote_ip:]remote_port[-remote_port]:]'
                     'port[/protocol]' % port)


def split_port(port):
    parts = str(port).split(':')

    if not 1 <= len(parts) <= 3:
        _raise_invalid_port(port)

    if len(parts) == 1:
        internal_port, = parts
        return to_port_range(internal_port), None
    if len(parts) == 2:
        external_port, internal_port = parts

        internal_range = to_port_range(internal_port)
        external_range = to_port_range(external_port)

        if internal_range is None or external_range is None:
            _raise_invalid_port(port)

        if len(internal_range) != len(external_range):
            raise ValueError('Port ranges don\'t match in length')

        return internal_range, external_range

    external_ip, external_port, internal_port = parts
    internal_range = to_port_range(internal_port)
    external_range = to_port_range(external_port)
    if not external_range:
        external_range = [None] * len(internal_range)

    if len(internal_range) != len(external_range):
        raise ValueError('Port ranges don\'t match in length')

    return internal_range, [(external_ip, ex_port or None)
                            for ex_port in external_range]
