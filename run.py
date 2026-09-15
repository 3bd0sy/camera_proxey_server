"""Entry point — runs the FastAPI server with optional HTTPS support."""

import uvicorn
from app.core.config import get_config

if __name__ == "__main__":
    cfg = get_config()

    run_kwargs = {
        "host": cfg.server.host,
        "port": cfg.server.port,
        "log_level": "info",
        "reload": False,
    }

    if cfg.server.ssl.enabled:
        if not cfg.server.ssl.cert_file or not cfg.server.ssl.key_file:
            raise ValueError(
                "SSL is enabled but cert_file or key_file is missing in config.yaml"
            )
        print("\n\n\nssl:", cfg.server.ssl)
        run_kwargs["ssl_certfile"] = cfg.server.ssl.cert_file
        run_kwargs["ssl_keyfile"] = cfg.server.ssl.key_file
        if cfg.server.ssl.ssl_version:
            run_kwargs["ssl_version"] = 17  # TLSv1_2
        print(f"🔒 HTTPS enabled: {cfg.server.ssl.cert_file}")
    else:
        print("⚠️  HTTPS disabled — using HTTP (not secure)")

    uvicorn.run("app.main:app", **run_kwargs)
