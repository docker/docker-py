# Portainer

To connect with Docker through the portainer API we need a custom http header.
This can be done by adding the header to the config.json `HttpHeaders` entry.
The APIClient searches for the config.json file in your home directory or in the
directory you specify in the DOCKER_CONFIG environment variable.

For sake of clarity we create the config file in this example inline:

```python

with TemporaryDirectory() as temp_path:
    docker_config = temp_path / Path("config.json")

    docker_config.write_text(
        json.dumps(
            {
                "HttpHeaders": {
                    "Authorization": "Bearer " + os.environ("PORTAINER_JWT"),
                }
            }
        )
    )

    os.environ["DOCKER_CONFIG"] = temp_path

    client = DockerClient(
        base_url="http://localhost:9000/api/endpoints/1/docker/")

    print(client.containers.list())
```
