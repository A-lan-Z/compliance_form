package com.example.dcl.adapter.web;

import com.example.dcl.application.WorkflowResult;
import com.example.dcl.application.WorkflowService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import java.net.URI;
import java.security.Principal;
import java.util.UUID;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/workflows")
public class WorkflowController {
    private final WorkflowService workflowService;

    public WorkflowController(WorkflowService workflowService) {
        this.workflowService = workflowService;
    }

    @PostMapping("/open")
    public ResponseEntity<WorkflowResponse> open(
            @Valid @RequestBody OpenWorkflowRequest request,
            Principal principal,
            HttpServletRequest servletRequest) {
        WorkflowResult result = workflowService.open(
                principal.getName(), request.assetUrn(), request.formKey(), RequestIdFilter.requestId(servletRequest));
        WorkflowResponse response = WorkflowResponse.from(result);
        if (result.created()) {
            return ResponseEntity.created(URI.create("/api/v1/workflows/" + result.workflow().id())).body(response);
        }
        return ResponseEntity.ok(response);
    }

    @GetMapping("/{workflowId}")
    public WorkflowResponse get(@PathVariable UUID workflowId, Principal principal) {
        return WorkflowResponse.from(workflowService.get(principal.getName(), workflowId));
    }

    @PutMapping("/{workflowId}/draft")
    public WorkflowResponse saveDraft(
            @PathVariable UUID workflowId,
            @Valid @RequestBody SaveDraftRequest request,
            Principal principal,
            HttpServletRequest servletRequest) {
        return WorkflowResponse.from(workflowService.saveDraft(
                principal.getName(),
                workflowId,
                request.expectedVersion(),
                request.values(),
                RequestIdFilter.requestId(servletRequest)));
    }
}
