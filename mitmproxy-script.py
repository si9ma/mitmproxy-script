import inspect
import json
import re
import uuid
from mitmproxy import http
from mitmproxy import dns
from mitmproxy import udp
from mitmproxy.addons import dns_resolver

scripts = [
    {
        "pattern": "^https?:\/\/manifests(\.v2)?\.api\.hbo\.com\/hls\.m3u8(\?.+)?$",
        "requires-body": True,
        "max-size": 0,
        "timeout": 30,
        "script": "https://raw.githubusercontent.com/si9ma/DualSubs/main/js/DualSubs.HLS.Main.m3u8.js",
        "type": "response"
    },
    {
        "pattern": "^https?:\/\/manifests(\.v2)?\.api\.hbo\.com\/hlsMedia\.m3u8(\?.*dualsubs=\w+)$",
        "requires-body": True,
        "max-size": 0,
        "timeout": 30,
        "script": "https://raw.githubusercontent.com/si9ma/DualSubs/main/js/DualSubs.HLS.WebVTT.m3u8.js",
        "type": "response"
    },
    {
        "pattern": "^https?:\/\/(.+)\.hbomaxcdn\.com\/videos\/(.+)\.vtt(\?.*dualsubs=\w+)$",
        "requires-body": True,
        "max-size": 0,
        "timeout": 30,
        "script": "https://raw.githubusercontent.com/DualSubs/DualSubs/main/js/DualSubs.SUB.WebVTT.js",
        "type": "response"
    }
]


def download_script(url):
    """
    download script from url to local
    """
    import requests
    r = requests.get(url)
    return r.text


for i, script in enumerate(scripts):
    scripts[i]["script_content"] = download_script(scripts[i]["script"])


def show_object_content(obj):
    # Get a list of the object's attributes
    attributes = inspect.getmembers(obj, lambda a: not (inspect.isroutine(a)))
    # Print the attributes
    for attribute in attributes:
        print(attribute)


def request(flow: http.HTTPFlow):
    print("handle request: " + flow.request.url)

    # change url, remove mitmproxy
    flow.request.host = flow.request.host.replace("mitmproxy.", "")

    # match base on url and pattern
    for script in scripts:
        if script["type"] == "response" or (not flow.request.content and script["requires-body"]):
            continue
        # match pattern use regex
        pattern = re.compile(script["pattern"])
        match = pattern.match(flow.request.url)

        if match:
            print("Matched script: " + script["script"])
            print("received request: " + str(flow.request.content))
            break


def response(flow: http.HTTPFlow):
    print("handle response: " + flow.request.url)
    # match base on url and patter
    for script in scripts:
        if script["type"] == "request" or (not flow.response.content and script["requires-body"]):
            continue

        # match pattern use regex
        pattern = re.compile(script["pattern"])
        match = pattern.match(flow.request.url)

        if match:
            print("Matched script: " +
                  script["script"], "url: " + flow.request.url)
            call_js(flow, script)
            break


def call_js(flow: http.HTTPFlow, script):
    vars = {
        "$request": {
            "url": flow.request.url,
            "method": flow.request.method,
            "headers": headers_to_dict(flow.request.headers),
            "body": str(flow.request.content, 'UTF-8')
        },
        "$response": {
            "status": flow.response.status_code,
            "headers": headers_to_dict(flow.response.headers),
            "body": str(flow.response.content, 'UTF-8')
        }
    }

    # js wrapper code
    js_code = """
    const http = require('http');
    const https = require('https');

    class HttpClient {
        makeRequest (options, callback) {
            module  = options.url.startsWith('https') ? https : http;
            options.host = options.url.match(/:\/\/(.[^/]+)/)[1];
            options.path = options.url.replace(/.*?:\/\//g, '').replace(options.host, '');
            const req = module.request(options, res => {
                let response = '';
                res.setEncoding('utf8');
                res.on('data', chunk => {
                    response += chunk;
                });
                res.on('end', () => {
                    callback(null, res, response);
                });
            });

            req.on('error', error => {
                callback(error);
            });

            if (options.data) {
                req.write(options.data);
            }
            if (options.body) {
                req.write(options.body);
            }
            req.end();
        }

        get(options, callback) {
            if (typeof options === 'string') {
                options = {
                    url: options
                };
            }

            options.method = 'GET';
            this.makeRequest(options, callback);
        }

        put(options, callback) {
            if (typeof options === 'string') {
                options = {
                    url: options
                };
            }

            options.method = 'PUT';
            this.makeRequest(options, callback);
        }

        post(options, callback) {
            if (typeof options === 'string') {
                options = {
                    url: options
                };
            }

            options.method = 'POST';
            this.makeRequest(options, callback);
        }

        delete(options, callback) {
            if (typeof options === 'string') {
                options = {
                    url: options
                };
            }

            options.method = 'DELETE';
            this.makeRequest(options, callback);
        }

        head(options, callback) {
            if (typeof options === 'string') {
                options = {
                    url: options
                };
            }

            options.method = 'HEAD';
            this.makeRequest(options, callback);
        }

        patch(options, callback) {
            if (typeof options === 'string') {
                options = {
                    url: options
                };
            }

            options.method = 'PATCH';
            this.makeRequest(options, callback);
        }
    }

    $httpClient = new HttpClient()

    class PersistentStore {
        constructor() {
            this.cache = {}
        }

        read (key) {
            return this.cache[key]
        }

        write (key, value) {
            this.cache[key] = value
        }
    }

    $persistentStore = new PersistentStore()

    const util = require('util')

    $loon = ''

    function $done (val) {
        console.log('result------------------')
        console.log(JSON.stringify(val, null, 4));
        console.log('result------------------')
    }
    $request = %s
    $response = %s
    """ % (json.dumps(vars["$request"]), json.dumps(vars["$response"]))
    js_code += script["script_content"]

    # create an temp js file in /tmp/ to run
    id = uuid.uuid4().hex
    tmp_file = "/tmp/" + id + ".js"
    # tmp_file = "debug.js"

    # save js code to file then run
    with open(tmp_file, "w") as f:
        f.write(js_code)

    # run js code with nodejs
    import subprocess
    res = subprocess.run(["node", tmp_file], capture_output=True)

    # parse result from stdout between 'result------------------'
    result = re.search(
        r"result------------------\n(.*)\nresult------------------", res.stdout.decode("utf-8"), re.DOTALL)
    if result:
        result = json.loads(result.group(1))
        if "status" in result:
            flow.response.status_code = result["status"]
        if "headers" in result:
            for key, value in result["headers"].items():
                flow.response.headers[key] = value
        if "body" in result:
            flow.response.content = result["body"].encode("utf-8")

    # print(res.stdout.decode("utf-8"))

    # remove temp js file
    import os
    os.remove(tmp_file)


def headers_to_dict(headers):
    return dict(headers.items(multi=True))
