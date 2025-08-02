#!/usr/bin/env python3
"""
CLI testing tool for the Open Deep Think API.
"""
import sys
import json
import time
import argparse
import requests
from typing import Optional, Dict, Any


class DeepThinkCLI:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        
    def health_check(self, detailed: bool = False) -> Dict[str, Any]:
        """Check the health of the service."""
        try:
            params = {}
            if detailed:
                params = {"check_api": "true", "include_details": "true"}
            
            response = requests.get(f"{self.base_url}/health", params=params, timeout=10)
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}", "data": response.text}
                
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}
    
    def think(self, query: str, n_paths: int = 4, top_k: int = 2, timeout: int = 60) -> Dict[str, Any]:
        """Send a query to the Deep Think pipeline."""
        try:
            payload = {
                "query": query,
                "n_paths": n_paths,
                "top_k": top_k,
                "timeout": timeout
            }
            
            print(f"🧠 Sending query to Deep Think pipeline...")
            print(f"   Query: {query}")
            print(f"   Paths: {n_paths}, Top-K: {top_k}, Timeout: {timeout}s")
            print()
            
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/think",
                json=payload,
                timeout=timeout + 10  # Add buffer to request timeout
            )
            execution_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "data": data,
                    "execution_time": execution_time
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "data": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
                    "execution_time": execution_time
                }
                
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}
    
    def info(self) -> Dict[str, Any]:
        """Get service information."""
        try:
            response = requests.get(f"{self.base_url}/info", timeout=10)
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}", "data": response.text}
                
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}


def print_json(data: Dict[str, Any], indent: int = 2):
    """Pretty print JSON data."""
    print(json.dumps(data, indent=indent, default=str))


def main():
    parser = argparse.ArgumentParser(description="Open Deep Think CLI Testing Tool")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the service")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Health check command
    health_parser = subparsers.add_parser("health", help="Check service health")
    health_parser.add_argument("--detailed", action="store_true", help="Include detailed component info")
    
    # Think command
    think_parser = subparsers.add_parser("think", help="Send a query to Deep Think")
    think_parser.add_argument("query", help="The question to ask")
    think_parser.add_argument("--paths", type=int, default=4, help="Number of thinking paths (default: 4)")
    think_parser.add_argument("--top-k", type=int, default=2, help="Number of top candidates (default: 2)")
    think_parser.add_argument("--timeout", type=int, default=60, help="Timeout in seconds (default: 60)")
    think_parser.add_argument("--compact", action="store_true", help="Show compact output")
    
    # Info command
    info_parser = subparsers.add_parser("info", help="Get service information")
    
    # Interactive command
    interactive_parser = subparsers.add_parser("interactive", help="Start interactive mode")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = DeepThinkCLI(args.url)
    
    if args.command == "health":
        print("🏥 Checking service health...")
        result = cli.health_check(detailed=args.detailed)
        
        if result["success"]:
            data = result["data"]
            status = data.get("status", "unknown")
            
            if status == "healthy":
                print("✅ Service is healthy!")
            elif status == "degraded":
                print("⚠️  Service is degraded but operational")
            else:
                print(f"❌ Service status: {status}")
            
            if args.detailed and "components" in data:
                print("\n📊 Component Details:")
                print_json(data["components"])
        else:
            print(f"❌ Health check failed: {result['error']}")
            
    elif args.command == "think":
        result = cli.think(args.query, args.paths, args.top_k, args.timeout)
        
        if result["success"]:
            data = result["data"]
            exec_time = result["execution_time"]
            
            print("✅ Deep Think completed successfully!")
            print(f"⏱️  Execution time: {exec_time:.2f} seconds")
            print()
            
            if args.compact:
                print("💡 Answer:")
                print(data["answer"])
                print()
                metadata = data.get("metadata", {})
                print(f"📊 Metadata: {metadata.get('candidates_generated', 0)} candidates, "
                      f"{metadata.get('confidence_level', 'unknown')} confidence")
            else:
                print("💡 Answer:")
                print(data["answer"])
                print()
                print("📊 Metadata:")
                print_json(data["metadata"])
                
        else:
            exec_time = result.get("execution_time", 0)
            print(f"❌ Deep Think failed after {exec_time:.2f} seconds")
            print(f"Error: {result['error']}")
            if "data" in result:
                print("Response:")
                if isinstance(result["data"], dict):
                    print_json(result["data"])
                else:
                    print(result["data"])
                    
    elif args.command == "info":
        print("ℹ️  Getting service information...")
        result = cli.info()
        
        if result["success"]:
            print("✅ Service information retrieved!")
            print_json(result["data"])
        else:
            print(f"❌ Failed to get service info: {result['error']}")
            
    elif args.command == "interactive":
        print("🎮 Starting interactive mode...")
        print("Type 'help' for commands, 'quit' to exit")
        print()
        
        while True:
            try:
                user_input = input("DeepThink> ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                    
                elif user_input.lower() == 'help':
                    print("Available commands:")
                    print("  help          - Show this help")
                    print("  health        - Check service health")
                    print("  info          - Get service info")
                    print("  quit/exit/q   - Exit interactive mode")
                    print("  <question>    - Ask a question to Deep Think")
                    print()
                    
                elif user_input.lower() == 'health':
                    result = cli.health_check(detailed=True)
                    if result["success"]:
                        status = result["data"].get("status", "unknown")
                        print(f"Health: {status}")
                    else:
                        print(f"Health check failed: {result['error']}")
                        
                elif user_input.lower() == 'info':
                    result = cli.info()
                    if result["success"]:
                        service_info = result["data"].get("service", {})
                        config_info = result["data"].get("configuration", {})
                        print(f"Service: {service_info.get('name', 'unknown')} v{service_info.get('version', 'unknown')}")
                        print(f"Config: {config_info.get('default_n_paths', 'unknown')} paths, "
                              f"{config_info.get('pipeline_timeout', 'unknown')}s timeout")
                    else:
                        print(f"Info failed: {result['error']}")
                        
                elif user_input:
                    # Treat as a question
                    result = cli.think(user_input, n_paths=4, top_k=2, timeout=60)
                    
                    if result["success"]:
                        data = result["data"]
                        exec_time = result["execution_time"]
                        
                        print(f"💡 Answer (took {exec_time:.1f}s):")
                        print(data["answer"])
                        
                        metadata = data.get("metadata", {})
                        confidence = metadata.get("confidence_level", "unknown")
                        candidates = metadata.get("candidates_generated", 0)
                        print(f"📊 {candidates} candidates, {confidence} confidence")
                        print()
                    else:
                        print(f"❌ Error: {result['error']}")
                        print()
                        
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except EOFError:
                print("\n👋 Goodbye!")
                break


if __name__ == "__main__":
    main()