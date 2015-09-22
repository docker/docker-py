FROM python:2.7
RUN mkdir /tmp/certs
VOLUME /certs

WORKDIR /tmp/certs
RUN openssl genrsa -aes256 -passout pass:foobar -out ca-key.pem 4096
RUN echo "[req]\nprompt=no\ndistinguished_name = req_distinguished_name\n[req_distinguished_name]\ncountryName=AU" > /tmp/config
RUN openssl req -new -x509 -passin pass:foobar -config /tmp/config -days 365 -key ca-key.pem -sha256 -out ca.pem
RUN openssl genrsa -out server-key.pem -passout pass:foobar 4096
RUN openssl req -subj "/CN=docker" -sha256 -new -key server-key.pem -out server.csr
RUN echo subjectAltName = DNS:docker,DNS:localhost > extfile.cnf
RUN openssl x509 -req -days 365 -passin pass:foobar -sha256 -in server.csr -CA ca.pem -CAkey ca-key.pem -CAcreateserial -out server-cert.pem -extfile extfile.cnf
RUN openssl genrsa -out key.pem 4096
RUN openssl req -passin pass:foobar -subj '/CN=client' -new -key key.pem -out client.csr
RUN echo extendedKeyUsage = clientAuth > extfile.cnf
RUN openssl x509 -req -passin pass:foobar -days 365 -sha256 -in client.csr -CA ca.pem -CAkey ca-key.pem -CAcreateserial -out cert.pem -extfile extfile.cnf
RUN chmod -v 0400 ca-key.pem key.pem server-key.pem
RUN chmod -v 0444 ca.pem server-cert.pem cert.pem

CMD cp -R /tmp/certs/* /certs && while true; do sleep 1; done
