package plugin

import (
	"strings"

	"github.com/bhakha-services/naagmani-plugins/hdk/go/protocol"
)

// Message is a single chat message.
type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// Request represents an AI inference request.
type Request struct {
	Model    string    `json:"model"`
	Messages []Message `json:"messages"`
	Stream   bool      `json:"stream"`
}

// PromptText returns the combined text of all user messages in the request.
func (r *Request) PromptText() string {
	var parts []string
	for _, m := range r.Messages {
		if m.Role == "user" {
			parts = append(parts, m.Content)
		}
	}
	return strings.Join(parts, "\n")
}

// AddMessage appends a new message to the chat history.
func (r *Request) AddMessage(role, content string) {
	r.Messages = append(r.Messages, Message{
		Role:    role,
		Content: content,
	})
}

func requestFromProtocol(req *protocol.HookRequest) *Request {
	if req == nil {
		return nil
	}
	r := &Request{
		Model:  req.Model,
		Stream: req.Stream,
	}
	for _, m := range req.Messages {
		r.Messages = append(r.Messages, Message{
			Role:    m.Role,
			Content: m.Content,
		})
	}
	return r
}

func (r *Request) toProtocol() *protocol.HookRequest {
	if r == nil {
		return nil
	}
	proto := &protocol.HookRequest{
		Model:  r.Model,
		Stream: r.Stream,
	}
	for _, m := range r.Messages {
		proto.Messages = append(proto.Messages, protocol.HookMessage{
			Role:    m.Role,
			Content: m.Content,
		})
	}
	return proto
}
