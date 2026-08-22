package com.example.dcl.application.port;

import com.example.dcl.domain.workflow.AuditEvent;

public interface AuditEventRepository {
    void insert(AuditEvent event);
}
