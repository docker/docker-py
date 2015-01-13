import json
import re


build_success_re = r'^Successfully built ([a-f0-9]+)\n$'


def get_build_id(build_result, discard_logs=False):
    """ **Params:**
        * `build_result` is a python generator returned by `Client.build`
        * `discard_logs` (bool, default=False). If True, log lines will
          be discarded after they're processed. Limits memory footprint.
        **Returns** tuple:
            1. Image ID if found, None otherwise
            2. List of log lines
    """
    parsed_lines = []
    image_id = None
    for line in build_result:
        try:
            parsed_line = json.loads(line).get('stream', '')
            if not discard_logs:
                parsed_lines.append(parsed_line)
            match = re.match(build_success_re, line)
            if match:
                image_id = match.group(1)
        except ValueError:
            # sometimes all the data is sent on a single line
            # This ONLY works because every line is formatted as
            # {"stream": STRING}
            lines = re.findall('{\s*"stream"\s*:\s*"[^"]*"\s*}', line)
            return get_build_id(lines, discard_logs)

    return image_id, parsed_lines
