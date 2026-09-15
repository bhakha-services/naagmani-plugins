package plugin

import (
	"io"
	"os"
)

// RequestHandler handles inbound request hooks ("request.before", "request.after").
type RequestHandler func(ctx *Context, req *Request) (*Result, error)

// ResponseHandler handles outbound response hooks ("response.before", "response.after").
type ResponseHandler func(ctx *Context, resp *Response) (*Result, error)

// Plugin is the primary developer abstraction for creating a Naagmani plugin.
type Plugin struct {
	name         string
	version      string
	description  string
	author       string
	capabilities []string

	onRequestBefore  RequestHandler
	onRequestAfter   RequestHandler
	onResponseBefore ResponseHandler
	onResponseAfter  ResponseHandler
}

// New creates a new Plugin definition with the specified plugin name.
func New(name string) *Plugin {
	return &Plugin{
		name:    name,
		version: "0.1.0",
	}
}

// Version sets the plugin semantic version (default: "0.1.0").
func (p *Plugin) Version(v string) *Plugin {
	p.version = v
	return p
}

// Description sets the human-readable description for the plugin.
func (p *Plugin) Description(desc string) *Plugin {
	p.description = desc
	return p
}

// Author sets the author or organization name.
func (p *Plugin) Author(author string) *Plugin {
	p.author = author
	return p
}

// Capabilities declares functional capabilities provided by this plugin.
func (p *Plugin) Capabilities(caps ...string) *Plugin {
	p.capabilities = append(p.capabilities, caps...)
	return p
}

// OnRequestBefore registers a handler executed on the "request.before" pipeline hook.
// Handlers can inspect the request, return Continue(), Block(reason), or ModifyRequest(req).
func (p *Plugin) OnRequestBefore(h RequestHandler) *Plugin {
	p.onRequestBefore = h
	return p
}

// OnRequestAfter registers a handler executed on the "request.after" pipeline hook.
// Handlers can inspect the routed request (read-only; cannot modify).
func (p *Plugin) OnRequestAfter(h RequestHandler) *Plugin {
	p.onRequestAfter = h
	return p
}

// OnResponseBefore registers a handler executed on the "response.before" pipeline hook.
// Handlers can inspect and mutate the response before it reaches the client.
func (p *Plugin) OnResponseBefore(h ResponseHandler) *Plugin {
	p.onResponseBefore = h
	return p
}

// OnResponseAfter registers a handler executed on the "response.after" pipeline hook.
// Handlers can perform asynchronous telemetry and audit logging.
func (p *Plugin) OnResponseAfter(h ResponseHandler) *Plugin {
	p.onResponseAfter = h
	return p
}

// Run starts the plugin event loop using standard input and output pipes.
// This is the default entrypoint for compiled plugin binaries.
func (p *Plugin) Run() error {
	return p.Serve(os.Stdin, os.Stdout)
}

// Serve starts the plugin event loop on arbitrary input and output streams.
// Useful for automated testing and in-memory test harnesses.
func (p *Plugin) Serve(in io.Reader, out io.Writer) error {
	srv := newServer(p, in, out)
	return srv.serve()
}
