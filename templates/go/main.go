package main

import (
	"log"

	"github.com/bhakha-services/naagmani-plugins/hdk/go/plugin"
)

func main() {
	p := plugin.New("my-go-plugin").
		Version("0.1.0").
		Description("A starter Naagmani plugin built with Go").
		OnRequestBefore(func(ctx *plugin.Context, req *plugin.Request) (*plugin.Result, error) {
			log.Printf("[my-go-plugin] processing request ID=%s model=%s", ctx.RequestID, req.Model)
			return plugin.Continue(), nil
		})

	if err := p.Run(); err != nil {
		log.Fatalf("[my-go-plugin] runtime error: %v", err)
	}
}
