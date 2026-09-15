# Hello Plugin (Naagmani HDK Example)

A reference Naagmani plugin built with the Go HDK (`github.com/bhakha-services/naagmani-plugins/hdk/go`).

## Features
- Implements `naagmani.plugin/v1` protocol.
- Subscribes to the `request.before` ingress hook.
- Logs the request to `stderr` and returns `continue` to let inference proceed normally.

## Building
```bash
go build -o hello-plugin main.go
```

On Windows:
```bash
go build -o hello-plugin.exe main.go
```
