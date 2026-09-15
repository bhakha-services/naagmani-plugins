package main

import (
	"log"

	"github.com/bhakha-services/naagmani-plugins/hdk/go/plugin"
)

func main() {
	p := plugin.New("hello-plugin").
		Version("0.1.0").
		Description("A simple Naagmani hello world plugin").
		Author("developer").
		Capabilities("hello_world").
		OnRequestBefore(func(ctx *plugin.Context, req *plugin.Request) (*plugin.Result, error) {
			// Developer diagnostic logging strictly directed to stderr
			log.Printf("[hello-plugin] intercepted request ID=%s model=%s messages=%d",
				ctx.RequestID, req.Model, len(req.Messages))

			// Pass request through unchanged
			return plugin.Continue(), nil
		})

	if err := p.Run(); err != nil {
		log.Fatalf("[hello-plugin] runtime error: %v", err)
	}
}
