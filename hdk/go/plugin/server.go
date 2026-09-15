package plugin

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"os"
	"sync"
	"time"

	"github.com/bhakha-services/naagmani-plugins/hdk/go/protocol"
)

type server struct {
	plugin    *Plugin
	in        io.Reader
	out       io.Writer
	writeMu   sync.Mutex
	startedAt time.Time
	logger    *log.Logger
}

func newServer(p *Plugin, in io.Reader, out io.Writer) *server {
	return &server{
		plugin:    p,
		in:        in,
		out:       out,
		startedAt: time.Now(),
		logger:    log.New(os.Stderr, fmt.Sprintf("[%s] ", p.name), log.LstdFlags),
	}
}

func (s *server) serve() error {
	scanner := bufio.NewScanner(s.in)
	buf := make([]byte, 64*1024)
	scanner.Buffer(buf, 2*1024*1024) // up to 2MB line length

	for scanner.Scan() {
		line := scanner.Bytes()
		trimmed := bytes.TrimSpace(line)
		if len(trimmed) == 0 {
			continue
		}

		var req protocol.RPCRequest
		if err := json.Unmarshal(trimmed, &req); err != nil {
			s.logger.Printf("failed parsing JSON-RPC line: %v", err)
			_ = s.sendError(0, protocol.CodeParseError, "Parse error", nil)
			continue
		}

		shouldExit, err := s.handleRequest(&req)
		if err != nil {
			s.logger.Printf("error handling method %q: %v", req.Method, err)
		}
		if shouldExit {
			return nil
		}
	}

	if err := scanner.Err(); err != nil && err != io.EOF {
		return fmt.Errorf("reading stdin: %w", err)
	}

	return nil
}

func (s *server) handleRequest(req *protocol.RPCRequest) (bool, error) {
	if req.JSONRPC != "2.0" {
		return false, s.sendError(req.ID, protocol.CodeInvalidRequest, "Invalid JSON-RPC version, expected '2.0'", nil)
	}

	switch req.Method {
	case protocol.MethodRegister:
		var params protocol.RegisterParams
		if len(req.Params) > 0 {
			if err := json.Unmarshal(req.Params, &params); err != nil {
				return false, s.sendError(req.ID, protocol.CodeInvalidParams, "Invalid registration params", nil)
			}
		}

		// Validate protocol version compatibility
		if params.ProtocolVersion != "" && params.ProtocolVersion != protocol.ProtocolVersion {
			errMsg := fmt.Sprintf("incompatible protocol version: expected %s, got %s", protocol.ProtocolVersion, params.ProtocolVersion)
			s.logger.Printf(errMsg)
			return false, s.sendError(req.ID, protocol.CodeProtocolVersionMismatch, errMsg, nil)
		}

		caps := s.plugin.capabilities
		if len(caps) == 0 {
			caps = []string{"core"}
		}

		res := protocol.RegisterResult{
			Status:          "ok",
			ProtocolVersion: protocol.ProtocolVersion,
			Capabilities:    caps,
			Message:         fmt.Sprintf("%s v%s initialized successfully", s.plugin.name, s.plugin.version),
		}
		return false, s.sendSuccess(req.ID, res)

	case protocol.MethodHealth:
		uptime := time.Since(s.startedAt).Round(time.Second).String()
		res := protocol.HealthResult{
			Status:  "healthy",
			Uptime:  uptime,
			Message: "Plugin operational",
		}
		return false, s.sendSuccess(req.ID, res)

	case protocol.MethodShutdown:
		res := protocol.ShutdownResult{
			Status: "shutting_down",
		}
		_ = s.sendSuccess(req.ID, res)
		return true, nil

	case protocol.MethodHookInvoke:
		var params protocol.HookInvokeParams
		if err := json.Unmarshal(req.Params, &params); err != nil {
			return false, s.sendError(req.ID, protocol.CodeInvalidParams, "Invalid hook invoke params", nil)
		}

		decision := s.dispatchHook(&params)
		return false, s.sendSuccess(req.ID, decision)

	default:
		return false, s.sendError(req.ID, protocol.CodeMethodNotFound, fmt.Sprintf("Method %q not found", req.Method), nil)
	}
}

func (s *server) dispatchHook(params *protocol.HookInvokeParams) protocol.HookDecision {
	devCtx := contextFromProtocol(&params.Context)

	switch params.Hook {
	case protocol.HookRequestBefore:
		if s.plugin.onRequestBefore != nil {
			devReq := requestFromProtocol(params.Context.Request)
			res, err := s.plugin.onRequestBefore(devCtx, devReq)
			if err != nil {
				s.logger.Printf("handler error on %s: %v", params.Hook, err)
				return protocol.HookDecision{
					Decision: protocol.DecisionContinue,
					Error:    err.Error(),
				}
			}
			return res.toProtocolDecision()
		}

	case protocol.HookRequestAfter:
		if s.plugin.onRequestAfter != nil {
			devReq := requestFromProtocol(params.Context.Request)
			res, err := s.plugin.onRequestAfter(devCtx, devReq)
			if err != nil {
				s.logger.Printf("handler error on %s: %v", params.Hook, err)
				return protocol.HookDecision{
					Decision: protocol.DecisionContinue,
					Error:    err.Error(),
				}
			}
			// request.after is read-only
			dec := res.toProtocolDecision()
			dec.ModifiedRequest = nil
			return dec
		}

	case protocol.HookResponseBefore:
		if s.plugin.onResponseBefore != nil {
			devResp := responseFromProtocol(params.Context.Response)
			res, err := s.plugin.onResponseBefore(devCtx, devResp)
			if err != nil {
				s.logger.Printf("handler error on %s: %v", params.Hook, err)
				return protocol.HookDecision{
					Decision: protocol.DecisionContinue,
					Error:    err.Error(),
				}
			}
			return res.toProtocolDecision()
		}

	case protocol.HookResponseAfter:
		if s.plugin.onResponseAfter != nil {
			devResp := responseFromProtocol(params.Context.Response)
			res, err := s.plugin.onResponseAfter(devCtx, devResp)
			if err != nil {
				s.logger.Printf("handler error on %s: %v", params.Hook, err)
				return protocol.HookDecision{
					Decision: protocol.DecisionContinue,
					Error:    err.Error(),
				}
			}
			// response.after is audit only
			dec := res.toProtocolDecision()
			dec.ModifiedResponse = nil
			return dec
		}
	}

	// Default fallback: continue with no modification
	return protocol.HookDecision{
		Decision: protocol.DecisionContinue,
	}
}

func (s *server) sendSuccess(id int64, result any) error {
	s.writeMu.Lock()
	defer s.writeMu.Unlock()

	resp, err := protocol.NewSuccessResponse(id, result)
	if err != nil {
		return err
	}
	return protocol.WriteResponse(s.out, resp)
}

func (s *server) sendError(id int64, code int, message string, data any) error {
	s.writeMu.Lock()
	defer s.writeMu.Unlock()

	resp := protocol.NewErrorResponse(id, code, message, data)
	return protocol.WriteResponse(s.out, resp)
}
