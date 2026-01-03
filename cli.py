#!/usr/bin/env python3
"""
Command Line Interface for Yukio Japanese Tutor.

This CLI connects to the Yukio API for interactive Japanese language learning.
You can ask questions about Japanese vocabulary, grammar, kanji, and more.
"""

import json
import asyncio
import aiohttp
import argparse
import os
import subprocess
import platform
import warnings
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import sys

# ANSI color codes for better formatting
class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


class YukioCLI:
    """CLI for interacting with the Yukio Japanese Tutor API."""
    
    def __init__(self, base_url: str = "http://localhost:8058", enable_voice: bool = False):
        """Initialize CLI with base URL."""
        self.base_url = base_url.rstrip('/')
        self.session_id = None
        self.user_id = "cli_user"
        self.enable_voice = enable_voice
        self.tts_manager = None
        
        # Initialize TTS if voice is enabled
        if self.enable_voice:
            try:
                from agent.tts import TTSManager
                self.tts_manager = TTSManager()
                if self.tts_manager.is_available():
                    print(f"{Colors.GREEN}✓ Voice (TTS) enabled{Colors.END}")
                else:
                    print(f"{Colors.YELLOW}⚠ Voice requested but Dia TTS not available{Colors.END}")
                    print(f"{Colors.YELLOW}  Local Dia found at: yukio/dia/{Colors.END}")
                    print(f"{Colors.YELLOW}  Install dependencies: cd dia && pip install -e .{Colors.END}")
                    print(f"{Colors.YELLOW}  Or: pip install descript-audio-codec torch torchaudio{Colors.END}")
                    self.enable_voice = False
            except Exception as e:
                print(f"{Colors.YELLOW}⚠ Voice initialization failed: {e}{Colors.END}")
                self.enable_voice = False
        
    def print_banner(self):
        """Print welcome banner."""
        print(f"\n{Colors.CYAN}{Colors.BOLD}{'=' * 60}")
        print("🏯 Yukio - Japanese Language Tutor CLI")
        print("=" * 60)
        print(f"{Colors.WHITE}Connected to: {self.base_url}")
        print(f"Type 'exit', 'quit', or Ctrl+C to exit")
        print(f"Type 'help' for commands")
        print("=" * 60 + f"{Colors.END}\n")
    
    def print_help(self):
        """Print help information."""
        help_text = f"""
{Colors.BOLD}Available Commands:{Colors.END}
  {Colors.GREEN}help{Colors.END}           - Show this help message
  {Colors.GREEN}health{Colors.END}         - Check API health status
  {Colors.GREEN}clear{Colors.END}          - Clear the session
  {Colors.GREEN}exit/quit{Colors.END}      - Exit the CLI
  
{Colors.BOLD}Usage:{Colors.END}
  Simply type your question and press Enter to chat with Yukio.
  Ask about Japanese vocabulary, grammar, kanji, or request practice exercises.
  
{Colors.BOLD}Examples:{Colors.END}
  - "What does こんにちは mean?"
  - "Explain the particle は"
  - "Teach me about kanji 漢字"
  - "Give me an N5 vocabulary quiz"
  - "How do I say 'I want to study Japanese'?"
  - "What's the difference between 見る and 観る?"
"""
        print(help_text)
    
    async def check_health(self) -> bool:
        """Check API health."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        status = data.get('status', 'unknown')
                        if status == 'healthy':
                            print(f"{Colors.GREEN}✓ API is healthy{Colors.END}")
                            return True
                        else:
                            print(f"{Colors.YELLOW}⚠ API status: {status}{Colors.END}")
                            return False
                    else:
                        print(f"{Colors.RED}✗ API health check failed (HTTP {response.status}){Colors.END}")
                        return False
        except Exception as e:
            print(f"{Colors.RED}✗ Failed to connect to API: {e}{Colors.END}")
            return False
    
    def format_tools_used(self, tools: List[Dict[str, Any]]) -> str:
        """Format tools used for display."""
        if not tools:
            return f"{Colors.YELLOW}No tools used{Colors.END}"
        
        formatted = f"{Colors.MAGENTA}{Colors.BOLD}🛠 Tools Used:{Colors.END}\n"
        for i, tool in enumerate(tools, 1):
            tool_name = tool.get('tool_name', 'unknown')
            args = tool.get('args', {})
            
            formatted += f"  {Colors.CYAN}{i}. {tool_name}{Colors.END}"
            
            # Show key arguments for context
            if args:
                key_args = []
                if 'query' in args:
                    key_args.append(f"query='{args['query'][:50]}{'...' if len(args['query']) > 50 else ''}'")
                if 'limit' in args:
                    key_args.append(f"limit={args['limit']}")
                if 'learning_type' in args:
                    key_args.append(f"type='{args['learning_type']}'")
                if 'content' in args:
                    key_args.append(f"content='{args['content'][:30]}...'")
                
                if key_args:
                    formatted += f" ({', '.join(key_args)})"
            
            formatted += "\n"
        
        return formatted
    
    async def stream_chat(self, message: str) -> None:
        """Send message to streaming chat endpoint and display response."""
        request_data = {
            "message": message,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "search_type": "hybrid"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/stream",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"{Colors.RED}✗ API Error ({response.status}): {error_text}{Colors.END}")
                        return
                    
                    print(f"\n{Colors.BOLD}🏯 Yukio:{Colors.END}")
                    
                    tools_used = []
                    full_response = ""
                    
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        
                        if line.startswith('data: '):
                            try:
                                data = json.loads(line[6:])  # Remove 'data: ' prefix
                                
                                if data.get('type') == 'session':
                                    # Store session ID for future requests
                                    self.session_id = data.get('session_id')
                                
                                elif data.get('type') == 'text':
                                    # Stream text content
                                    content = data.get('content', '')
                                    print(content, end='', flush=True)
                                    full_response += content
                                
                                elif data.get('type') == 'tools':
                                    # Store tools used information
                                    tools_used = data.get('tools', [])
                                
                                elif data.get('type') == 'end':
                                    # End of stream
                                    break
                                
                                elif data.get('type') == 'error':
                                    # Handle errors
                                    error_content = data.get('content', 'Unknown error')
                                    print(f"\n{Colors.RED}Error: {error_content}{Colors.END}")
                                    return
                            
                            except json.JSONDecodeError:
                                # Skip malformed JSON
                                continue
                    
                    # Print newline after response
                    print()
                    
                    # Generate voice output if enabled
                    if self.enable_voice and self.tts_manager and self.tts_manager.is_available() and full_response:
                        try:
                            import os
                            from datetime import datetime
                            
                            # Create audio directory
                            audio_dir = Path("yukio_data/audio")
                            audio_dir.mkdir(parents=True, exist_ok=True)
                            
                            # Generate audio filename (use .wav for better compatibility)
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            audio_filename = audio_dir / f"yukio_response_{timestamp}.wav"
                            
                            # Format text for TTS - this now handles Romaji conversion
                            tts_text = self.tts_manager.format_japanese_text(full_response)
                            
                            if not tts_text:
                                print(f"{Colors.YELLOW}⚠ Text could not be formatted for TTS. Skipping voice generation.{Colors.END}")
                            else:
                                # Generate speech (suppress PyTorch warnings during generation)
                                print(f"\n{Colors.CYAN}🔊 Generating voice...{Colors.END}", end="", flush=True)
                                # Suppress warnings during TTS generation
                                import time
                                start_time = time.time()
                                with warnings.catch_warnings():
                                    warnings.simplefilter("ignore")
                                    # Limit text length for faster generation
                                    # Truncate very long responses to keep generation time reasonable
                                    max_text_length = 150  # Rough estimate: ~800 tokens
                                    if len(tts_text) > max_text_length:
                                        tts_text = tts_text[:max_text_length] + "..."
                                        print(f"{Colors.YELLOW} (text truncated for faster generation){Colors.END}", end="", flush=True)
                                    
                                    # Use verbose=False to avoid too much output, but show progress
                                    audio = self.tts_manager.generate_speech(
                                        tts_text,
                                        max_tokens=800,  # Limit tokens for faster generation
                                        verbose=False  # Set to True for detailed progress
                                    )
                                elapsed = time.time() - start_time
                                print(f" ({elapsed:.1f}s)", end="", flush=True)
                                print()  # Newline after generation completes
                                
                                if audio is None:
                                    print(f" {Colors.RED}✗{Colors.END}")
                                    print(f"{Colors.YELLOW}⚠ Failed to generate audio{Colors.END}")
                                else:
                                    # Save audio
                                    save_success = self.tts_manager.save_audio(str(audio_filename), audio)
                                    if save_success:
                                        print(f" {Colors.GREEN}✓{Colors.END}")
                                        print(f"{Colors.CYAN}   Audio saved: {audio_filename}{Colors.END}")
                                        
                                        # Verify file exists
                                        if not audio_filename.exists():
                                            print(f"{Colors.YELLOW}⚠ Audio file not found at: {audio_filename}{Colors.END}")
                                        else:
                                            # Try to play audio (platform-dependent)
                                            try:
                                                system = platform.system()
                                                
                                                # Get absolute path and quote it
                                                abs_path = str(audio_filename.resolve())
                                                
                                                if system == "Darwin":  # macOS
                                                    # Use subprocess.run to play audio and capture potential errors
                                                    try:
                                                        # Check if file is empty
                                                        if audio_filename.stat().st_size == 0:
                                                            print(f"{Colors.YELLOW}⚠ Generated audio file is empty. Skipping playback.{Colors.END}")
                                                        else:
                                                            print(f"{Colors.GREEN}🔊 Playing audio...{Colors.END}")
                                                            result = subprocess.run(
                                                                ["afplay", abs_path],
                                                                capture_output=True,
                                                                text=True,
                                                                check=False  # Don't raise exception on non-zero exit code
                                                            )
                                                            if result.returncode != 0:
                                                                print(f"{Colors.YELLOW}⚠ Audio playback failed with exit code {result.returncode}.{Colors.END}")
                                                                print(f"{Colors.YELLOW}   afplay stderr: {result.stderr.strip()}{Colors.END}")
                                                                print(f"{Colors.CYAN}   You can manually play the file: {abs_path}{Colors.END}")

                                                    except Exception as e:
                                                        print(f"{Colors.YELLOW}⚠ Failed to execute audio playback command: {e}{Colors.END}")
                                                        print(f"{Colors.CYAN}   Audio file saved at: {abs_path}{Colors.END}")
                                                elif system == "Linux":
                                                    try:
                                                        subprocess.Popen(
                                                            ["aplay", abs_path],
                                                            stdout=subprocess.DEVNULL,
                                                            stderr=subprocess.DEVNULL
                                                        )
                                                        print(f"{Colors.GREEN}🔊 Playing audio...{Colors.END}")
                                                    except FileNotFoundError:
                                                        try:
                                                            subprocess.Popen(
                                                                ["paplay", abs_path],
                                                                stdout=subprocess.DEVNULL,
                                                                stderr=subprocess.DEVNULL
                                                            )
                                                            print(f"{Colors.GREEN}🔊 Playing audio...{Colors.END}")
                                                        except FileNotFoundError:
                                                            print(f"{Colors.YELLOW}⚠ No audio player found (aplay/paplay){Colors.END}")
                                                elif system == "Windows":
                                                    try:
                                                        os.startfile(abs_path)
                                                        print(f"{Colors.GREEN}🔊 Playing audio...{Colors.END}")
                                                    except Exception as e:
                                                        print(f"{Colors.YELLOW}⚠ Failed to play audio: {e}{Colors.END}")
                                            except FileNotFoundError as e:
                                                print(f"{Colors.YELLOW}⚠ Audio player not found: {e}{Colors.END}")
                                                print(f"{Colors.CYAN}   You can manually play: {abs_path}{Colors.END}")
                                            except Exception as e:
                                                print(f"{Colors.YELLOW}⚠ Audio playback error: {e}{Colors.END}")
                                                print(f"{Colors.CYAN}   Audio file saved at: {abs_path}{Colors.END}")
                                    else:
                                        print(f" {Colors.RED}✗{Colors.END}")
                                        print(f"{Colors.YELLOW}⚠ Failed to save audio{Colors.END}")
                                
                        except Exception as e:
                            print(f"{Colors.YELLOW}⚠ Voice generation failed: {e}{Colors.END}")
                    
                    # Display tools used
                    if tools_used:
                        print(f"\n{self.format_tools_used(tools_used)}")
                    
                    # Print separator
                    print(f"{Colors.BLUE}{'─' * 60}{Colors.END}")
        
        except aiohttp.ClientError as e:
            print(f"{Colors.RED}✗ Connection error: {e}{Colors.END}")
        except Exception as e:
            print(f"{Colors.RED}✗ Unexpected error: {e}{Colors.END}")
    
    async def run(self):
        """Run the CLI main loop."""
        self.print_banner()
        
        # Check API health
        if not await self.check_health():
            print(f"{Colors.RED}Cannot connect to API. Please ensure the server is running.{Colors.END}")
            return
        
        print(f"{Colors.GREEN}Ready to learn Japanese! Ask me about vocabulary, grammar, kanji, or request practice.{Colors.END}\n")
        
        try:
            while True:
                try:
                    # Get user input
                    user_input = input(f"{Colors.BOLD}George: {Colors.END}").strip()
                    
                    if not user_input:
                        continue
                    
                    # Handle commands
                    if user_input.lower() in ['exit', 'quit']:
                        print(f"{Colors.CYAN}👋 Goodbye!{Colors.END}")
                        break
                    elif user_input.lower() == 'help':
                        self.print_help()
                        continue
                    elif user_input.lower() == 'health':
                        await self.check_health()
                        continue
                    elif user_input.lower() == 'clear':
                        self.session_id = None
                        print(f"{Colors.GREEN}✓ Session cleared{Colors.END}")
                        continue
                    
                    # Send message to agent
                    await self.stream_chat(user_input)
                
                except KeyboardInterrupt:
                    print(f"\n{Colors.CYAN}👋 Goodbye!{Colors.END}")
                    break
                except EOFError:
                    print(f"\n{Colors.CYAN}👋 Goodbye!{Colors.END}")
                    break
        
        except Exception as e:
            print(f"{Colors.RED}✗ CLI error: {e}{Colors.END}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Yukio Japanese Tutor CLI - Interactive Japanese language learning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py                    # Connect to default server (localhost:8058)
  python cli.py --port 8000        # Connect to server on port 8000
  python cli.py --url http://localhost:8058  # Connect to specific URL
        """
    )
    
    parser.add_argument(
        '--url',
        default='http://localhost:8058',
        help='Base URL for the Yukio API (default: http://localhost:8058)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        help='Port number (overrides URL port)'
    )
    
    parser.add_argument(
        '--voice',
        action='store_true',
        help='Enable voice output using Dia TTS (requires Dia installation)'
    )
    
    args = parser.parse_args()
    
    # Build base URL
    base_url = args.url
    if args.port:
        # Extract host from URL and use provided port
        if '://' in base_url:
            protocol, rest = base_url.split('://', 1)
            host = rest.split(':')[0].split('/')[0]
            base_url = f"{protocol}://{host}:{args.port}"
        else:
            base_url = f"http://localhost:{args.port}"
    
    # Create and run CLI
    cli = YukioCLI(base_url, enable_voice=args.voice)
    
    try:
        asyncio.run(cli.run())
    except KeyboardInterrupt:
        print(f"\n{Colors.CYAN}👋 Goodbye!{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}✗ CLI startup error: {e}{Colors.END}")
        sys.exit(1)


if __name__ == "__main__":
    main()