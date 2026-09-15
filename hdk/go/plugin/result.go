package plugin

import "github.com/bhakha-services/naagmani-plugins/hdk/go/protocol"

// Result represents the plugin's decision for a hook.
type Result struct {
	decision         string
	blockReason      string
	modifiedRequest  *Request
	modifiedResponse *Response
}

// Continue instructs the pipeline to proceed normally without modifications.
func Continue() *Result {
	return &Result{
		decision: protocol.DecisionContinue,
	}
}

// Block instructs the pipeline to immediately reject the request with HTTP 403.
func Block(reason string) *Result {
	return &Result{
		decision:    protocol.DecisionBlock,
		blockReason: reason,
	}
}

// ModifyRequest instructs the pipeline to replace the request with the modified version.
func ModifyRequest(req *Request) *Result {
	return &Result{
		decision:        protocol.DecisionModify,
		modifiedRequest: req,
	}
}

// ModifyResponse instructs the pipeline to replace the response with the modified version.
func ModifyResponse(resp *Response) *Result {
	return &Result{
		decision:         protocol.DecisionModify,
		modifiedResponse: resp,
	}
}

func (r *Result) toProtocolDecision() protocol.HookDecision {
	if r == nil {
		return protocol.HookDecision{
			Decision: protocol.DecisionContinue,
		}
	}
	return protocol.HookDecision{
		Decision:         r.decision,
		BlockReason:      r.blockReason,
		ModifiedRequest:  r.modifiedRequest.toProtocol(),
		ModifiedResponse: r.modifiedResponse.toProtocol(),
	}
}
