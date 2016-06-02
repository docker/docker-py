import win32pipe
import win32file

import random

def pipe_name():
	return 'testpipe{}'.format(random.randint(0, 4096))

def create_pipe(name):
	handle = win32pipe.CreateNamedPipe(
		'//./pipe/{}'.format(name),
		win32pipe.PIPE_ACCESS_DUPLEX,
		win32pipe.PIPE_TYPE_BYTE | win32pipe.PIPE_READMODE_BYTE | win32pipe.PIPE_WAIT,
		128, 4096, 4096, 300, None
	)
	return handle

def rw_loop(pipe):
	err = win32pipe.ConnectNamedPipe(pipe, None)
	if err != 0:
		raise RuntimeError('Error code: {}'.format(err))
	while True:
		err, data = win32file.ReadFile(pipe, 4096, None)
		if err != 0:
			raise RuntimeError('Error code: {}'.format(err))
		print('Data received: ', data, len(data))
		win32file.WriteFile(pipe, b'ACK', None)


def __main__():
	name = pipe_name()
	print('Initializing pipe {}'.format(name))
	pipe = create_pipe(name)
	print('Pipe created, entering server loop.')
	rw_loop(pipe)

__main__()