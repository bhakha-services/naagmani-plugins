package plugin

import "github.com/bhakha-services/naagmani-plugins/hdk/go/protocol"

// TenantContext carries multi-tenant scoping information for the request.
type TenantContext struct {
	OrganizationID string
	ProjectID      string
	EnvironmentID  string
}

// Context carries metadata and tenant information passed to plugin hooks.
type Context struct {
	Hook      string
	RequestID string
	Tenant    TenantContext
	Metadata  map[string]string
}

func contextFromProtocol(ctx *protocol.HookContext) *Context {
	c := &Context{
		Hook:      ctx.Hook,
		RequestID: ctx.RequestID,
		Tenant: TenantContext{
			OrganizationID: ctx.Tenant.OrganizationID,
			ProjectID:      ctx.Tenant.ProjectID,
			EnvironmentID:  ctx.Tenant.EnvironmentID,
		},
		Metadata: make(map[string]string),
	}
	for k, v := range ctx.Metadata {
		c.Metadata[k] = v
	}
	return c
}
