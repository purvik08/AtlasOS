"""Voice management commands for Atlas OS.

Provides wake word detection, speech-to-text, and text-to-speech.
"""

from __future__ import annotations

import asyncio
import json
import sys

import click
from rich.console import Console
from rich.table import Table

from atlas.voice.core import VoiceConfig, VoiceManager

console = Console()


def _get_voice_manager(ctx: click.Context) -> VoiceManager:
    """Get or create VoiceManager from context."""
    manager: VoiceManager | None = ctx.obj.get("voice_manager")
    if manager is None:
        app = ctx.obj["app"]
        ai_cfg = getattr(app.config, "ai", None)
        config = VoiceConfig(
            wake_word_model=(
                getattr(ai_cfg, "wake_word_model", "alexa") if ai_cfg else "alexa"
            ),
            stt_model=(
                getattr(ai_cfg, "stt_model", "base.en") if ai_cfg else "base.en"
            ),
            tts_model=(
                getattr(ai_cfg, "tts_model", "en_US-lessac-medium")
                if ai_cfg
                else "en_US-lessac-medium"
            ),
        )
        manager = VoiceManager(config)
        asyncio.run(manager.initialize())
        ctx.obj["voice_manager"] = manager
    return manager


@click.group(name="voice")
def voice_group() -> None:
    """Manage voice interaction features."""
    pass


@voice_group.command(name="status")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def voice_status(ctx: click.Context, output_json: bool) -> None:
    """Show voice system status."""
    manager = _get_voice_manager(ctx)
    status = manager.get_status()

    if output_json:
        console.print(json.dumps(status, indent=2))
        return

    table = Table(title="Voice System Status", box=None)
    table.add_column("Component", style="cyan")
    table.add_column("Available", style="green")
    table.add_column("Details", style="white")

    # NOTE: key is "wake_word" (not "wake") — matches VoiceManager.get_status()
    wake = status["wake_word"]
    table.add_row(
        "Wake Word",
        "[green]yes[/]" if wake["available"] else "[red]no[/]",
        f"Model: {wake['model']}, Threshold: {wake['threshold']}",
    )

    stt = status["stt"]
    table.add_row(
        "Speech-to-Text",
        "[green]yes[/]" if stt["available"] else "[red]no[/]",
        f"Model: {stt['model']}, Device: {stt['device']}",
    )

    tts = status["tts"]
    table.add_row(
        "Text-to-Speech",
        "[green]yes[/]" if tts["available"] else "[red]no[/]",
        f"Model: {tts['model']}",
    )

    audio = status["audio"]
    table.add_row(
        "Audio I/O",
        "[green]yes[/]" if audio["available"] else "[red]no[/]",
        f"Backend: {audio.get('backend', 'unknown')}, "
        f"Sample Rate: {audio['sample_rate']} Hz, "
        f"Inputs: {audio.get('input_devices', 0)}, "
        f"Outputs: {audio.get('output_devices', 0)}",
    )

    console.print(table)

    if not all([wake["available"], stt["available"], tts["available"], audio["available"]]):
        console.print("\n[yellow]Missing dependencies. Install with:[/]")
        if not wake["available"]:
            console.print("  pip install openwakeword")
        if not stt["available"]:
            console.print("  pip install faster-whisper")
        if not tts["available"]:
            console.print("  pip install piper-tts")
        if not audio["available"]:
            console.print("  pip install sounddevice")


@voice_group.command(name="test-wake")
@click.option("--model", default="alexa", help="Wake word model to use")
@click.option("--threshold", default=0.5, type=float, help="Detection threshold")
@click.pass_context
def voice_test_wake(ctx: click.Context, model: str, threshold: float) -> None:
    """Test wake word detection."""
    manager = _get_voice_manager(ctx)
    manager.config.wake_word_model = model
    manager.config.wake_word_threshold = threshold

    console.print(f"[cyan]Testing wake word: {model} (threshold={threshold})[/]")
    console.print("[dim]Say the wake word... Press Ctrl+C to stop[/]")

    try:
        result = asyncio.run(manager.listen_for_wake_word())
        if result:
            console.print("[green]Wake word detected![/]")
        else:
            console.print("[yellow]Stopped without detection.[/]")
    except KeyboardInterrupt:
        console.print("\n[dim]Stopped.[/]")
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/]")
        sys.exit(1)


@voice_group.command(name="test-stt")
@click.option("--duration", "-d", default=5.0, type=float, help="Recording duration in seconds")
@click.option("--model", default="base.en", help="Whisper model to use")
@click.pass_context
def voice_test_stt(ctx: click.Context, duration: float, model: str) -> None:
    """Test speech-to-text transcription."""
    manager = _get_voice_manager(ctx)
    manager.config.stt_model = model

    console.print(f"[cyan]Recording for {duration}s... Speak now![/]")

    try:
        text = asyncio.run(manager.listen_and_transcribe(duration))
        if text:
            console.print(f"[green]Transcribed:[/] {text}")
        else:
            console.print("[yellow]No speech detected.[/]")
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/]")
        sys.exit(1)


@voice_group.command(name="test-tts")
@click.argument("text")
@click.option("--model", default="en_US-lessac-medium", help="Piper voice model")
@click.pass_context
def voice_test_tts(ctx: click.Context, text: str, model: str) -> None:
    """Test text-to-speech synthesis."""
    manager = _get_voice_manager(ctx)
    manager.config.tts_model = model

    console.print(f"[cyan]Synthesizing: {text}[/]")

    try:
        success = asyncio.run(manager.speak(text))
        if success:
            console.print("[green]Playback complete.[/]")
        else:
            console.print("[red]Synthesis failed.[/]")
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/]")
        sys.exit(1)


def _get_os_ai(ctx: click.Context) -> Any:
    """Get or create AtlasOSAI from context."""
    os_ai = ctx.obj.get("os_ai") if ctx.obj else None
    if os_ai is not None:
        return os_ai

    app = ctx.obj.get("app") if ctx.obj else None
    if app and hasattr(app, "container") and "os_ai" in app.container:
        os_ai = app.container.resolve("os_ai")
        if ctx.obj:
            ctx.obj["os_ai"] = os_ai
        return os_ai

    try:
        from atlas.ai.os_ai import AtlasOSAI
        from atlas.ai.tools import create_default_tool_registry

        ai_mgr = getattr(app, "ai_manager", None) if app else None
        rag_svc = getattr(app, "rag_service", None) if app else None
        container = getattr(app, "container", None) if app else None
        manager = _get_voice_manager(ctx)
        os_ai = AtlasOSAI(
            ai_manager=ai_mgr,
            rag_service=rag_svc,
            tool_registry=create_default_tool_registry(
                container=container,
                rag_service=rag_svc,
                voice_manager=manager,
            ),
            container=container,
        )
        if ctx.obj:
            ctx.obj["os_ai"] = os_ai
        return os_ai
    except Exception:
        return None


@voice_group.command(name="converse")
@click.option("--model", default="base.en", help="STT model")
@click.option("--tts-model", default="en_US-lessac-medium", help="TTS model")
@click.pass_context
def voice_converse(ctx: click.Context, model: str, tts_model: str) -> None:
    """Run a conversation turn: wake → listen → respond."""
    manager = _get_voice_manager(ctx)
    manager.config.stt_model = model
    manager.config.tts_model = tts_model
    os_ai = _get_os_ai(ctx)

    console.print("[cyan]Starting conversation mode...[/]")
    console.print("[dim]Say the wake word to begin. Press Ctrl+C to exit.[/]")

    try:
        while True:
            command = asyncio.run(manager.conversation_turn())
            if command:
                console.print(f"[green]You said:[/] {command}")
                response_text = ""
                if os_ai is not None:
                    try:
                        ai_res = asyncio.run(os_ai.process_message(command))
                        response_text = ai_res.content
                    except Exception as exc:
                        console.print(f"[yellow]AI processing error: {exc}[/]")
                        response_text = "Sorry, I had trouble processing that request."
                else:
                    response_text = f"You said: {command}"

                console.print(f"[cyan]Atlas:[/] {response_text}")
                asyncio.run(manager.speak(response_text))
            else:
                console.print("[yellow]No command received.[/]")
    except KeyboardInterrupt:
        console.print("\n[dim]Conversation ended.[/]")
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/]")
        sys.exit(1)


@voice_group.command(name="config")
@click.option("--wake-model", default=None, help="Wake word model")
@click.option("--stt-model", default=None, help="STT model (e.g., base.en, small.en)")
@click.option("--tts-model", default=None, help="TTS model (e.g., en_US-lessac-medium)")
@click.option("--threshold", default=None, type=float, help="Wake word threshold")
@click.option("--show", is_flag=True, help="Show current config")
@click.pass_context
def voice_config(
    ctx: click.Context,
    wake_model: str | None,
    stt_model: str | None,
    tts_model: str | None,
    threshold: float | None,
    show: bool,
) -> None:
    """Configure voice system settings."""
    manager = _get_voice_manager(ctx)

    if show:
        config = manager.config
        table = Table(title="Voice Configuration", box=None)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="white")
        table.add_row("Wake Word Model", config.wake_word_model)
        table.add_row("Wake Word Threshold", str(config.wake_word_threshold))
        table.add_row("STT Model", config.stt_model)
        table.add_row("STT Device", config.stt_device)
        table.add_row("TTS Model", config.tts_model)
        console.print(table)
        return

    if wake_model:
        manager.config.wake_word_model = wake_model
        console.print(f"[green]Wake word model set to: {wake_model}[/]")
    if stt_model:
        manager.config.stt_model = stt_model
        console.print(f"[green]STT model set to: {stt_model}[/]")
    if tts_model:
        manager.config.tts_model = tts_model
        console.print(f"[green]TTS model set to: {tts_model}[/]")
    if threshold is not None:
        manager.config.wake_word_threshold = threshold
        console.print(f"[green]Wake word threshold set to: {threshold}[/]")

    console.print("[dim]Changes apply to current session only. "
          "Add to atlas.yaml for persistence.[/]")


@voice_group.command(name="devices")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def voice_devices(ctx: click.Context, output_json: bool) -> None:
    """List available audio input and output devices."""
    manager = _get_voice_manager(ctx)
    inputs = manager.list_input_devices()
    outputs = manager.list_output_devices()

    if output_json:
        data = {
            "inputs": [d.to_dict() for d in inputs],
            "outputs": [d.to_dict() for d in outputs],
        }
        console.print(json.dumps(data, indent=2))
        return

    if inputs:
        table = Table(title="Input Devices (Microphones)", box=None)
        table.add_column("Index", style="yellow", justify="right")
        table.add_column("Name", style="cyan")
        table.add_column("Channels", justify="right")
        table.add_column("Sample Rate", justify="right")
        table.add_column("Default", style="green")
        for d in inputs:
            table.add_row(
                str(d.index), d.name,
                str(d.max_input_channels),
                f"{d.default_sample_rate:.0f} Hz",
                "✓" if d.is_default_input else "",
            )
        console.print(table)
    else:
        console.print("[yellow]No input devices found.[/]")

    if outputs:
        table = Table(title="Output Devices (Speakers)", box=None)
        table.add_column("Index", style="yellow", justify="right")
        table.add_column("Name", style="cyan")
        table.add_column("Channels", justify="right")
        table.add_column("Sample Rate", justify="right")
        table.add_column("Default", style="green")
        for d in outputs:
            table.add_row(
                str(d.index), d.name,
                str(d.max_output_channels),
                f"{d.default_sample_rate:.0f} Hz",
                "✓" if d.is_default_output else "",
            )
        console.print(table)
    else:
        console.print("[yellow]No output devices found.[/]")
