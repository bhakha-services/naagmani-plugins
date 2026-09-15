package plugin_test

import (
	"bufio"
	"encoding/json"
	"io"
	"strings"
	"testing"

	"github.com/bhakha-services/naagmani-plugins/hdk/go/plugin"
	"github.com/bhakha-services/naagmani-plugins/hdk/go/protocol"
)

type harness struct {
	inReader   *io.PipeReader
	inWriter   *io.PipeWriter
	outReader  *io.PipeReader
	outWriter  *io.PipeWriter
	p          *plugin.Plugin
	serverDone chan error
	scanner    *bufio.Scanner
}

func newHarness(p *plugin.Plugin) *harness {
	inReader, inWriter := io.Pipe()
	outReader, outWriter := io.Pipe()
	h := &harness{
		inReader:   inReader,
		inWriter:   inWriter,
		outReader:  outReader,
		outWriter:  outWriter,
		p:          p,
		serverDone: make(chan error, 1),
		scanner:    bufio.NewScanner(outReader),
	}
	go func() {
		h.serverDone <- p.Serve(inReader, outWriter)
		_ = outWriter.Close()
	}()
	return h
}

func (h *harness) call(req *protocol.RPCRequest) (*protocol.RPCResponse, error) {
	data, err := json.Marshal(req)
	if err != nil {
		return nil, err
	}
	data = append(data, '\n')
	if _, err := h.inWriter.Write(data); err != nil {
		return nil, err
	}

	if !h.scanner.Scan() {
		return nil, io.EOF
	}

	var resp protocol.RPCResponse
	if err := json.Unmarshal(h.scanner.Bytes(), &resp); err != nil {
		return nil, err
	}
	return &resp, nil
}

func (h *harness) close() {
	_ = h.inWriter.Close()
	<-h.serverDone
}

func TestHDK_RegistrationHandshake(t *testing.T) {
	p := plugin.New("test-plugin").
		Version("1.2.3").
		Capabilities("test_guard")

	h := newHarness(p)
	defer h.close()

	// 1. Valid handshake
	req, _ := protocol.NewRPCRequest(1, protocol.MethodRegister, protocol.RegisterParams{
		PluginName:      "test-plugin",
		PluginVersion:   "1.2.3",
		APIVersion:      "v1",
		ProtocolVersion: protocol.ProtocolVersion,
	})

	resp, err := h.call(req)
	if err != nil {
		t.Fatalf("call failed: %v", err)
	}
	if resp.Error != nil {
		t.Fatalf("expected success, got error: %+v", resp.Error)
	}

	var res protocol.RegisterResult
	if err := json.Unmarshal(resp.Result, &res); err != nil {
		t.Fatalf("unmarshal result: %v", err)
	}
	if res.Status != "ok" {
		t.Errorf("expected status 'ok', got %q", res.Status)
	}
	if res.ProtocolVersion != protocol.ProtocolVersion {
		t.Errorf("expected protocol version %q, got %q", protocol.ProtocolVersion, res.ProtocolVersion)
	}
}

func TestHDK_ProtocolVersionMismatch(t *testing.T) {
	p := plugin.New("test-plugin").Version("1.0.0")
	h := newHarness(p)
	defer h.close()

	req, _ := protocol.NewRPCRequest(1, protocol.MethodRegister, protocol.RegisterParams{
		ProtocolVersion: "naagmani.plugin/v99",
	})

	resp, err := h.call(req)
	if err != nil {
		t.Fatalf("call failed: %v", err)
	}
	if resp.Error == nil {
		t.Fatal("expected protocol mismatch error, got success")
	}
	if resp.Error.Code != protocol.CodeProtocolVersionMismatch {
		t.Errorf("expected code %d, got %d", protocol.CodeProtocolVersionMismatch, resp.Error.Code)
	}
}

func TestHDK_HealthProbe(t *testing.T) {
	p := plugin.New("test-plugin")
	h := newHarness(p)
	defer h.close()

	req, _ := protocol.NewRPCRequest(42, protocol.MethodHealth, protocol.HealthParams{})
	resp, err := h.call(req)
	if err != nil {
		t.Fatalf("call failed: %v", err)
	}
	if resp.Error != nil {
		t.Fatalf("expected success, got error: %+v", resp.Error)
	}

	var res protocol.HealthResult
	if err := json.Unmarshal(resp.Result, &res); err != nil {
		t.Fatalf("unmarshal result: %v", err)
	}
	if res.Status != "healthy" {
		t.Errorf("expected status 'healthy', got %q", res.Status)
	}
}

func TestHDK_HookRequestBefore_Continue(t *testing.T) {
	invoked := false
	p := plugin.New("test-plugin").
		OnRequestBefore(func(ctx *plugin.Context, req *plugin.Request) (*plugin.Result, error) {
			invoked = true
			if req.Model != "gpt-4" {
				t.Errorf("expected model 'gpt-4', got %q", req.Model)
			}
			return plugin.Continue(), nil
		})

	h := newHarness(p)
	defer h.close()

	hookReq, _ := protocol.NewRPCRequest(10, protocol.MethodHookInvoke, protocol.HookInvokeParams{
		Hook: protocol.HookRequestBefore,
		Context: protocol.HookContext{
			Hook:      protocol.HookRequestBefore,
			RequestID: "req_test_123",
			Request: &protocol.HookRequest{
				Model: "gpt-4",
				Messages: []protocol.HookMessage{
					{Role: "user", Content: "Hello world"},
				},
			},
		},
	})

	resp, err := h.call(hookReq)
	if err != nil {
		t.Fatalf("call failed: %v", err)
	}
	if resp.Error != nil {
		t.Fatalf("got error: %+v", resp.Error)
	}
	if !invoked {
		t.Error("expected handler to be invoked")
	}

	var dec protocol.HookDecision
	if err := json.Unmarshal(resp.Result, &dec); err != nil {
		t.Fatalf("unmarshal decision: %v", err)
	}
	if dec.Decision != "continue" {
		t.Errorf("expected decision 'continue', got %q", dec.Decision)
	}
}

func TestHDK_HookRequestBefore_Block(t *testing.T) {
	p := plugin.New("test-plugin").
		OnRequestBefore(func(ctx *plugin.Context, req *plugin.Request) (*plugin.Result, error) {
			if strings.Contains(req.PromptText(), "danger") {
				return plugin.Block("Prohibited dangerous prompt"), nil
			}
			return plugin.Continue(), nil
		})

	h := newHarness(p)
	defer h.close()

	hookReq, _ := protocol.NewRPCRequest(11, protocol.MethodHookInvoke, protocol.HookInvokeParams{
		Hook: protocol.HookRequestBefore,
		Context: protocol.HookContext{
			Hook: protocol.HookRequestBefore,
			Request: &protocol.HookRequest{
				Model: "mock/gpt-4",
				Messages: []protocol.HookMessage{
					{Role: "user", Content: "this is danger territory"},
				},
			},
		},
	})

	resp, err := h.call(hookReq)
	if err != nil {
		t.Fatalf("call failed: %v", err)
	}

	var dec protocol.HookDecision
	if err := json.Unmarshal(resp.Result, &dec); err != nil {
		t.Fatalf("unmarshal decision: %v", err)
	}
	if dec.Decision != "block" {
		t.Errorf("expected decision 'block', got %q", dec.Decision)
	}
	if dec.BlockReason != "Prohibited dangerous prompt" {
		t.Errorf("expected block reason, got %q", dec.BlockReason)
	}
}

func TestHDK_HookResponseBefore_Modify(t *testing.T) {
	p := plugin.New("test-plugin").
		OnResponseBefore(func(ctx *plugin.Context, resp *plugin.Response) (*plugin.Result, error) {
			if strings.Contains(resp.Content, "SECRET") {
				resp.Content = strings.ReplaceAll(resp.Content, "SECRET", "REDACTED")
				return plugin.ModifyResponse(resp), nil
			}
			return plugin.Continue(), nil
		})

	h := newHarness(p)
	defer h.close()

	hookReq, _ := protocol.NewRPCRequest(12, protocol.MethodHookInvoke, protocol.HookInvokeParams{
		Hook: protocol.HookResponseBefore,
		Context: protocol.HookContext{
			Hook: protocol.HookResponseBefore,
			Response: &protocol.HookResponse{
				Model:   "mock/gpt-4",
				Content: "Here is your SECRET key",
			},
		},
	})

	resp, err := h.call(hookReq)
	if err != nil {
		t.Fatalf("call failed: %v", err)
	}

	var dec protocol.HookDecision
	if err := json.Unmarshal(resp.Result, &dec); err != nil {
		t.Fatalf("unmarshal decision: %v", err)
	}
	if dec.Decision != "modify" {
		t.Errorf("expected decision 'modify', got %q", dec.Decision)
	}
	if dec.ModifiedResponse == nil || dec.ModifiedResponse.Content != "Here is your REDACTED key" {
		t.Errorf("expected modified response, got %+v", dec.ModifiedResponse)
	}
}

func TestHDK_MethodNotFound(t *testing.T) {
	p := plugin.New("test-plugin")
	h := newHarness(p)
	defer h.close()

	req, _ := protocol.NewRPCRequest(99, "unknown.method", map[string]any{})
	resp, err := h.call(req)
	if err != nil {
		t.Fatalf("call failed: %v", err)
	}
	if resp.Error == nil || resp.Error.Code != protocol.CodeMethodNotFound {
		t.Errorf("expected method not found error, got %+v", resp.Error)
	}
}

func TestHDK_GracefulShutdown(t *testing.T) {
	p := plugin.New("test-plugin")
	h := newHarness(p)

	req, _ := protocol.NewRPCRequest(100, protocol.MethodShutdown, protocol.ShutdownParams{})
	resp, err := h.call(req)
	if err != nil {
		t.Fatalf("call failed: %v", err)
	}

	var res protocol.ShutdownResult
	if err := json.Unmarshal(resp.Result, &res); err != nil {
		t.Fatalf("unmarshal result: %v", err)
	}
	if res.Status != "shutting_down" {
		t.Errorf("expected status 'shutting_down', got %q", res.Status)
	}

	// Server should exit gracefully
	select {
	case err := <-h.serverDone:
		if err != nil {
			t.Errorf("expected clean server exit, got %v", err)
		}
	}
}
