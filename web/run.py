"""Convenience launcher: python -m web.run [--port 8000]"""
import argparse
import sys
import uvicorn


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--reload", action="store_true",
                   help="auto-reload on file changes (dev mode)")
    args = p.parse_args()
    print(f"qrfix GUI on http://{args.host}:{args.port}")
    uvicorn.run("web.app:app", host=args.host, port=args.port,
                reload=args.reload)


if __name__ == "__main__":
    main()
