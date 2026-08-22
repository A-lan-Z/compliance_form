package com.example.dcl.application.error;

public final class AssetNotFoundException extends DclException {
    public AssetNotFoundException() {
        super(404, "ASSET_NOT_FOUND", "Asset not found", "The requested fixture asset was not found.");
    }
}
