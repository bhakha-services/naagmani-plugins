package protocol

import (
	"encoding/json"
	"fmt"
	"io"
)

// NewRPCRequest creates a new JSON-RPC 2.0 request payload.
func NewRPCRequest(id int64, method string, params any) (*RPCRequest, error) {
	rawParams, err := json.Marshal(params)
	if err != nil {
		return nil, fmt.Errorf("marshaling params: %w", err)
	}
	return &RPCRequest{
		JSONRPC: "2.0",
		Method:  method,
		Params:  rawParams,
		ID:      id,
	}, nil
}

// NewSuccessResponse creates a standard JSON-RPC 2.0 success response.
func NewSuccessResponse(id int64, result any) (*RPCResponse, error) {
	rawResult, err := json.Marshal(result)
	if err != nil {
		return nil, fmt.Errorf("marshaling result: %w", err)
	}
	return &RPCResponse{
		JSONRPC: "2.0",
		Result:  rawResult,
		ID:      id,
	}, nil
}

// NewErrorResponse creates a standard JSON-RPC 2.0 error response.
func NewErrorResponse(id int64, code int, message string, data any) *RPCResponse {
	return &RPCResponse{
		JSONRPC: "2.0",
		Error: &RPCError{
			Code:    code,
			Message: message,
			Data:    data,
		},
		ID: id,
	}
}

// WriteResponse encodes and writes a JSON-RPC 2.0 response followed by a newline.
func WriteResponse(w io.Writer, resp *RPCResponse) error {
	data, err := json.Marshal(resp)
	if err != nil {
		return fmt.Errorf("marshaling rpc response: %w", err)
	}
	data = append(data, '\n')
	_, err = w.Write(data)
	return err
}
