package plugin

import "github.com/bhakha-services/naagmani-plugins/hdk/go/protocol"

// Usage carries token usage statistics.
type Usage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

// Response represents an AI model completion response.
type Response struct {
	Model   string `json:"model"`
	Content string `json:"content"`
	Usage   *Usage `json:"usage,omitempty"`
}

func responseFromProtocol(resp *protocol.HookResponse) *Response {
	if resp == nil {
		return nil
	}
	r := &Response{
		Model:   resp.Model,
		Content: resp.Content,
	}
	if resp.Usage != nil {
		r.Usage = &Usage{
			PromptTokens:     resp.Usage.PromptTokens,
			CompletionTokens: resp.Usage.CompletionTokens,
			TotalTokens:      resp.Usage.TotalTokens,
		}
	}
	return r
}

func (r *Response) toProtocol() *protocol.HookResponse {
	if r == nil {
		return nil
	}
	proto := &protocol.HookResponse{
		Model:   r.Model,
		Content: r.Content,
	}
	if r.Usage != nil {
		proto.Usage = &protocol.HookUsage{
			PromptTokens:     r.Usage.PromptTokens,
			CompletionTokens: r.Usage.CompletionTokens,
			TotalTokens:      r.Usage.TotalTokens,
		}
	}
	return proto
}
