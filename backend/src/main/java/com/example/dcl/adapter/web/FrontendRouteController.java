package com.example.dcl.adapter.web;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class FrontendRouteController {

    @GetMapping("/compliance-form")
    public String complianceForm() {
        return "forward:/index.html";
    }
}
