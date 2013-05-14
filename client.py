import requests

class Client(requests.Session):
    def __init__(self, base_url="http://localhost"):
        self.base_url = base_url

    def _url(self, path):
        return self.base_url + path

    def _result(self, response):
        # FIXME
        return response

    def build(self, dockerfile):
        url = self._url("/build")
        return self._result(self.post(url, dockerfile))

    def history(self, image):
        return self._result(self.get(self._url("/images/{0}/history".format(image))))

    def info(self):
        return self._result(self.get(self._url("/info")))

    def insert(self, image, url, path):
        url = self._url("/images/" + image)
        params = {
            'url': url,
            'path': path
        }
        return self._result(self.post(url, None, params=params))

    def inspect_container(self, container_id):
        return self._result(self.get(self._url("/containers/{0}/json".format(container_id))))

    def inspect_image(self, image_id):
        return self._result(self.get(self._url("/images/{0}/json".format(image_id))))

    def kill(self, *args):
        for name in args:
            url = self._url("/containers/{0}/kill".format(name))
            self.post(url, None)

    def login(self, username, password=None, email=None):
        url = self._url("/auth")
        res = self.get(url)
        json = res.json()
        if 'username' in json and json['username'] == username:
            return json
        req_data = {
            'username': username,
            'password': password if password is not None else json['password'],
            'email': email if email is not None else json['email']
        }
        return self._result(self.post(url, req_data))

    def port(self, container, private_port):
        res = self.get(self._url("/containers/{0}/json".format(container)))
        json = res.json()
        return json['NetworkSettings']['PortMapping'][private_port]

    def remove_container(self, *args, **kwargs):
        params = {
            'v': kwargs.get('v', False)
        }
        for container in args:
            self.delete(self._url("/containers/" + container), params=params)

    def remove_image(self, *args):
        for image in args:
            self.delete(self._url("/images/" + image))

    def restart(self, *args, **kwargs):
        params = {
            't': kwargs.get('timeout', 10)
        }
        for name in args:
            url = self._url("/containers/{0}/restart".format(name))
            self.post(url, None, params=params)

    def start(self, *args):
        for name in args:
            url = self._url("/containers/{0}/start".format(name))
            self.post(url, None)

    def stop(self, *args, **kwargs):
        params = {
            't': kwargs.get('timeout', 10)
        }
        for name in args:
            url = self._url("/containers/{0}/stop".format(name))
            self.post(url, None, params=params)

    def version(self):
        return self._result(self.get(self._url("/version")))

    def wait(self, *args):
        result = []
        for name in args:
            url = self._url("/containers/{0}/wait".format(name))
            res = self.post(url, None, timeout=None)
            json = res.json()
            if 'StatusCode' in json:
                result.append(json['StatusCode'])
        return result


# func CmdImport(args ...string) error {
#     cmd := Subcmd("import", "URL|- [REPOSITORY [TAG]]", "Create a new filesystem image from the contents of a tarball")

#     if err := cmd.Parse(args); err != nil {
#         return nil
#     }
#     if cmd.NArg() < 1 {
#         cmd.Usage()
#         return nil
#     }
#     src, repository, tag := cmd.Arg(0), cmd.Arg(1), cmd.Arg(2)
#     v := url.Values{}
#     v.Set("repo", repository)
#     v.Set("tag", tag)
#     v.Set("fromSrc", src)

#     err := hijack("POST", "/images/create?"+v.Encode(), false)
#     if err != nil {
#         return err
#     }
#     return nil
# }

# func CmdPush(args ...string) error {
#     cmd := Subcmd("push", "[OPTION] NAME", "Push an image or a repository to the registry")
#     registry := cmd.String("registry", "", "Registry host to push the image to")
#     if err := cmd.Parse(args); err != nil {
#         return nil
#     }
#     name := cmd.Arg(0)

#     if name == "" {
#         cmd.Usage()
#         return nil
#     }

#     body, _, err := call("GET", "/auth", nil)
#     if err != nil {
#         return err
#     }

#     var out auth.AuthConfig
#     err = json.Unmarshal(body, &out)
#     if err != nil {
#         return err
#     }

#     // If the login failed AND we're using the index, abort
#     if *registry == "" && out.Username == "" {
#         if err := CmdLogin(args...); err != nil {
#             return err
#         }

#         body, _, err = call("GET", "/auth", nil)
#         if err != nil {
#             return err
#         }
#         err = json.Unmarshal(body, &out)
#         if err != nil {
#             return err
#         }

#         if out.Username == "" {
#             return fmt.Errorf("Please login prior to push. ('docker login')")
#         }
#     }

#     if len(strings.SplitN(name, "/", 2)) == 1 {
#         return fmt.Errorf("Impossible to push a \"root\" repository. Please rename your repository in <user>/<repo> (ex: %s/%s)", out.Username, name)
#     }

#     v := url.Values{}
#     v.Set("registry", *registry)
#     if err := hijack("POST", "/images/"+name+"/push?"+v.Encode(), false); err != nil {
#         return err
#     }
#     return nil
# }

# func CmdPull(args ...string) error {
#     cmd := Subcmd("pull", "NAME", "Pull an image or a repository from the registry")
#     tag := cmd.String("t", "", "Download tagged image in repository")
#     registry := cmd.String("registry", "", "Registry to download from. Necessary if image is pulled by ID")
#     if err := cmd.Parse(args); err != nil {
#         return nil
#     }

#     if cmd.NArg() != 1 {
#         cmd.Usage()
#         return nil
#     }

#     remote := cmd.Arg(0)
#     if strings.Contains(remote, ":") {
#         remoteParts := strings.Split(remote, ":")
#         tag = &remoteParts[1]
#         remote = remoteParts[0]
#     }

#     v := url.Values{}
#     v.Set("fromImage", remote)
#     v.Set("tag", *tag)
#     v.Set("registry", *registry)

#     if err := hijack("POST", "/images/create?"+v.Encode(), false); err != nil {
#         return err
#     }

#     return nil
# }

# func CmdImages(args ...string) error {
#     cmd := Subcmd("images", "[OPTIONS] [NAME]", "List images")
#     quiet := cmd.Bool("q", false, "only show numeric IDs")
#     all := cmd.Bool("a", false, "show all images")
#     flViz := cmd.Bool("viz", false, "output graph in graphviz format")

#     if err := cmd.Parse(args); err != nil {
#         return nil
#     }
#     if cmd.NArg() > 1 {
#         cmd.Usage()
#         return nil
#     }

#     if *flViz {
#         body, _, err := call("GET", "/images/viz", false)
#         if err != nil {
#             return err
#         }
#         fmt.Printf("%s", body)
#     } else {
#         v := url.Values{}
#         if cmd.NArg() == 1 {
#             v.Set("filter", cmd.Arg(0))
#         }
#         if *quiet {
#             v.Set("only_ids", "1")
#         }
#         if *all {
#             v.Set("all", "1")
#         }

#         body, _, err := call("GET", "/images/json?"+v.Encode(), nil)
#         if err != nil {
#             return err
#         }

#         var outs []ApiImages
#         err = json.Unmarshal(body, &outs)
#         if err != nil {
#             return err
#         }

#         w := tabwriter.NewWriter(os.Stdout, 20, 1, 3, ' ', 0)
#         if !*quiet {
#             fmt.Fprintln(w, "REPOSITORY\tTAG\tID\tCREATED")
#         }

#         for _, out := range outs {
#             if !*quiet {
#                 fmt.Fprintf(w, "%s\t%s\t%s\t%s ago\n", out.Repository, out.Tag, out.Id, HumanDuration(time.Now().Sub(time.Unix(out.Created, 0))))
#             } else {
#                 fmt.Fprintln(w, out.Id)
#             }
#         }

#         if !*quiet {
#             w.Flush()
#         }
#     }
#     return nil
# }

# func CmdPs(args ...string) error {
#     cmd := Subcmd("ps", "[OPTIONS]", "List containers")
#     quiet := cmd.Bool("q", false, "Only display numeric IDs")
#     all := cmd.Bool("a", false, "Show all containers. Only running containers are shown by default.")
#     noTrunc := cmd.Bool("notrunc", false, "Don't truncate output")
#     nLatest := cmd.Bool("l", false, "Show only the latest created container, include non-running ones.")
#     since := cmd.String("sinceId", "", "Show only containers created since Id, include non-running ones.")
#     before := cmd.String("beforeId", "", "Show only container created before Id, include non-running ones.")
#     last := cmd.Int("n", -1, "Show n last created containers, include non-running ones.")

#     if err := cmd.Parse(args); err != nil {
#         return nil
#     }
#     v := url.Values{}
#     if *last == -1 && *nLatest {
#         *last = 1
#     }
#     if *quiet {
#         v.Set("only_ids", "1")
#     }
#     if *all {
#         v.Set("all", "1")
#     }
#     if *noTrunc {
#         v.Set("trunc_cmd", "0")
#     }
#     if *last != -1 {
#         v.Set("limit", strconv.Itoa(*last))
#     }
#     if *since != "" {
#         v.Set("since", *since)
#     }
#     if *before != "" {
#         v.Set("before", *before)
#     }

#     body, _, err := call("GET", "/containers/ps?"+v.Encode(), nil)
#     if err != nil {
#         return err
#     }

#     var outs []ApiContainers
#     err = json.Unmarshal(body, &outs)
#     if err != nil {
#         return err
#     }
#     w := tabwriter.NewWriter(os.Stdout, 20, 1, 3, ' ', 0)
#     if !*quiet {
#         fmt.Fprintln(w, "ID\tIMAGE\tCOMMAND\tCREATED\tSTATUS\tPORTS")
#     }

#     for _, out := range outs {
#         if !*quiet {
#             fmt.Fprintf(w, "%s\t%s\t%s\t%s\t%s ago\t%s\n", out.Id, out.Image, out.Command, out.Status, HumanDuration(time.Now().Sub(time.Unix(out.Created, 0))), out.Ports)
#         } else {
#             fmt.Fprintln(w, out.Id)
#         }
#     }

#     if !*quiet {
#         w.Flush()
#     }
#     return nil
# }

# func CmdCommit(args ...string) error {
#     cmd := Subcmd("commit", "[OPTIONS] CONTAINER [REPOSITORY [TAG]]", "Create a new image from a container's changes")
#     flComment := cmd.String("m", "", "Commit message")
#     flAuthor := cmd.String("author", "", "Author (eg. \"John Hannibal Smith <hannibal@a-team.com>\"")
#     flConfig := cmd.String("run", "", "Config automatically applied when the image is run. "+`(ex: {"Cmd": ["cat", "/world"], "PortSpecs": ["22"]}')`)
#     if err := cmd.Parse(args); err != nil {
#         return nil
#     }
#     name, repository, tag := cmd.Arg(0), cmd.Arg(1), cmd.Arg(2)
#     if name == "" {
#         cmd.Usage()
#         return nil
#     }

#     v := url.Values{}
#     v.Set("container", name)
#     v.Set("repo", repository)
#     v.Set("tag", tag)
#     v.Set("comment", *flComment)
#     v.Set("author", *flAuthor)
#     var config *Config
#     if *flConfig != "" {
#         config = &Config{}
#         if err := json.Unmarshal([]byte(*flConfig), config); err != nil {
#             return err
#         }
#     }
#     body, _, err := call("POST", "/commit?"+v.Encode(), config)
#     if err != nil {
#         return err
#     }

#     apiId := &ApiId{}
#     err = json.Unmarshal(body, apiId)
#     if err != nil {
#         return err
#     }

#     fmt.Println(apiId.Id)
#     return nil
# }

# func CmdExport(args ...string) error {
#     cmd := Subcmd("export", "CONTAINER", "Export the contents of a filesystem as a tar archive")
#     if err := cmd.Parse(args); err != nil {
#         return nil
#     }

#     if cmd.NArg() != 1 {
#         cmd.Usage()
#         return nil
#     }

#     if err := stream("GET", "/containers/"+cmd.Arg(0)+"/export"); err != nil {
#         return err
#     }
#     return nil
# }

# func CmdDiff(args ...string) error {
#     cmd := Subcmd("diff", "CONTAINER", "Inspect changes on a container's filesystem")
#     if err := cmd.Parse(args); err != nil {
#         return nil
#     }
#     if cmd.NArg() != 1 {
#         cmd.Usage()
#         return nil
#     }

#     body, _, err := call("GET", "/containers/"+cmd.Arg(0)+"/changes", nil)
#     if err != nil {
#         return err
#     }

#     changes := []Change{}
#     err = json.Unmarshal(body, &changes)
#     if err != nil {
#         return err
#     }
#     for _, change := range changes {
#         fmt.Println(change.String())
#     }
#     return nil
# }

# func CmdLogs(args ...string) error {
#     cmd := Subcmd("logs", "CONTAINER", "Fetch the logs of a container")
#     if err := cmd.Parse(args); err != nil {
#         return nil
#     }
#     if cmd.NArg() != 1 {
#         cmd.Usage()
#         return nil
#     }

#     v := url.Values{}
#     v.Set("logs", "1")
#     v.Set("stdout", "1")
#     v.Set("stderr", "1")

#     if err := hijack("POST", "/containers/"+cmd.Arg(0)+"/attach?"+v.Encode(), false); err != nil {
#         return err
#     }
#     return nil
# }

# func CmdAttach(args ...string) error {
#     cmd := Subcmd("attach", "CONTAINER", "Attach to a running container")
#     if err := cmd.Parse(args); err != nil {
#         return nil
#     }
#     if cmd.NArg() != 1 {
#         cmd.Usage()
#         return nil
#     }

#     body, _, err := call("GET", "/containers/"+cmd.Arg(0)+"/json", nil)
#     if err != nil {
#         return err
#     }

#     container := &Container{}
#     err = json.Unmarshal(body, container)
#     if err != nil {
#         return err
#     }

#     v := url.Values{}
#     v.Set("stream", "1")
#     v.Set("stdout", "1")
#     v.Set("stderr", "1")
#     v.Set("stdin", "1")

#     if err := hijack("POST", "/containers/"+cmd.Arg(0)+"/attach?"+v.Encode(), container.Config.Tty); err != nil {
#         return err
#     }
#     return nil
# }

# func CmdSearch(args ...string) error {
#     cmd := Subcmd("search", "NAME", "Search the docker index for images")
#     if err := cmd.Parse(args); err != nil {
#         return nil
#     }
#     if cmd.NArg() != 1 {
#         cmd.Usage()
#         return nil
#     }

#     v := url.Values{}
#     v.Set("term", cmd.Arg(0))
#     body, _, err := call("GET", "/images/search?"+v.Encode(), nil)
#     if err != nil {
#         return err
#     }

#     outs := []ApiSearch{}
#     err = json.Unmarshal(body, &outs)
#     if err != nil {
#         return err
#     }
#     fmt.Printf("Found %d results matching your query (\"%s\")\n", len(outs), cmd.Arg(0))
#     w := tabwriter.NewWriter(os.Stdout, 20, 1, 3, ' ', 0)
#     fmt.Fprintf(w, "NAME\tDESCRIPTION\n")
#     for _, out := range outs {
#         fmt.Fprintf(w, "%s\t%s\n", out.Name, out.Description)
#     }
#     w.Flush()
#     return nil
# }

# // Ports type - Used to parse multiple -p flags
# type ports []int

# // ListOpts type
# type ListOpts []string

# func (opts *ListOpts) String() string {
#     return fmt.Sprint(*opts)
# }

# func (opts *ListOpts) Set(value string) error {
#     *opts = append(*opts, value)
#     return nil
# }

# // AttachOpts stores arguments to 'docker run -a', eg. which streams to attach to
# type AttachOpts map[string]bool

# func NewAttachOpts() AttachOpts {
#     return make(AttachOpts)
# }

# func (opts AttachOpts) String() string {
#     // Cast to underlying map type to avoid infinite recursion
#     return fmt.Sprintf("%v", map[string]bool(opts))
# }

# func (opts AttachOpts) Set(val string) error {
#     if val != "stdin" && val != "stdout" && val != "stderr" {
#         return fmt.Errorf("Unsupported stream name: %s", val)
#     }
#     opts[val] = true
#     return nil
# }

# func (opts AttachOpts) Get(val string) bool {
#     if res, exists := opts[val]; exists {
#         return res
#     }
#     return false
# }

# // PathOpts stores a unique set of absolute paths
# type PathOpts map[string]struct{}

# func NewPathOpts() PathOpts {
#     return make(PathOpts)
# }

# func (opts PathOpts) String() string {
#     return fmt.Sprintf("%v", map[string]struct{}(opts))
# }

# func (opts PathOpts) Set(val string) error {
#     if !filepath.IsAbs(val) {
#         return fmt.Errorf("%s is not an absolute path", val)
#     }
#     opts[filepath.Clean(val)] = struct{}{}
#     return nil
# }

# func CmdTag(args ...string) error {
#     cmd := Subcmd("tag", "[OPTIONS] IMAGE REPOSITORY [TAG]", "Tag an image into a repository")
#     force := cmd.Bool("f", false, "Force")
#     if err := cmd.Parse(args); err != nil {
#         return nil
#     }
#     if cmd.NArg() != 2 && cmd.NArg() != 3 {
#         cmd.Usage()
#         return nil
#     }

#     v := url.Values{}
#     v.Set("repo", cmd.Arg(1))
#     if cmd.NArg() == 3 {
#         v.Set("tag", cmd.Arg(2))
#     }

#     if *force {
#         v.Set("force", "1")
#     }

#     if _, _, err := call("POST", "/images/"+cmd.Arg(0)+"/tag?"+v.Encode(), nil); err != nil {
#         return err
#     }
#     return nil
# }

# func CmdRun(args ...string) error {
#     config, cmd, err := ParseRun(args, nil)
#     if err != nil {
#         return err
#     }
#     if config.Image == "" {
#         cmd.Usage()
#         return nil
#     }

#     //create the container
#     body, statusCode, err := call("POST", "/containers/create", config)
#     //if image not found try to pull it
#     if statusCode == 404 {
#         v := url.Values{}
#         v.Set("fromImage", config.Image)
#         err = hijack("POST", "/images?"+v.Encode(), false)
#         if err != nil {
#             return err
#         }
#         body, _, err = call("POST", "/containers/create", config)
#         if err != nil {
#             return err
#         }
#     }
#     if err != nil {
#         return err
#     }

#     out := &ApiRun{}
#     err = json.Unmarshal(body, out)
#     if err != nil {
#         return err
#     }

#     for _, warning := range out.Warnings {
#         fmt.Fprintln(os.Stderr, "WARNING: ", warning)
#     }

#     v := url.Values{}
#     v.Set("logs", "1")
#     v.Set("stream", "1")

#     if config.AttachStdin {
#         v.Set("stdin", "1")
#     }
#     if config.AttachStdout {
#         v.Set("stdout", "1")
#     }
#     if config.AttachStderr {
#         v.Set("stderr", "1")

#     }

#     //start the container
#     _, _, err = call("POST", "/containers/"+out.Id+"/start", nil)
#     if err != nil {
#         return err
#     }

#     if config.AttachStdin || config.AttachStdout || config.AttachStderr {
#         if err := hijack("POST", "/containers/"+out.Id+"/attach?"+v.Encode(), config.Tty); err != nil {
#             return err
#         }
#     }
#     if !config.AttachStdout && !config.AttachStderr {
#         fmt.Println(out.Id)
#     }
#     return nil
# }

# func call(method, path string, data interface{}) ([]byte, int, error) {
#     var params io.Reader
#     if data != nil {
#         buf, err := json.Marshal(data)
#         if err != nil {
#             return nil, -1, err
#         }
#         params = bytes.NewBuffer(buf)
#     }

#     req, err := http.NewRequest(method, "http://0.0.0.0:4243"+path, params)
#     if err != nil {
#         return nil, -1, err
#     }
#     req.Header.Set("User-Agent", "Docker-Client/"+VERSION)
#     if data != nil {
#         req.Header.Set("Content-Type", "application/json")
#     } else if method == "POST" {
#         req.Header.Set("Content-Type", "plain/text")
#     }
#     resp, err := http.DefaultClient.Do(req)
#     if err != nil {
#         if strings.Contains(err.Error(), "connection refused") {
#             return nil, -1, fmt.Errorf("Can't connect to docker daemon. Is 'docker -d' running on this host?")
#         }
#         return nil, -1, err
#     }
#     defer resp.Body.Close()
#     body, err := ioutil.ReadAll(resp.Body)
#     if err != nil {
#         return nil, -1, err
#     }
#     if resp.StatusCode < 200 || resp.StatusCode >= 400 {
#         return nil, resp.StatusCode, fmt.Errorf("error: %s", body)
#     }
#     return body, resp.StatusCode, nil
# }

# func stream(method, path string) error {
#     req, err := http.NewRequest(method, "http://0.0.0.0:4243"+path, nil)
#     if err != nil {
#         return err
#     }
#     req.Header.Set("User-Agent", "Docker-Client/"+VERSION)
#     if method == "POST" {
#         req.Header.Set("Content-Type", "plain/text")
#     }
#     resp, err := http.DefaultClient.Do(req)
#     if err != nil {
#         if strings.Contains(err.Error(), "connection refused") {
#             return fmt.Errorf("Can't connect to docker daemon. Is 'docker -d' running on this host?")
#         }
#         return err
#     }
#     defer resp.Body.Close()
#     if _, err := io.Copy(os.Stdout, resp.Body); err != nil {
#         return err
#     }
#     return nil
# }

# func hijack(method, path string, setRawTerminal bool) error {
#     req, err := http.NewRequest(method, path, nil)
#     if err != nil {
#         return err
#     }
#     req.Header.Set("Content-Type", "plain/text")
#     dial, err := net.Dial("tcp", "0.0.0.0:4243")
#     if err != nil {
#         return err
#     }
#     clientconn := httputil.NewClientConn(dial, nil)
#     clientconn.Do(req)
#     defer clientconn.Close()

#     rwc, br := clientconn.Hijack()
#     defer rwc.Close()

#     receiveStdout := Go(func() error {
#         _, err := io.Copy(os.Stdout, br)
#         return err
#     })

#     if setRawTerminal && term.IsTerminal(int(os.Stdin.Fd())) && os.Getenv("NORAW") == "" {
#         if oldState, err := SetRawTerminal(); err != nil {
#             return err
#         } else {
#             defer RestoreTerminal(oldState)
#         }
#     }

#     sendStdin := Go(func() error {
#         _, err := io.Copy(rwc, os.Stdin)
#         if err := rwc.(*net.TCPConn).CloseWrite(); err != nil {
#             fmt.Fprintf(os.Stderr, "Couldn't send EOF: %s\n", err)
#         }
#         return err
#     })

#     if err := <-receiveStdout; err != nil {
#         return err
#     }

#     if !term.IsTerminal(int(os.Stdin.Fd())) {
#         if err := <-sendStdin; err != nil {
#             return err
#         }
#     }
#     return nil

# }

# func Subcmd(name, signature, description string) *flag.FlagSet {
#     flags := flag.NewFlagSet(name, flag.ContinueOnError)
#     flags.Usage = func() {
#         fmt.Printf("\nUsage: docker %s %s\n\n%s\n\n", name, signature, description)
#         flags.PrintDefaults()
#     }
#     return flags
# }
